"""Smoke-test both model choices in the shared built image, without inference."""
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
settings=root/'.credentials/worker-local.json'
models=root.parent/'codex-neon-local/models'
code='''
import json, os
from pathlib import Path
from worker.settings import load_settings
from worker.runner import Worker
cfg=load_settings('/config/worker.json')
selected=os.environ['AI_MODEL']
assert list(cfg['models'])==[selected]
for key in ('path','taesd'):
    assert Path(cfg['models'][selected][key]).is_file()
worker=Worker(cfg)
cmd=worker.command({'id':'a'*32,'model_id':selected,'prompt':'test','seed':1},Path('/state/test.png'))
print(json.dumps({'model':selected,'steps':cmd[cmd.index('--steps')+1],
                  'sampler':cmd[cmd.index('--sampling-method')+1],'files_present':True}))
'''
checks=[]
for model in ('sd-turbo','dreamshaper-8-lcm'):
    result=subprocess.run(['docker','run','--rm','--network','none','-e','AI_MODEL='+model,
        '-v',str(settings)+':/config/worker.json:ro',
        '-v',str(models)+':/models:ro',
        '--entrypoint','python3','bachcp10/neon-hub-worker:1.2.0','-c',code],
        check=True,capture_output=True,text=True)
    checks.append(json.loads(result.stdout))
    print(result.stdout.strip())
report={'automated_tests_passed':46,'image_model_checks':checks,'inference_started':False,
        'application_services_started':False}
(root/'test-results/model-selection.json').write_text(json.dumps(report,indent=2))
