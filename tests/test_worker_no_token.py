import json
from io import BytesIO
from pathlib import Path

from worker import client as protocol
from worker.runner import Worker


def test_client_does_not_send_legacy_bearer_header(monkeypatch):
    seen=[]
    class Opener:
        def open(self,request,timeout):
            seen.append(request)
            return BytesIO(json.dumps({'job':None}).encode())
    monkeypatch.setattr(protocol,'build_opener',lambda *_:Opener())
    protocol.Client('http://server:8081','2.1','legacy-ignored-token').claim()
    assert not seen[0].has_header('Authorization')


def test_runner_accepts_settings_without_token(tmp_path):
    cfg={'worker_id':'2.1','server_url':'http://server:8081','state_dir':str(tmp_path),
         'models':{'sd-turbo':{'path':'/models/test'}}}
    assert Worker(cfg).client.prefix=='/internal/workers/2.1'
