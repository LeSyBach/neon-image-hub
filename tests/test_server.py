from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server import config, store
from server.api import app


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'DATA',tmp_path)
    monkeypatch.setattr(config,'DATABASE',tmp_path/'test.sqlite3')
    monkeypatch.setattr(config,'IMAGES',tmp_path/'images')
    monkeypatch.setattr(config,'ADMIN_TOKEN','test-admin')
    cfg=tmp_path/'workers.json'
    cfg.write_text(json.dumps({str(i)+'.1':{'models':['sd-turbo' if i!=3 else 'tiny-sd']} for i in [2,3,4]}))
    monkeypatch.setattr(config,'CREDENTIALS',cfg)
    with TestClient(app) as c:
        yield c


def auth(worker='2.1'):
    return {}


def search(client,name='black dog'):
    return client.post('/api/search',json={'name':name})


def claim(client,worker='2.1'):
    return client.post(f'/internal/workers/{worker}/claim',headers=auth(worker))


def png(size=128):
    # A deterministic test fixture, never inserted into the deployed database.
    buf=BytesIO();Image.new('RGB',(size,size),'blue').save(buf,format='PNG');return buf.getvalue()


def complete(client,job,worker='2.1',data=None):
    return client.post(f'/internal/workers/{worker}/jobs/{job["id"]}/complete',
        headers=auth(worker),data={'lease':job['lease'],'model_id':job['model_id']},
        files={'file':('../../unsafe.jpg',data or png(),'image/png')})


def test_search_concurrency_deduplicates_and_promotes_background(client):
    with store.transaction() as c:
        bg=store.enqueue(c,'black dog','background')
    with ThreadPoolExecutor(max_workers=10) as pool:
        results=list(pool.map(lambda _:search(client,'  BLACK   DOG  '),range(20)))
    assert all(r.status_code==202 for r in results)
    assert len({r.json()['job']['id'] for r in results})==1
    with store.connect() as c:
        assert c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==1
        assert c.execute('SELECT priority FROM jobs').fetchone()[0]==100


def test_worker_claim_is_atomic_and_priority_is_respected(client):
    with store.transaction() as c:
        store.enqueue(c,'blue fish','background')
    wanted=search(client,'red bicycle').json()['job']['id']
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:claim(client),range(8)))
    ok=[r.json()['job'] for r in results if r.status_code==200]
    assert len(ok)==1 and ok[0]['id']==wanted
    assert all(r.status_code in [200,409] for r in results)


def test_three_workers_receive_different_jobs(client):
    for name in ['white rabbit','blue butterfly','red bicycle']:
        search(client,name)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda w:claim(client,w),['2.1','3.1','4.1']))
    jobs=[r.json()['job'] for r in results]
    assert len({j['id'] for j in jobs})==3
    assert {j['model_id'] for j in jobs}=={'sd-turbo','tiny-sd'}


def test_worker_selects_authorized_model_without_editing_server_again(client):
    credentials=json.loads(config.CREDENTIALS.read_text())
    credentials['2.1']['allowed_models']=['sd-turbo','dreamshaper-8-lcm']
    config.CREDENTIALS.write_text(json.dumps(credentials))
    search(client,'dragonfly')
    answer=client.post('/internal/workers/2.1/claim',headers=auth(),
                       json={'models':['dreamshaper-8-lcm']})
    assert answer.status_code==200
    job=answer.json()['job']
    assert job['model_id']=='dreamshaper-8-lcm'
    # A restart may advertise the next model while uploading an old result.
    client.post('/internal/workers/2.1/heartbeat',headers=auth(),
                json={'models':['sd-turbo'],'job_id':job['id'],'lease':job['lease']})
    assert complete(client,job).status_code==200
    search(client,'lotus')
    new=client.post('/internal/workers/2.1/claim',headers=auth(),json={'models':['sd-turbo']})
    assert new.json()['job']['model_id']=='sd-turbo'
    stats=client.get('/api/stats').json()
    assert next(w for w in stats['workers'] if w['id']=='2.1')['models']==['sd-turbo']


@pytest.mark.parametrize('body,status',[
    ({'models':['unauthorized']},403),({'models':[]},422),({'models':'sd-turbo'},422)])
def test_worker_cannot_claim_unauthorized_or_empty_model(client,body,status):
    search(client)
    assert client.post('/internal/workers/2.1/claim',headers=auth(),json=body).status_code==status
    assert claim(client).json()['job']['model_id']=='sd-turbo'


