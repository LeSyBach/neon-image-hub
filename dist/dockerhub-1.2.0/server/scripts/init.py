"""Initialize local credentials without printing secrets or overwriting them."""
import json
from pathlib import Path
import secrets

root=Path(__file__).resolve().parents[1]
for folder in ['.credentials','data/hub/images','data/ntfy','data/beszel','logs','backups','test-results']:
    (root/folder).mkdir(parents=True,exist_ok=True)
env=root/'.env'
if not env.exists():
    env.write_text('\n'.join([
        'ADMIN_TOKEN='+secrets.token_urlsafe(36),
        'NTFY_USER=neon', 'NTFY_PASSWORD='+secrets.token_urlsafe(24),
        'NTFY_TOPIC=neon-'+secrets.token_hex(8),
        'BESZEL_EMAIL=admin@neon.local', 'BESZEL_PASSWORD='+secrets.token_urlsafe(24),
        'WEB_BIND=127.0.0.1','WEB_PORT=8080','WORKER_BIND=127.0.0.1','WORKER_PORT=8081',
        'MONITOR_BIND=127.0.0.1','MONITOR_PORT=8090','NTFY_BIND=127.0.0.1','NTFY_PORT=8091',
        'LEASE_SECONDS=180','WORKER_TIMEOUT=90','MAX_ATTEMPTS=3','MAX_PENDING=100',''
    ]))
workers=root/'.credentials/workers.json'
if not workers.exists():
    workers.write_text(json.dumps({
        '2.1':{'models':['sd-turbo'],'allowed_models':['sd-turbo','dreamshaper-8-lcm']},
        '3.1':{'models':['dreamshaper-8-lcm'],'allowed_models':['sd-turbo','dreamshaper-8-lcm']},
        '4.1':{'models':['sd-turbo'],'allowed_models':['sd-turbo','dreamshaper-8-lcm']},
    },indent=2))
print('Initialized project directories and private credentials; existing credentials preserved.')
