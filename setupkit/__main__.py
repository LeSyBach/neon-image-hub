import argparse
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import shutil
import re
import uuid
import sys
from urllib.parse import urlsplit
import zipfile

VERSION = '1.2.0'
IDS = ('2.1', '3.1', '4.1')


def origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ValueError('Server URL must be an HTTP(S) origin such as http://100.x.y.z:8081')
    return value.rstrip('/')


def extract(payload, role, target):
    target = Path(target).resolve()
    if target.exists() and any(target.iterdir()):
        raise ValueError('Output folder must be empty. Existing configuration/data was left unchanged.')
    with zipfile.ZipFile(payload) as archive:
        members = [item for item in archive.infolist() if item.filename.startswith(role + '/')]
        if not members:
            raise ValueError('Deployment payload is incomplete')
        for member in members:
            relative = Path(member.filename).relative_to(role)
            destination = (target / relative).resolve()
            if not destination.is_relative_to(target):
                raise ValueError('Invalid deployment payload path')
        target.mkdir(parents=True, exist_ok=True)
        for member in members:
            relative = Path(member.filename).relative_to(role)
            destination = target / relative
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(member))
    return target


def configure_server(args, payload):
    ip = str(ipaddress.IPv4Address(args.server_ip))
    target = extract(payload, 'server', args.output)
    subprocess.run([sys.executable, str(target / 'scripts/init.py')], check=True)
    path = target / '.env'
    lines = path.read_text().splitlines()
    lines = ['WORKER_BIND=' + ip if line.startswith('WORKER_BIND=') else line for line in lines]
    path.write_text('\n'.join(lines) + '\n')
    path.chmod(0o600)
    (target / '.credentials/workers.json').chmod(0o600)
    print('Server configuration created. Run docker compose pull, then docker compose up -d in the host folder.')


def configure_worker(args, payload):
    server = origin(args.server_url)
    selected = args.model or ('dreamshaper-8-lcm' if args.worker_id == '3.1' else 'sd-turbo')
    with zipfile.ZipFile(payload) as archive:
        catalog = json.loads(archive.read('server/worker-models.json'))
    if selected not in catalog:
        raise ValueError('Unsupported model')
    target = extract(payload, 'worker', args.output)
    cfg = {'worker_id': args.worker_id, 'server_url': server,
           'state_dir': '/state', 'threads': args.cpus, 'generation_timeout': 900,
           'minimum_free_bytes': 1024**3, 'models': {selected: catalog[selected]}}
    (target / 'worker-settings.json').write_text(json.dumps(cfg, indent=2))
    (target / 'worker-settings.json').chmod(0o600)
    (target / '.env').write_text(f'AI_MODEL={selected}\nWORKER_CPUS={args.cpus}\nWORKER_MEMORY=5g\n')
    (target / '.env').chmod(0o600)
    print(f'Worker {args.worker_id} configuration created; model={selected}.')
    print('Put model files in models/, then run docker compose pull and docker compose up -d in the host folder.')


def upgrade(args):
    target=Path(args.output).resolve()
    compose=target/'compose.yaml'
    text=compose.read_text()
    pattern=r'(image:\s*bachcp10/neon-hub-(?:api|worker):)[A-Za-z0-9_.-]+'
    updated,count=re.subn(pattern,lambda match:match[1]+VERSION,text)
    if not count:
        raise ValueError('No recognized Neon Hub image reference in compose.yaml')
    changes={compose:updated}
    for path in (target/'worker-settings.json',target/'.credentials/workers.json'):
        if not path.is_file():
            continue
        cfg=json.loads(path.read_text())
        if path.name=='worker-settings.json':
            cfg.pop('token',None)
        else:
            for worker in cfg.values():
                worker.pop('token',None)
        changes[path]=json.dumps(cfg,indent=2)
    for path,content in changes.items():
        if content==path.read_text():
            continue
        backup=path.with_name(path.name+'.before-'+VERSION)
        if not backup.exists():
            shutil.copy2(path,backup)
        temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
        temp.write_text(content)
        temp.chmod(path.stat().st_mode & 0o777)
        temp.replace(path)
    print('Updated image references to '+VERSION+' and removed worker bearer tokens. Existing data and .env preserved.')
    print('Now run docker compose pull and docker compose up -d. Upgrade the server before connecting new workers.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Create deployment files directly from the Docker image (no ZIP transfer).')
    sub = parser.add_subparsers(dest='role', required=True)
    server = sub.add_parser('server', help='Initialize a NEW server in an empty bind-mounted folder')
    server.add_argument('--output', default='/setup')
    server.add_argument('--server-ip', required=True, help='Tailscale IPv4 of this server VM')
    worker = sub.add_parser('worker', help='Initialize a NEW worker in an empty bind-mounted folder')
    worker.add_argument('--output', default='/setup')
    worker.add_argument('--worker-id', choices=IDS, required=True)
    worker.add_argument('--server-url', required=True)
    worker.add_argument('--model', choices=('sd-turbo', 'dreamshaper-8-lcm'))
    worker.add_argument('--cpus', type=int, choices=range(1, 65), default=4)
    update=sub.add_parser('upgrade',help='Update an existing deployment to '+VERSION+' without reinitializing data')
    update.add_argument('--output',default='/setup')
    args = parser.parse_args(argv)
    try:
        if args.role == 'upgrade':
            upgrade(args)
            return
        payload = Path(__file__).with_name('payload.zip')
        if args.role == 'server':
            configure_server(args, payload)
        else:
            configure_worker(args, payload)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError):
        # Do not include token contents or arbitrary exception data in logs.
        parser.exit(2, 'Setup failed: invalid input, a nonempty output folder, or a missing/unwritable setup file. Existing files are not overwritten.\n')


if __name__ == '__main__':
    main()
