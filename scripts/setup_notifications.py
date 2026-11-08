import base64
import os
from pathlib import Path
import subprocess
from urllib.request import Request,urlopen

root=Path(__file__).resolve().parents[1]
env={line.split('=',1)[0]:line.split('=',1)[1] for line in (root/'.env').read_text().splitlines() if '=' in line and not line.startswith('#')}
proc_env=os.environ.copy();proc_env['NTFY_PASSWORD']=env['NTFY_PASSWORD']
subprocess.run(['/usr/bin/docker','compose','exec','-T','-e','NTFY_PASSWORD','ntfy','ntfy','user','add','--ignore-exists','--role=admin',env['NTFY_USER']],
               cwd=root,env=proc_env,check=True,capture_output=True)
auth=base64.b64encode((env['NTFY_USER']+':'+env['NTFY_PASSWORD']).encode()).decode()
req=Request('http://127.0.0.1:'+env.get('NTFY_PORT','8091')+'/'+env['NTFY_TOPIC'],data=b'Server Neon: log channel ready.',
            headers={'Authorization':'Basic '+auth,'Title':'Neon server setup'},method='POST')
with urlopen(req,timeout=10) as r:
    assert r.status==200
print('Private ntfy account initialized; authenticated log publish succeeded. Credentials remain in .env.')
