"""Build the current public setup payload without obsolete release folders."""
import argparse
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--output',default=str(root/'setupkit/payload.zip'))
args=parser.parse_args()
source=root/'dist/dockerhub-1.2.0'
files=[]
for role in ('server','worker'):
    folder=source/role
    if not (folder/'compose.yaml').is_file():
        raise RuntimeError('Missing current deployment assets: '+role)
    files.append(folder)
    files.extend(folder.rglob('*'))
for path in files:
    relative=path.relative_to(source)
    if '.credentials' in relative.parts or path.name in ('.env','worker-settings.json','hub.sqlite3'):
        raise RuntimeError('Private configuration must not be packaged')
    if path.suffix in ('.safetensors','.gguf'):
        raise RuntimeError('Model weights must remain outside the image')
required_dirs=('worker/models/','worker/worker-state/','server/worker-template/models/','server/worker-template/worker-state/')
output=Path(args.output)
output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
    names=set()
    for path in sorted(files):
        archive.write(path,path.relative_to(source))
        name=path.relative_to(source).as_posix()+('/' if path.is_dir() else '')
        names.add(name)
    for name in required_dirs:
        if name not in names:
            archive.writestr(name,b'')
print('Current public deployment payload created:',output.name)
