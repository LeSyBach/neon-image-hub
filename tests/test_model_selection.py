import json
from pathlib import Path

import pytest

from worker.settings import load_settings
from worker.client import Client
from worker.runner import Worker, atomic_json


@pytest.mark.parametrize('model,steps,sampler',[
    ('sd-turbo',4,'euler'),('dreamshaper-8-lcm',6,'lcm')])
def test_env_selects_complete_preset_without_changing_identity(tmp_path,model,steps,sampler):
    path=tmp_path/'worker.json'
    original={'worker_id':'2.1','token':'private-test','server_url':'http://server:8081',
              'state_dir':str(tmp_path/'state'),'models':{'old':{'path':'old'}}}
    path.write_text(json.dumps(original))
    cfg=load_settings(path,{'AI_MODEL':model})
    assert list(cfg['models'])==[model]
    preset=cfg['models'][model]
    assert preset['steps']==steps and preset['sampler']==sampler
    assert preset['path'].startswith('/models/')
    assert cfg['token']==original['token'] and cfg['worker_id']=='2.1'
    assert json.loads(path.read_text())==original


def test_invalid_selection_fails_before_connecting(tmp_path):
    path=tmp_path/'worker.json';path.write_text('{"models":{}}')
    with pytest.raises(ValueError,match='AI_MODEL'):
        load_settings(path,{'AI_MODEL':'unknown'})
    assert load_settings(path,{})=={'models':{}}


def test_client_announces_selection_on_claim_and_heartbeat():
    client=Client('http://server:8081','2.1','test',['dreamshaper-8-lcm'])
    sent=[]
    client.request=lambda path,data=None:sent.append((path,data))
    client.claim();client.heartbeat()
    assert sent==[('/claim',{'models':['dreamshaper-8-lcm']}),
                  ('/heartbeat',{'models':['dreamshaper-8-lcm']})]


def test_pending_job_uses_old_preset_after_selection_change(tmp_path):
    path=tmp_path/'worker.json'
    path.write_text(json.dumps({'worker_id':'2.1','token':'test','server_url':'http://server:8081',
                              'state_dir':str(tmp_path/'state')}))
    worker=Worker(load_settings(path,{'AI_MODEL':'dreamshaper-8-lcm'}))
    job={'id':'a'*32,'model_id':'sd-turbo','prompt':'cat','seed':42}
    with pytest.raises(ValueError):worker.command(job,tmp_path/'image.png')
    atomic_json(worker.pending,{'job':job,'phase':'generating'})
    command=worker.command(job,tmp_path/'image.png')
    assert command[command.index('--sampling-method')+1]=='euler'
    assert command[command.index('--steps')+1]=='4'

