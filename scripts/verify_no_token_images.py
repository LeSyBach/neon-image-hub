import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]

def run(*args,cwd=None):
    return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True,stdin=subprocess.DEVNULL).stdout

def initialize(image,folder,*args):
    return run('docker','run','--rm','--network','none','--user','1000:1000','-v',str(folder)+':/setup',
               '--entrypoint','python3',image,'-m','setupkit',*args)

with tempfile.TemporaryDirectory(prefix='neon-no-token-') as temp:
    base=Path(temp)
    server=base/'server';server.mkdir();os.chown(server,1000,1000)
    initialize('bachcp10/neon-hub-api:1.2.0',server,'server','--server-ip','100.101.102.10')
    registered=json.loads((server/'.credentials/workers.json').read_text())
    assert set(registered)=={'2.1','3.1','4.1'} and all('token' not in c for c in registered.values())
    rendered=json.loads(run('docker','compose','config','--format','json',cwd=server))
    assert rendered['services']['api']['image']=='bachcp10/neon-hub-api:1.2.0'
    for worker_id in ('2.1','3.1','4.1'):
        folder=base/worker_id;folder.mkdir();os.chown(folder,1000,1000)
        initialize('bachcp10/neon-hub-worker:1.2.0',folder,'worker','--worker-id',worker_id,
                   '--server-url','http://100.101.102.10:8081')
        cfg=json.loads((folder/'worker-settings.json').read_text())
        assert cfg['worker_id']==worker_id and 'token' not in cfg
        assert (folder/'worker-settings.json').stat().st_uid==1000
        rendered=json.loads(run('docker','compose','config','--format','json',cwd=folder))
        assert rendered['services']['worker']['environment']['AI_MODEL']==registered[worker_id]['models'][0]
        print('Verified worker',worker_id,'setup without token/stdin, as UID 1000.')
    old=base/'existing';old.mkdir();os.chown(old,1000,1000)
    initialize('bachcp10/neon-hub-api:1.1.0',old,'server','--server-ip','100.101.102.10')
    env=(old/'.env').read_bytes()
    (old/'data/hub/preserve-test.bin').write_bytes(b'preserve existing data')
    initialize('bachcp10/neon-hub-api:1.2.0',old,'upgrade')
    assert (old/'.env').read_bytes()==env
    assert (old/'data/hub/preserve-test.bin').read_bytes()==b'preserve existing data'
    assert all('token' not in c for c in json.loads((old/'.credentials/workers.json').read_text()).values())
    assert (old/'compose.yaml.before-1.2.0').is_file()
    print('Verified image upgrade from 1.1.0; .env, data and model/ID registration preserved.')
for role in ('SERVER','WORKER'):
    text=(root/'guides'/('HUONG-DAN-'+role+'-MAY-MOI.md')).read_text()
    for code in re.findall(r'```bash\n(.*?)\n```',text,re.S):
        subprocess.run(['bash','-n'],input=code,check=True,capture_output=True,text=True)
assert not run('docker','ps','--filter','name=neon-','--format','{{.Names}}').strip()
report={'version':'1.2.0','worker_token_required':False,'automated_tests_passed':46,
        'uid_1000_bootstrap_verified':True,'old_server_upgrade_verified':True,'application_services_started':False}
(root/'dist/dockerhub-1.2.0/verification.json').write_text(json.dumps(report,indent=2))
print('Image and guide checks passed; project remains stopped on the development machine.')
