import json
from pathlib import Path
import sys
import threading
import time

import pytest

from worker.client import Client, Rejected, multipart
from worker.runner import Worker, atomic_json


JOB={'id':'a'*32,'name':'black dog','prompt':'black dog, neon lighting','model_id':'sd-turbo',
     'seed':42,'lease':'lease-example','lease_seconds':3,'heartbeat_after':1}


class FakeClient:
    def __init__(self):
        self.heartbeats=0;self.uploads=0;self.failures=[];self.lost_response=False

    def heartbeat(self,job=None):
        self.heartbeats+=1
        return {'lease_seconds':3}

    def complete(self,job,path):
        assert Path(path).is_file()
        self.uploads+=1
        if self.lost_response and self.uploads==1:
            raise OSError('Simulated lost completion response')
        return {'image':{'id':'image-id','filename':'black dog 2.1.png'},'reused':self.uploads>1}

    def fail(self,job,message):
        self.failures.append(message)
        return {'state':'queued'}


@pytest.fixture
def worker(tmp_path):
    model=tmp_path/'model.gguf';model.write_bytes(b'model fixture')
    cfg={'worker_id':'2.1','token':'test-only','server_url':'http://server:8000',
         'state_dir':str(tmp_path/'state'),'models':{'sd-turbo':{'path':str(model),'steps':4,'size':512}},
         'sd_cli':sys.executable,'generation_timeout':5}
    return Worker(cfg,FakeClient())


def fixture_generator(worker,delay=0,code=0):
    # Only worker control-flow tests use this deterministic fixture program.
    # The deployment smoke test uses the real sd-cli and real model weights.
    def command(job,path):
        return [sys.executable,'-c',
                f'import time,sys; time.sleep({delay}); open(sys.argv[1],"wb").write(b"fixture"*100); sys.exit({code})',str(path)]
    worker.command=command


def test_command_keeps_prompt_as_one_argument_without_shell(worker):
    job={**JOB,'prompt':'cat; $(do-not-execute)'}
    cmd=worker.command(job,worker.root/'result.png')
    assert cmd[cmd.index('-p')+1]==job['prompt']
    assert cmd[cmd.index('--backend')+1]=='cpu'


def test_success_has_heartbeat_during_generation_and_cleans_result(worker):
    fixture_generator(worker,delay=1.3)
    record={'job':dict(JOB),'phase':'generating'}
    atomic_json(worker.pending,record)
    worker.process(record)
    assert worker.client.heartbeats>=2
    assert worker.client.uploads==1
    assert not worker.pending.exists()
    assert not (worker.root/f'{JOB["id"]}.png').exists()
    assert json.loads((worker.root/f'{JOB["id"]}.result.json').read_text())['image_id']=='image-id'


def test_result_recovery_uploads_without_generating_again(worker):
    path=worker.root/f'{JOB["id"]}.png';path.write_bytes(b'finished image')
    record={'job':dict(JOB),'phase':'upload'}
    atomic_json(worker.pending,record)
    worker.command=lambda *_:pytest.fail('Must not generate an already finished image')
    worker.process(record)
    assert worker.client.uploads==1 and not worker.pending.exists()


def test_missing_completion_response_replays_same_job(worker):
    fixture_generator(worker)
    worker.client.lost_response=True
    record={'job':dict(JOB),'phase':'generating'}
    atomic_json(worker.pending,record)
    worker.process(record)
    assert worker.client.uploads==2
    assert json.loads((worker.root/f'{JOB["id"]}.result.json').read_text())['reused'] is True


def test_reassigned_job_is_not_uploaded(worker):
    def reject(*_):raise Rejected(409)
    worker.client.heartbeat=reject
    record={'job':dict(JOB),'phase':'generating'}
    atomic_json(worker.pending,record)
    worker.process(record)
    assert worker.client.uploads==0 and not worker.pending.exists()


def test_engine_error_is_reported_to_server(worker):
    fixture_generator(worker,code=7)
    record={'job':dict(JOB),'phase':'generating'}
    atomic_json(worker.pending,record)
    worker.process(record)
    assert len(worker.client.failures)==1
    assert worker.client.uploads==0 and not worker.pending.exists()


def test_shutdown_retains_claim_for_recovery(worker):
    fixture_generator(worker,delay=5)
    record={'job':dict(JOB),'phase':'generating'}
    atomic_json(worker.pending,record)
    timer=threading.Timer(.4,worker.stop.set);timer.start()
    try:worker.process(record)
    finally:timer.cancel()
    assert worker.pending.exists()
    assert not worker.client.failures and worker.client.uploads==0


def test_unconfigured_model_and_invalid_job_id_rejected(worker):
    with pytest.raises(ValueError):worker.command({**JOB,'model_id':'pretend-model'},worker.root/'out.png')
    with pytest.raises(ValueError):worker.command({**JOB,'id':'../../outside'},worker.root/'out.png')


def test_multipart_contains_file_and_fields(worker):
    file=worker.root/'a.png';file.write_bytes(b'image bytes')
    body,kind=multipart({'lease':'current-lease','model_id':'sd-turbo'},file)
    assert b'image bytes' in body and b'current-lease' in body and b'sd-turbo' in body
    assert kind.startswith('multipart/form-data; boundary=')


@pytest.mark.parametrize('origin',['file:///tmp/key','http://user:password@host','http://host/?token=secret'])
def test_bad_server_origins_rejected(origin):
    with pytest.raises(ValueError):Client(origin,'2.1','test-token')
