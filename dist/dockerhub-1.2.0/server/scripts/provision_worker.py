"""Create one private worker configuration from this server's registered IDs."""
import argparse,json,shutil
from pathlib import Path
from urllib.parse import urlsplit
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('worker_id',choices=['2.1','3.1','4.1'])
p.add_argument('--server',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
url=urlsplit(a.server)
if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.path not in ('','/') or url.query or url.fragment:
    p.error('--server must be an HTTP(S) origin, e.g. http://100.x.y.z:8081')
dest=Path(a.output).resolve()
if dest.exists():p.error('Output must be a new folder')
registered=json.loads((root/'.credentials/workers.json').read_text())[a.worker_id]
catalog=json.loads((root/'worker-models.json').read_text())
model=registered['models'][0]
shutil.copytree(root/'worker-template',dest)
cfg=json.loads((dest/'worker-settings.example.json').read_text())
cfg.update(worker_id=a.worker_id,server_url=a.server,
           models={model:catalog[model]})
(dest/'worker-settings.json').write_text(json.dumps(cfg,indent=2))
(dest/'.env').write_text('AI_MODEL='+model+'\nWORKER_CPUS=6\nWORKER_MEMORY=5g\n')
print('Created private configuration for',a.worker_id,'; copy model files into models/.')
