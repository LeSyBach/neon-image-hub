import json
import os
from pathlib import Path

DATA = Path(os.getenv('DATA_DIR', '/data'))
DATABASE = DATA / 'hub.sqlite3'
IMAGES = DATA / 'images'
LEASE_SECONDS = int(os.getenv('LEASE_SECONDS', '180'))
WORKER_TIMEOUT = int(os.getenv('WORKER_TIMEOUT', '90'))
MAX_ATTEMPTS = int(os.getenv('MAX_ATTEMPTS', '3'))
MAX_PENDING = int(os.getenv('MAX_PENDING', '100'))
MAX_UPLOAD = 10 * 1024 * 1024
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', '')
CREDENTIALS = Path(os.getenv('WORKER_CONFIG', '/config/workers.json'))
NEON_STYLE = 'vivid cyan and magenta glowing neon tubes, luminous outline, plain black background, single clearly recognizable subject, simple composition, no lettering, no watermark'


def workers():
    if not CREDENTIALS.exists():
        return {}
    return json.loads(CREDENTIALS.read_text())