def test_end_to_end_save_replay_reuse_and_filename(client):
    search(client)
    job=claim(client).json()['job']
    saved=complete(client,job)
    assert saved.status_code==200,saved.text
    image=saved.json()['image']
    assert image['filename']=='black dog 2.1.png'
    assert image['width']==128
    assert client.get(image['url']).headers['content-type']=='image/png'
    replay=complete(client,job)
    assert replay.json()['reused'] is True
    found=search(client,'BLACK DOG')
    assert found.status_code==200 and found.json()['state']=='found'
    assert search(client,'dog').json()['image']['id']==image['id']
    assert client.get('/api/stats').json()['total_images']==1
    assert client.get('/api/jobs/'+job['id']).json()['state']=='succeeded'
    assert all(p.name!='unsafe.jpg' for p in config.IMAGES.rglob('*'))


def test_expired_lease_is_fenced_and_reclaimed(client):
    search(client)
    old=claim(client).json()['job']
    with store.transaction() as c:
        c.execute('UPDATE jobs SET expires=? WHERE id=?',(time.time()-5,old['id']))
    new=claim(client,'3.1').json()['job']
    assert old['id']==new['id'] and old['lease']!=new['lease']
    assert complete(client,old).status_code==409
    assert complete(client,new,'3.1').status_code==200


def test_heartbeat_renews_only_current_owner(client):
    search(client);job=claim(client).json()['job']
    body={'job_id':job['id'],'lease':job['lease']}
    assert client.post('/internal/workers/3.1/heartbeat',headers=auth('3.1'),json=body).status_code==409
    assert client.post('/internal/workers/2.1/heartbeat',headers=auth(),json=body).status_code==200


@pytest.mark.parametrize('kind',['small','bad','wrong-model'])
def test_upload_validation(client,kind):
    search(client);job=claim(client).json()['job']
    if kind=='wrong-model': job['model_id']='not-authorized'
    r=complete(client,job,data=png(64) if kind=='small' else (b'not an image' if kind=='bad' else None))
    assert r.status_code==(409 if kind=='wrong-model' else 422)
    assert client.get('/api/stats').json()['total_images']==0


def test_authentication_and_invalid_names(client):
    assert client.post('/internal/workers/2.1/claim').status_code==200
    assert client.post('/internal/workers/3.1/claim').status_code==200
    assert client.post('/internal/workers/2.2/claim').status_code==403
    assert client.get('/internal/status').status_code==401
    for name in ['chó đen','../cat','%','a','cat\x00dog']:
        assert search(client,name).status_code==422


def test_retry_limit_and_admin_cancel(client):
    job_id=search(client).json()['job']['id']
    for i in range(config.MAX_ATTEMPTS):
        job=claim(client).json()['job']
        r=client.post(f'/internal/workers/2.1/jobs/{job_id}/fail',headers=auth(),
            json={'lease':job['lease'],'message':'test failure'})
        assert r.json()['state']==('failed' if i==config.MAX_ATTEMPTS-1 else 'queued')
    assert client.get('/api/jobs/'+job_id).json()['state']=='failed'
    headers={'Authorization':'Bearer test-admin'}
    assert client.post('/internal/jobs/'+job_id+'/retry',headers=headers).status_code==200
    assert client.post('/internal/jobs/'+job_id+'/cancel',headers=headers).status_code==200
    assert claim(client).json()['job'] is None


def test_background_is_bounded_and_requires_online_workers(client):
    for _ in range(5): store.tick()
    assert client.get('/api/stats').json()['jobs']=={}
    client.post('/internal/workers/2.1/heartbeat',headers=auth(),json={})
    for _ in range(6):
        with store.transaction() as c:
            c.execute("UPDATE settings SET value='0' WHERE key='last_background'")
        store.tick()
    assert client.get('/api/stats').json()['jobs']['queued']==2


def test_pagination_order_and_data_survive_init(client):
    # Populate an isolated test DB only; production never receives these rows.
    with store.transaction() as c:
        for i in range(51):
            j=store.enqueue(c,f'test object {i}')
            c.execute("UPDATE jobs SET state='succeeded' WHERE id=?",(j['id'],))
            c.execute('INSERT INTO images VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (f'image-{i:03}',j['id'],j['name'],'test.png','test.png','2.1','sd-turbo',float(i),128,128,'hash',42))
    first=client.get('/api/images').json();second=client.get('/api/images?page=2').json()
    assert len(first['items'])==50 and len(second['items'])==1
    assert first['items'][0]['name']=='test object 50'
    store.init()
    assert client.get('/api/stats').json()['total_images']==51
