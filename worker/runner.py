"""One real local inference at a time, with a durable pending result and lease.

No server credentials/DB access and no Docker socket are needed in this worker.
"""
import fcntl
import json
import logging
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time

from .client import Client, Rejected
from .settings import load_settings

log = logging.getLogger('neon.worker')


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as file:
        json.dump(value, file, ensure_ascii=False)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary, path)


class Worker:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.id = settings['worker_id']
        if not re.fullmatch(r'[1-9]\d*\.[1-9]\d*', self.id):
            raise ValueError('Worker ID must be member.process, for example 2.1')
        self.client = client or Client(settings['server_url'], self.id, models=list(settings['models']))
        self.root = Path(settings['state_dir'])
        self.root.mkdir(parents=True, exist_ok=True)
        self.pending = self.root / 'pending.json'
        self.stop = threading.Event()
        self.active_process = None

    def status(self, state, **detail):
        atomic_json(self.root / 'status.json', {'worker_id':self.id, 'state':state, 'updated':time.time(), **detail})

    def command(self, job, output):
        model = self.settings['models'].get(job['model_id'])
        if not model and self.pending.exists():
            pending_job = json.loads(self.pending.read_text()).get('job', {})
            if pending_job.get('id') == job['id'] and pending_job.get('model_id') == job['model_id']:
                model = self.settings.get('model_presets', {}).get(job['model_id'])
        if not model:
            raise ValueError('Server selected a model that is not configured locally')
        if not re.fullmatch(r'[0-9a-f]{32}', job['id']):
            raise ValueError('Invalid job ID')
        if not isinstance(job['prompt'], str) or len(job['prompt']) > 2000:
            raise ValueError('Invalid prompt')
        if not isinstance(job['seed'], int) or not 0 <= job['seed'] < 2**31:
            raise ValueError('Invalid seed')
        size = int(model.get('size', 512))
        steps = int(model.get('steps', 4))
        if not 128 <= size <= 2048 or not 1 <= steps <= 50:
            raise ValueError('Invalid local model size/steps')
        cmd = [self.settings.get('sd_cli', '/opt/sd/sd-cli'), '-m', model['path'],
            '--backend','cpu','--mmap','-t',str(self.settings.get('threads',6)),
            '-p',job['prompt'],'-W',str(size),'-H',str(size),'--steps',str(steps),
            '--cfg-scale',str(model.get('cfg',1)), '--sampling-method',model.get('sampler','euler'),
            '-s',str(job['seed']),'-o',str(output)]
        if model.get('clip_skip'):
            cmd.extend(['--clip-skip',str(model['clip_skip'])])
        if model.get('taesd'):
            cmd.extend(['--taesd',model['taesd']])
        return cmd

    def heartbeat_loop(self, job, done, lost):
        interval = max(1,min(20,job.get('heartbeat_after',20),job.get('lease_seconds',180)/4))
        lease_seconds=job.get('lease_seconds',180)
        deadline = time.monotonic() + lease_seconds
        while not done.wait(interval):
            if self.stop.is_set():
                return
            try:
                answer = self.client.heartbeat(job)
                lease_seconds=answer.get('lease_seconds',180)
                deadline = time.monotonic() + lease_seconds
            except Rejected as exc:
                if exc.status in (401,403,404,409):
                    log.warning('Lease rejected for job=%s HTTP=%s',job['id'],exc.status)
                    lost.set()
                    return
            except (OSError, ValueError):
                log.warning('Heartbeat delayed for job=%s',job['id'])
            if time.monotonic() > deadline - min(5,lease_seconds*.1):
                lost.set()
                log.warning('Lease could not be renewed for job=%s',job['id'])
                return

    def generate(self, job, output, lost):
        cmd = self.command(job, output)
        logfile = self.root / f'{job["id"]}.log'
        started = time.monotonic()
        self.status('generating',job_id=job['id'],name=job['name'],model_id=job['model_id'])
        log.info('Generating job=%s name=%s model=%s',job['id'],job['name'],job['model_id'])
        with logfile.open('w') as logs:
            process = subprocess.Popen(cmd, stdout=logs, stderr=subprocess.STDOUT, start_new_session=True)
            self.active_process = process
            try:
                while process.poll() is None:
                    if self.stop.is_set() or lost.is_set() or time.monotonic()-started > self.settings.get('generation_timeout',900):
                        os.killpg(process.pid,signal.SIGTERM)
                        try:
                            process.wait(timeout=8)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid,signal.SIGKILL)
                            process.wait()
                        if self.stop.is_set() or lost.is_set():
                            return False
                        raise RuntimeError('Local image generation exceeded its timeout')
                    time.sleep(.25)
                if process.returncode:
                    raise RuntimeError(f'Local inference failed with exit code {process.returncode}; see task log')
                if not output.is_file() or output.stat().st_size < 100:
                    raise RuntimeError('Local inference did not save a usable result')
            finally:
                self.active_process = None
        elapsed = round(time.monotonic()-started,2)
        log.info('Image generated job=%s seconds=%s',job['id'],elapsed)
        return True

    def clear(self, job, delete_output=False):
        if delete_output:
            (self.root / f'{job["id"]}.png').unlink(missing_ok=True)
        self.pending.unlink(missing_ok=True)

    def process(self, record):
        job = record['job']
        if not re.fullmatch(r'[0-9a-f]{32}', job['id']):
            raise ValueError('Invalid persisted job ID')
        output = self.root / f'{job["id"]}.png'
        # Completion is tried before heartbeats for a recovered result. If the
        # server committed it just before a crash, replay returns the same image.
        if record.get('phase') == 'upload' and output.is_file():
            try:
                result = self.client.complete(job, output)
                self.finish(job,result)
                return
            except Rejected as exc:
                if exc.status in (401,403):
                    raise
                if exc.status in (404,409):
                    self.clear(job,delete_output=True)
                    return
                if exc.status in (413,422):
                    record['phase']='failure'; record['error']='Server rejected result image'
                    atomic_json(self.pending,record)
            except OSError:
                pass
        try:
            self.client.heartbeat(job)
        except Rejected as exc:
            if exc.status in (404,409):
                self.clear(job,delete_output=True)
                return
            raise
        done=threading.Event();lost=threading.Event()
        heartbeat=threading.Thread(target=self.heartbeat_loop,args=(job,done,lost),daemon=True)
        heartbeat.start()
        try:
            if record.get('phase')=='generating':
                try:
                    if not self.generate(job,output,lost):
                        if lost.is_set():
                            self.clear(job,delete_output=True)
                        return
                    record['phase']='upload';atomic_json(self.pending,record)
                except (RuntimeError,ValueError,OSError) as exc:
                    record['phase']='failure';record['error']=str(exc)[:400]
                    atomic_json(self.pending,record)
                    log.error('Generation failed job=%s type=%s',job['id'],type(exc).__name__)
            delay=2
            while not self.stop.is_set() and not lost.is_set():
                try:
                    if record['phase']=='failure':
                        self.client.fail(job,record['error'])
                        self.clear(job,delete_output=True)
                        return
                    self.status('uploading',job_id=job['id'],name=job['name'])
                    result=self.client.complete(job,output)
                    self.finish(job,result)
                    return
                except Rejected as exc:
                    if exc.status in (401,403):
                        raise
                    if exc.status in (404,409):
                        self.clear(job,delete_output=True)
                        return
                    if exc.status in (413,422):
                        record['phase']='failure';record['error']='Server rejected result image'
                        atomic_json(self.pending,record)
                except OSError:
                    log.warning('Result transfer delayed job=%s; retrying',job['id'])
                self.stop.wait(delay);delay=min(30,delay*2)
            if lost.is_set():
                # Do not discard an upload here: an in-flight request could
                # already have committed. Replay it on the next cycle.
                if record.get('phase')!='upload':
                    self.clear(job,delete_output=True)
        finally:
            done.set();heartbeat.join(timeout=17)

    def finish(self, job, result):
        image=result['image']
        atomic_json(self.root / f'{job["id"]}.result.json', {
            'job_id':job['id'],'name':job['name'],'model_id':job['model_id'],
            'image_id':image['id'],'filename':image['filename'],'completed':time.time(),
            'reused':result.get('reused',False)})
        log.info('Saved by server job=%s filename=%s reused=%s',job['id'],image['filename'],result.get('reused',False))
        self.clear(job,delete_output=True)
        self.status('idle',last_job=job['id'])

    def run(self):
        for model in self.settings['models'].values():
            for key in ['path','taesd']:
                if model.get(key) and not Path(model[key]).is_file():
                    raise ValueError(f'Missing local model component: {key}')
        lock=(self.root/'worker.lock').open('w')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        log.info('Worker ready id=%s; backend=cpu; models=%s',self.id,','.join(self.settings['models']))
        next_heartbeat=0
        try:
            while not self.stop.is_set():
                try:
                    if self.pending.exists():
                        self.process(json.loads(self.pending.read_text()))
                        continue
                    if time.monotonic()>=next_heartbeat:
                        self.client.heartbeat();next_heartbeat=time.monotonic()+20
                    free=shutil.disk_usage(self.root).free
                    if (self.root/'pause').exists() or free<self.settings.get('minimum_free_bytes',1024**3):
                        self.status('paused',reason='manual' if (self.root/'pause').exists() else 'disk_space')
                        self.stop.wait(10)
                        continue
                    answer=self.client.claim()
                    job=answer.get('job')
                    if job:
                        atomic_json(self.pending,{'job':job,'phase':'generating'})
                        self.process({'job':job,'phase':'generating'})
                    else:
                        self.status('idle');self.stop.wait(min(20,answer.get('poll_after',10)))
                except Rejected as exc:
                    self.status('error',http_status=exc.status)
                    log.warning('Server request rejected HTTP=%s',exc.status)
                    if exc.status in (401,403):
                        raise RuntimeError('Worker ID/model rejected; verify server registration and selected model') from None
                    self.stop.wait(10)
                except (OSError,ValueError) as exc:
                    self.status('reconnecting',error_type=type(exc).__name__)
                    log.warning('Temporary issue type=%s; pending job retained',type(exc).__name__)
                    self.stop.wait(10)
        finally:
            self.status('stopped')
            fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


def main():
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    config=Path(os.getenv('WORKER_SETTINGS','/config/worker.json'))
    worker=Worker(load_settings(config))
    signal.signal(signal.SIGTERM,lambda *_:worker.stop.set())
    signal.signal(signal.SIGINT,lambda *_:worker.stop.set())
    worker.run()


if __name__=='__main__':
    main()
