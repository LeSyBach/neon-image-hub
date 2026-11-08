import base64
import json
import logging
import os
import signal
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from . import config, store

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
log=logging.getLogger('neon.scheduler')
running=True


def stop(*_):
    global running
    running=False


def publish_events():
    endpoint=os.getenv('NTFY_URL','').rstrip('/')
    topic=os.getenv('NTFY_TOPIC','')
    if not endpoint or not topic:
        return
    with store.connect() as c:
        rows=c.execute('SELECT * FROM events WHERE delivered IS NULL AND next_try<=? ORDER BY id LIMIT 40',(time.time(),)).fetchall()
    for row in rows:
        text=f"{row['module']} | {row['event']}\njob={row['job_id'] or '-'} worker={row['worker_id'] or '-'}\n{row['detail']}"
        headers={'Content-Type':'text/plain; charset=utf-8','Title':f"Neon {row['module']}", 'Tags':'information_source'}
        login=os.getenv('NTFY_USER','neon')+':'+os.getenv('NTFY_PASSWORD','')
        headers['Authorization']='Basic '+base64.b64encode(login.encode()).decode()
        try:
            req=Request(endpoint+'/'+topic,data=text.encode(),headers=headers,method='POST')
            with urlopen(req,timeout=5) as response:
                response.read()
            with store.transaction() as c:
                c.execute('UPDATE events SET delivered=? WHERE id=?',(time.time(),row['id']))
        except (URLError,OSError) as e:
            delay=min(300,2**min(row['tries']+1,8))
            with store.transaction() as c:
                c.execute('UPDATE events SET tries=tries+1,next_try=? WHERE id=?',(time.time()+delay,row['id']))
            log.warning('Notification deferred, event=%s; %s',row['id'],type(e).__name__)
            break


def main():
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    store.init()
    with store.transaction() as c:
        store.event(c,'scheduler','service_started')
    log.info('Scheduler ready; image generation runs only on connected workers.')
    last_cleanup=0
    while running:
        try:
            store.tick()
            publish_events()
            if time.time()-last_cleanup>3600:
                with store.transaction() as c:
                    c.execute('DELETE FROM events WHERE delivered IS NOT NULL AND created<?',(time.time()-30*86400,))
                last_cleanup=time.time()
            (config.DATA/'scheduler-heartbeat').touch()
        except Exception:
            log.exception('Scheduler cycle failed; retrying next cycle')
        for _ in range(3):
            if not running:
                break
            time.sleep(1)


if __name__=='__main__':
    main()
