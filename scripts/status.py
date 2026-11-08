from pathlib import Path
import json
from urllib.request import Request,urlopen

root=Path(__file__).resolve().parents[1]
env=dict(line.split('=',1) for line in (root/'.env').read_text().splitlines() if '=' in line)
request=Request('http://127.0.0.1:'+env.get('WORKER_PORT','8081')+'/internal/status',headers={'Authorization':'Bearer '+env['ADMIN_TOKEN']})
with urlopen(request,timeout=10) as response:
    print(json.dumps(json.load(response),ensure_ascii=False,indent=2))
