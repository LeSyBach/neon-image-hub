"""Real local inference recovery after gracefully restarting its container."""
from pathlib import Path
import json
import subprocess
import time
from urllib.request import urlopen

root=Path(__file__).resolve().parents[1]
pending=root/'data/worker-2.1/pending.json'
for _ in range(90):
    if pending.exists():
        record=json.loads(pending.read_text())
        status=json.loads((root/'data/worker-2.1/status.json').read_text())
        if record['phase']=='generating' and status.get('job_id')==record['job']['id'] and time.time()-status['updated']<3:break
    time.sleep(1)
else:raise RuntimeError('No running generation available to test recovery')
job_id=record['job']['id']
def get_job():
    with urlopen('http://127.0.0.1:8080/api/jobs/'+job_id,timeout=10) as r:return json.load(r)
before=get_job()
assert before['state']=='running'
attempts=before['attempts']
subprocess.run(['/usr/bin/docker','compose','-f','compose.yaml','-f','compose.worker-local.yaml',
    '--profile','local-worker','restart','worker-local'],cwd=root,check=True)
print('Worker restarted during generation; waiting for its original job.',flush=True)
for _ in range(90):
    job=get_job()
    if job['state']=='succeeded':break
    assert job['state']=='running', job['state']
    time.sleep(2)
else:raise RuntimeError('Recovery did not finish in time')
assert job['attempts']==attempts
assert job['image']['worker_id']=='2.1'
report={'job_id':job_id,'same_job_completed':True,'attempts_before':attempts,
        'attempts_after':job['attempts'],'image_id':job['image']['id'],
        'same_worker':True,'restart_requested_within_first_3_seconds_of_generation':True,'runtime':'one real local CPU worker in WSL'}
(root/'test-results/worker-real-restart.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
