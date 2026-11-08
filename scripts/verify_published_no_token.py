import json
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
expected={
    'bachcp10/neon-hub-api:1.2.0':'sha256:0da045e9f543d0064def4b075fd4d4885373dea5c8c110010b95fa0260b69a3d',
    'bachcp10/neon-hub-worker:1.2.0':'sha256:5d986938bab2050db9da81eb2fa1545c5e45aaa93837100498d4434f7dafc7b2',
}
images={}
with tempfile.TemporaryDirectory(prefix='neon-hub-anonymous-') as temp:
    Path(temp,'config.json').write_text('{}')
    for reference,digest in expected.items():
        result=subprocess.run(['docker','--config',temp,'pull',reference],capture_output=True,text=True,check=True)
        assert digest in result.stdout
        images[reference]={'digest':digest,'anonymous_pull':True}
        print('Anonymous pull verified:',reference)
path=root/'dist/dockerhub-1.2.0/verification.json'
report=json.loads(path.read_text())
report['published_images']=images
path.write_text(json.dumps(report,indent=2))
manifest={'version':'1.2.0','architecture':'linux/amd64','bootstrap_from_image':True,'worker_token_required':False,'images':images,
          'private_credentials_in_images':False,'model_weights_in_images':False}
(path.parent/'release.json').write_text(json.dumps(manifest,indent=2))
lockpath=root/'IMAGE-LOCK.json'
lock=json.loads(lockpath.read_text(encoding='utf-8-sig'))
for reference in expected:
    info=json.loads(subprocess.run(['docker','image','inspect',reference],capture_output=True,text=True,check=True).stdout)[0]
    item={'image':reference,'id':info['Id'],'digests':info.get('RepoDigests',[])}
    lock=[entry for entry in lock if entry['image']!=reference]
    lock.append(item)
lockpath.write_text(json.dumps(lock,indent=2))
result=subprocess.run(['docker','ps','--filter','name=neon-','--format','{{.Names}}'],capture_output=True,text=True,check=True)
assert not result.stdout.strip()
print('Public bootstrap release verified; application services remain stopped.')
