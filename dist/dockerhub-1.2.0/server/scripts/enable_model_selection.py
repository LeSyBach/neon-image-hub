"""Grant existing members the two tested presets, preserving tokens/defaults."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
path=root/'.credentials/workers.json'
workers=json.loads(path.read_text())
tested=['sd-turbo','dreamshaper-8-lcm']
for worker_id in ('2.1','3.1','4.1'):
    cfg=workers.get(worker_id)
    if cfg is None:
        continue
    allowed=cfg.get('allowed_models',cfg['models'])
    cfg['allowed_models']=list(dict.fromkeys([*allowed,*tested]))
temporary=path.with_suffix('.tmp')
temporary.write_text(json.dumps(workers,indent=2))
temporary.replace(path)
print('Enabled both tested model choices for existing members; tokens and defaults preserved.')
