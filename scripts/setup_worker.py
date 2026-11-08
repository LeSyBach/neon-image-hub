"""Create ONE local worker config; never copy all member tokens to a worker."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
credentials=json.loads((root/'.credentials/workers.json').read_text())
path=root/'.credentials/worker-local.json'
if path.exists():
    print('Local worker configuration already exists; preserved.')
else:
    cfg={'worker_id':'2.1','server_url':'http://api:8000',
         'state_dir':'/state','threads':6,'generation_timeout':900,'minimum_free_bytes':1024**3,
         'models':{'sd-turbo':{'path':'/models/sd_turbo-f16-q8_0.gguf','taesd':'/models/taesd.safetensors',
                              'steps':4,'size':512,'clip_skip':1,'cfg':1,'sampler':'euler'}}}
    path.write_text(json.dumps(cfg,indent=2))
    print('Local worker 2.1 configured; credentials not printed.')
(root/'data/worker-2.1').mkdir(parents=True,exist_ok=True)
