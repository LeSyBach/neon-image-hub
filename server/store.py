"""Durable central queue. Short IMMEDIATE transactions serialize claim/dedup.

Workers only call HTTP; the database is never shared over the network.
"""
from contextlib import contextmanager
import json
import re
import secrets
import sqlite3
import time
import uuid

from . import config


class Conflict(Exception):
    pass


class Busy(Exception):
    pass


def connect():
    c = sqlite3.connect(config.DATABASE, timeout=20, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA busy_timeout=20000')
    c.execute('PRAGMA foreign_keys=ON')
    return c


@contextmanager
def transaction():
    c = connect()
    try:
        c.execute('BEGIN IMMEDIATE')
        yield c
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally:
        c.close()


def init():
    config.DATA.mkdir(parents=True, exist_ok=True)
    config.IMAGES.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        # DELETE journal also works on bind mounts from Windows; no shared WAL
        # file across the API/scheduler processes or a network filesystem.
        c.execute('PRAGMA journal_mode=DELETE')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, source TEXT NOT NULL,
          priority INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
          created REAL NOT NULL, updated REAL NOT NULL, worker_id TEXT,
          lease TEXT, expires REAL, attempts INTEGER NOT NULL DEFAULT 0,
          model_id TEXT, error TEXT, seed INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS active_name ON jobs(name)
          WHERE state IN ('queued', 'running');
        CREATE INDEX IF NOT EXISTS queue_order ON jobs(state,priority DESC,created);
        CREATE TABLE IF NOT EXISTS images (
          id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
          name TEXT NOT NULL, filename TEXT NOT NULL, relative_path TEXT NOT NULL,
          worker_id TEXT NOT NULL, model_id TEXT NOT NULL, created REAL NOT NULL,
          width INTEGER NOT NULL, height INTEGER NOT NULL, sha256 TEXT NOT NULL,
          seed INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS image_names ON images(name);
        CREATE INDEX IF NOT EXISTS image_order ON images(created DESC,id DESC);
        CREATE TABLE IF NOT EXISTS workers (
          id TEXT PRIMARY KEY, last_seen REAL NOT NULL, models TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL NOT NULL,
          module TEXT NOT NULL, event TEXT NOT NULL, job_id TEXT, worker_id TEXT,
          detail TEXT NOT NULL, delivered REAL, tries INTEGER NOT NULL DEFAULT 0,
          next_try REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        INSERT OR IGNORE INTO settings VALUES ('background_enabled','true');
        INSERT OR IGNORE INTO settings VALUES ('background_interval','30');
        INSERT OR IGNORE INTO settings VALUES ('last_background','0');
        ''')


def event(c, module, kind, job_id=None, worker_id=None, **detail):
    c.execute('INSERT INTO events(created,module,event,job_id,worker_id,detail) VALUES(?,?,?,?,?,?)',
              (time.time(), module, kind, job_id, worker_id,
               json.dumps(detail, ensure_ascii=False)[:4000]))


def normalize(name):
    name = ' '.join(name.lower().strip().split())
    if not 2 <= len(name) <= 100 or not re.fullmatch(r"[a-z0-9][a-z0-9 '\-,]*", name):
        raise ValueError('Nhập tên tiếng Anh từ 2 đến 100 ký tự, dùng chữ, số, khoảng trắng hoặc dấu gạch nối.')
    return name


def image_dict(row):
    if row is None:
        return None
    d = dict(row)
    d.pop('relative_path', None)
    d['url'] = f'/api/images/{d["id"]}/file'
    return d


def job_dict(c, row):
    d = {k: row[k] for k in ('id','name','source','state','created','updated','attempts')}
    d['image'] = image_dict(c.execute('SELECT * FROM images WHERE job_id=?', (row['id'],)).fetchone())
    d['available_workers'] = c.execute('SELECT COUNT(*) FROM workers WHERE last_seen>?',
                                      (time.time()-config.WORKER_TIMEOUT,)).fetchone()[0]
    return d


def list_images(name='', page=1, limit=50):
    with connect() as c:
        # INSTR is a literal substring search: %, _ never become SQL wildcards.
        total = c.execute('SELECT COUNT(*) FROM images WHERE instr(name,?)>0', (name,)).fetchone()[0]
        rows = c.execute('SELECT * FROM images WHERE instr(name,?)>0 ORDER BY created DESC,id DESC LIMIT ? OFFSET ?',
                         (name, limit, (page-1)*limit)).fetchall()
        return {'items':[image_dict(r) for r in rows], 'total':total, 'page':page,
                'page_size':limit, 'pages':max(1,(total+limit-1)//limit)}


def enqueue(c, name, source='search'):
    active = c.execute("SELECT * FROM jobs WHERE name=? AND state IN ('queued','running')", (name,)).fetchone()
    if active:
        if source == 'search' and active['priority'] < 100:
            c.execute('UPDATE jobs SET priority=100,updated=? WHERE id=?', (time.time(),active['id']))
        return active
    count = c.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]
    if count >= config.MAX_PENDING:
        raise Busy('Hệ thống đang nhận nhiều yêu cầu. Vui lòng thử lại sau ít phút.')
    job_id = uuid.uuid4().hex
    now = time.time()
    c.execute('INSERT INTO jobs(id,name,source,priority,created,updated,seed) VALUES(?,?,?,?,?,?,?)',
              (job_id,name,source,100 if source=='search' else 10,now,now,secrets.randbelow(2**31)))
    event(c,'dispatch','job_queued',job_id,name=name,source=source)
    return c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()


def search(name):
    name = normalize(name)
    with transaction() as c:
        row = c.execute('SELECT * FROM images WHERE instr(name,?)>0 ORDER BY created DESC,id DESC LIMIT 1',(name,)).fetchone()
        event(c,'web','search',name=name,cache_hit=bool(row))
        if row:
            return {'state':'found','name':name,'image':image_dict(row)}
        job = enqueue(c,name)
        return {'state':'pending','name':name,'job':job_dict(c,job)}


def get_job(job_id):
    with connect() as c:
        row = c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        return job_dict(c,row) if row else None


def reap(c):
    now = time.time()
    rows = c.execute("SELECT * FROM jobs WHERE state='running' AND expires<?",(now,)).fetchall()
    for row in rows:
        state = 'queued' if row['attempts'] < config.MAX_ATTEMPTS else 'failed'
        c.execute('UPDATE jobs SET state=?,worker_id=NULL,lease=NULL,expires=NULL,updated=?,error=? WHERE id=?',
                  (state,now,'Worker không gia hạn công việc',row['id']))
        event(c,'dispatch','lease_expired',row['id'],row['worker_id'],next_state=state)


def heartbeat(worker_id, models, job_id=None, lease=None):
    now = time.time()
    with transaction() as c:
        old = c.execute('SELECT * FROM workers WHERE id=?',(worker_id,)).fetchone()
        if not old or old['last_seen'] < now-config.WORKER_TIMEOUT:
            event(c,'worker','worker_online',worker_id=worker_id,models=models)
        c.execute('INSERT INTO workers VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,models=excluded.models',
                  (worker_id,now,json.dumps(models)))
        if job_id:
            row = owned_job(c,worker_id,job_id,lease)
            if row['state'] != 'running':
                raise Conflict('Công việc không còn chạy')
            c.execute('UPDATE jobs SET expires=?,updated=? WHERE id=?',(now+config.LEASE_SECONDS,now,job_id))
    return {'ok':True,'heartbeat_after':20,'lease_seconds':config.LEASE_SECONDS}


def owned_job(c, worker_id, job_id, lease):
    row = c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
    if (not row or row['worker_id'] != worker_id or not row['lease'] or not lease or
            not secrets.compare_digest(row['lease'],lease)):
        raise Conflict('Quyền xử lý công việc không còn hợp lệ')
    if row['state']=='running' and row['expires'] < time.time():
        raise Conflict('Công việc đã hết thời gian giữ chỗ; gửi heartbeat để gia hạn khi đang chạy')
    return row


def claim(worker_id, models):
    with transaction() as c:
        reap(c)
        running = c.execute("SELECT id FROM jobs WHERE state='running' AND worker_id=?",(worker_id,)).fetchone()
        if running:
            raise Conflict('Worker đang có một công việc chưa hoàn tất')
        row = c.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY priority DESC,created,id LIMIT 1").fetchone()
        if not row:
            return None
        now=time.time(); lease=secrets.token_urlsafe(32)
        model_id=models[0]
        c.execute("UPDATE jobs SET state='running',worker_id=?,lease=?,expires=?,attempts=attempts+1,updated=?,model_id=?,error=NULL WHERE id=?",
                  (worker_id,lease,now+config.LEASE_SECONDS,now,model_id,row['id']))
        event(c,'dispatch','job_claimed',row['id'],worker_id,model_id=model_id)
        return {'id':row['id'],'name':row['name'],'seed':row['seed'],'model_id':model_id,
                'prompt':f"a colorful neon sign illustration of {row['name']}, {config.NEON_STYLE}", 'style':'Neon',
                'lease':lease,'lease_seconds':config.LEASE_SECONDS,'heartbeat_after':20,
                'minimum_width':128,'minimum_height':128}


def failed(worker_id, job_id, lease, message):
    with transaction() as c:
        row=owned_job(c,worker_id,job_id,lease)
        if row['state']!='running':
            raise Conflict('Công việc không còn chạy')
        state='queued' if row['attempts'] < config.MAX_ATTEMPTS else 'failed'
        c.execute('UPDATE jobs SET state=?,worker_id=NULL,lease=NULL,expires=NULL,updated=?,error=? WHERE id=?',
                  (state,time.time(),message[:500],job_id))
        event(c,'worker','generation_failed',job_id,worker_id,message=message[:500],next_state=state)
        return {'state':state}


def stats():
    now=time.time()
    with connect() as c:
        counts={r['worker_id']:r['n'] for r in c.execute('SELECT worker_id,COUNT(*) n FROM images GROUP BY worker_id')}
        states={r['state']:r['n'] for r in c.execute('SELECT state,COUNT(*) n FROM jobs GROUP BY state')}
        seen={r['id']:dict(r) for r in c.execute('SELECT * FROM workers')}
        items=[]
        for worker_id, cfg in config.workers().items():
            last=seen.get(worker_id,{}).get('last_seen',0)
            busy=c.execute("SELECT id FROM jobs WHERE state='running' AND worker_id=? AND expires>?",(worker_id,now)).fetchone()
            active=json.loads(seen[worker_id]['models']) if worker_id in seen else cfg['models']
            items.append({'id':worker_id,'models':active,'images':counts.get(worker_id,0),
                          'status':'offline' if last < now-config.WORKER_TIMEOUT else ('busy' if busy else 'idle')})
        return {'total_images':sum(counts.values()),'workers':items,'jobs':states,
                'background_enabled':c.execute("SELECT value FROM settings WHERE key='background_enabled'").fetchone()[0]=='true'}


def tick():
    with transaction() as c:
        reap(c)
        settings={r['key']:r['value'] for r in c.execute('SELECT * FROM settings')}
        now=time.time()
        if settings['background_enabled']!='true' or now-float(settings['last_background'])<int(settings['background_interval']):
            return
        online=c.execute('SELECT COUNT(*) FROM workers WHERE last_seen>?',(now-config.WORKER_TIMEOUT,)).fetchone()[0]
        pending=c.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]
        # Never create an unbounded background backlog when workers are offline.
        if not online or pending>=min(config.MAX_PENDING,online*2):
            return
        topics=['black dog','white cat','red bicycle','blue butterfly','green turtle','red apple',
                'yellow flower','white rabbit','orange fox','blue whale','red mushroom','green frog',
                'purple jellyfish','red train','blue bird','yellow duck','green tree','orange pumpkin',
                'white horse','red rose','blue fish','yellow banana','green cactus','purple orchid']
        ranked=[]
        for name in topics:
            if c.execute("SELECT 1 FROM jobs WHERE name=? AND state IN ('queued','running')",(name,)).fetchone():
                continue
            n=c.execute('SELECT COUNT(*) FROM images WHERE name=?',(name,)).fetchone()[0]
            ranked.append((n,name))
        if ranked:
            ranked.sort()
            enqueue(c,ranked[0][1],'background')
            c.execute("UPDATE settings SET value=? WHERE key='last_background'",(str(now),))


def retry_job(job_id):
    with transaction() as c:
        row=c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not row or row['state']!='failed':
            raise Conflict('Chỉ thử lại công việc đang ở trạng thái lỗi')
        active=c.execute("SELECT * FROM jobs WHERE name=? AND state IN ('queued','running')",(row['name'],)).fetchone()
        if active:
            return job_dict(c,active)
        c.execute("UPDATE jobs SET state='queued',attempts=0,updated=?,error=NULL WHERE id=?",(time.time(),job_id))
        event(c,'dispatch','job_retried',job_id)
        return job_dict(c,c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone())
