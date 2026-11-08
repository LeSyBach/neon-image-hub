import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
names=['neon-hub-api:local','nginx:stable-alpine','binwiederhier/ntfy:latest','henrygd/beszel:0.21.1','henrygd/beszel-agent:0.21.1','neon-hub-worker:local']
results=[]
for name in names:
    raw=subprocess.check_output(['/usr/bin/docker','image','inspect',name],text=True)
    image=json.loads(raw)[0]
    results.append({'image':name,'id':image['Id'],'digests':image.get('RepoDigests',[])})
(root/'IMAGE-LOCK.json').write_text(json.dumps(results,indent=2))
print('Recorded deployed image IDs and upstream digests.')
