import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
credentials=root/'.credentials/workers.json'
workers=json.loads(credentials.read_text())
if workers['3.1']['models']==['model-b']:
    workers['3.1']['models']=['dreamshaper-8-lcm']
    credentials.write_text(json.dumps(workers,indent=2))
if workers['3.1']['models']!=['dreamshaper-8-lcm']:
    raise RuntimeError('Worker 3.1 has custom models; refusing to replace its configuration')
cfg=root/'.credentials/worker-b-local.json'
if not cfg.exists():
    model=json.loads((root/'worker-models.json').read_text())['dreamshaper-8-lcm']
    cfg.write_text(json.dumps({'worker_id':'3.1','server_url':'http://api:8000',
        'state_dir':'/state','threads':6,'generation_timeout':900,'minimum_free_bytes':1024**3,
        'models':{'dreamshaper-8-lcm':model}},indent=2))
(root/'data/worker-3.1').mkdir(parents=True,exist_ok=True)
print('Worker 3.1 configured with DreamShaper8 LCM; existing token preserved.')
