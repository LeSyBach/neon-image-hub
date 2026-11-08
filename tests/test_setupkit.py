import json
from pathlib import Path
import subprocess
import sys

import pytest

from setupkit import __main__ as setup


def invoke(*args):
    return subprocess.run([sys.executable,'-m','setupkit',*map(str,args)],
                          text=True,capture_output=True,stdin=subprocess.DEVNULL)


def test_server_bootstrap_has_no_worker_tokens_and_keeps_admin(tmp_path):
    result=invoke('server','--output',tmp_path,'--server-ip','100.101.102.10')
    assert result.returncode==0,result.stderr
    assert (tmp_path/'web/index.html').is_file()
    assert 'bachcp10/neon-hub-api:1.2.0' in (tmp_path/'compose.yaml').read_text()
    cfg=json.loads((tmp_path/'.credentials/workers.json').read_text())
    assert set(cfg)==set(setup.IDS) and all('token' not in item for item in cfg.values())
    assert 'ADMIN_TOKEN=' in (tmp_path/'.env').read_text()


@pytest.mark.parametrize('worker_id,model',[('2.1','sd-turbo'),('3.1','dreamshaper-8-lcm'),('4.1','sd-turbo')])
def test_worker_bootstrap_without_stdin_or_token(tmp_path,worker_id,model):
    result=invoke('worker','--output',tmp_path,'--worker-id',worker_id,
                  '--server-url','http://100.101.102.10:8081')
    assert result.returncode==0,result.stderr
    cfg=json.loads((tmp_path/'worker-settings.json').read_text())
    assert cfg['worker_id']==worker_id and 'token' not in cfg
    assert list(cfg['models'])==[model]
    assert (tmp_path/'models').is_dir() and (tmp_path/'worker-state').is_dir()
    assert 'bachcp10/neon-hub-worker:1.2.0' in (tmp_path/'compose.yaml').read_text()


def test_reinitialization_preserves_existing_files(tmp_path):
    (tmp_path/'.env').write_text('keep-existing-config')
    result=invoke('server','--output',tmp_path,'--server-ip','100.101.102.10')
    assert result.returncode==2
    assert (tmp_path/'.env').read_text()=='keep-existing-config'


@pytest.mark.parametrize('url',['file:///etc/passwd','http://user:pass@server','http://server:8081/other'])
def test_invalid_worker_origin_fails_without_writing(tmp_path,url):
    result=invoke('worker','--output',tmp_path,'--worker-id','2.1','--server-url',url)
    assert result.returncode==2 and not list(tmp_path.iterdir())


@pytest.mark.parametrize('role',['server','worker'])
def test_upgrade_preserves_data_env_identity_and_models(tmp_path,role):
    compose=tmp_path/'compose.yaml'
    compose.write_text('services:\n  app:\n    image: bachcp10/neon-hub-'+('api' if role=='server' else 'worker')+':1.1.0\n')
    (tmp_path/'.env').write_text('ADMIN_TOKEN=keep-this-admin-secret\nWEB_BIND=0.0.0.0\n')
    data=tmp_path/'data';data.mkdir();(data/'keep.png').write_bytes(b'preserve-image-data')
    if role=='server':
        cfg_path=tmp_path/'.credentials/workers.json';cfg_path.parent.mkdir()
        original={'2.1':{'token':'old-secret','models':['sd-turbo'],'allowed_models':['sd-turbo','dreamshaper-8-lcm']}}
    else:
        cfg_path=tmp_path/'worker-settings.json'
        original={'worker_id':'2.1','token':'old-secret','server_url':'http://100.101.102.10:8081','models':{'sd-turbo':{'path':'/models/a'}}}
    cfg_path.write_text(json.dumps(original))
    result=invoke('upgrade','--output',tmp_path)
    assert result.returncode==0,result.stderr
    assert ':1.2.0' in compose.read_text()
    cfg=json.loads(cfg_path.read_text())
    expected=json.loads(json.dumps(original))
    if role=='server':expected['2.1'].pop('token')
    else:expected.pop('token')
    assert cfg==expected
    assert 'WEB_BIND=0.0.0.0' in (tmp_path/'.env').read_text()
    assert 'ADMIN_TOKEN=keep-this-admin-secret' in (tmp_path/'.env').read_text()
    assert (data/'keep.png').read_bytes()==b'preserve-image-data'
    assert json.loads(cfg_path.with_name(cfg_path.name+'.before-1.2.0').read_text())==original
    assert invoke('upgrade','--output',tmp_path).returncode==0
