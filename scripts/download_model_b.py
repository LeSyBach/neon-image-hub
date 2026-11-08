"""Fetch fixed model revision in bounded HTTP ranges, verify full SHA256.

Supports resuming the partial sequential download at the target path.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import time
from urllib.request import Request,urlopen

target=Path('D:/codex-neon-local/models/DreamShaper8_LCM.safetensors')
total=2133804992
checksum='a4f3e1526c5dc4fcbe342f5c410d83ae202c7a415fcefcbb92e0f93fcd0a87c3'
url='https://huggingface.co/Lykon/dreamshaper-8-lcm/resolve/4645d8bc6a8e6b106d21606d63e8460cdad4f1a6/DreamShaper8_LCM.safetensors'
start=target.stat().st_size if target.exists() else 0
if start>total: raise RuntimeError('Unexpected existing file size')
part_dir=target.with_suffix('.parts');part_dir.mkdir(exist_ok=True)
jobs=[]
step=max(1,(total-start+7)//8)
for i,begin in enumerate(range(start,total,step)):
    jobs.append((i,begin,min(total-1,begin+step-1)))

def fetch(item):
    i,begin,end=item
    path=part_dir/f'{i}-{begin}-{end}.part'
    have=path.stat().st_size if path.exists() else 0
    if have==end-begin+1:return path
    for attempt in range(4):
        try:
            have=path.stat().st_size if path.exists() else 0
            request=Request(url+f'?part={begin}',headers={'Range':f'bytes={begin+have}-{end}'})
            with urlopen(request,timeout=30) as response:
                expected=f'bytes {begin+have}-{end}/{total}'
                if response.status!=206 or response.headers.get('Content-Range')!=expected:
                    raise RuntimeError('Server did not honor the requested byte range')
                with path.open('ab') as output:
                    while chunk:=response.read(1024*1024):output.write(chunk)
            if path.stat().st_size!=end-begin+1:raise OSError('Incomplete range')
            print(f'Range {i+1}/{len(jobs)} downloaded',flush=True)
            return path
        except OSError:
            if attempt==3:raise
            time.sleep(2)

with ThreadPoolExecutor(max_workers=8) as pool:parts=list(pool.map(fetch,jobs))
with target.open('ab') as output:
    for path in parts:
        with path.open('rb') as part:
            while chunk:=part.read(1024*1024):output.write(chunk)
sha=hashlib.sha256()
with target.open('rb') as file:
    while chunk:=file.read(1024*1024):sha.update(chunk)
if target.stat().st_size!=total or sha.hexdigest()!=checksum:
    raise RuntimeError('Model checksum mismatch; do not load this file')
for path in parts:path.unlink()
part_dir.rmdir()
print('Model B downloaded and verified against author SHA256.',flush=True)
