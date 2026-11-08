import hashlib
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
import secrets
import time
import uuid

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from . import config, store

Image.MAX_IMAGE_PIXELS = 16_777_216
log=logging.getLogger('neon.api')


@asynccontextmanager
async def lifespan(app):
    store.init()
    if not config.ADMIN_TOKEN or not config.workers():
        raise RuntimeError('Run scripts/init.py before starting: admin and worker configuration is required.')
    with store.transaction() as c:
        store.event(c,'api','service_started')
    yield


app=FastAPI(title='Neon Image Hub Server',version='1.2.0',lifespan=lifespan,
            docs_url='/internal/docs',redoc_url=None,openapi_url='/internal/openapi.json')


@app.exception_handler(store.Conflict)
async def conflict_handler(request, exc):
    return JSONResponse(status_code=409,content={'detail':str(exc)})


@app.exception_handler(store.Busy)
async def busy_handler(request,exc):
    return JSONResponse(status_code=429,content={'detail':str(exc)},headers={'Retry-After':'20'})


def bearer(value):
    return value[7:] if value and value.startswith('Bearer ') else ''


def admin(authorization: str | None=Header(default=None)):
    if not config.ADMIN_TOKEN or not secrets.compare_digest(bearer(authorization),config.ADMIN_TOKEN):
        raise HTTPException(401,'Cần khóa quản trị')


def worker(worker_id: str):
    cfg=config.workers().get(worker_id)
    if not cfg:
        raise HTTPException(403,'ID worker chưa được đăng ký trên server')
    return cfg


class Search(BaseModel):
    name: str=Field(min_length=2,max_length=100)


class Heartbeat(BaseModel):
    job_id: str | None=None
    lease: str | None=None
    models: list[str] | None=Field(default=None,min_length=1,max_length=8)


class Claim(BaseModel):
    models: list[str] | None=Field(default=None,min_length=1,max_length=8)


def selected_models(cfg, requested):
    allowed = cfg.get('allowed_models', cfg['models'])
    models = cfg['models'] if requested is None else requested
    if not models or any(model not in allowed for model in models):
        raise HTTPException(403,'Mô hình chưa được cấp quyền cho worker này')
    return list(dict.fromkeys(models))


class Failure(BaseModel):
    lease: str
    message: str=Field(min_length=1,max_length=500)


class Background(BaseModel):
    enabled: bool
    interval_seconds: int=Field(default=30,ge=10,le=3600)


@app.get('/api/health')
def health():
    with store.connect() as c:
        c.execute('SELECT 1')
    return {'status':'ok','service':'neon-api'}


@app.get('/api/images')
def images(q: str='', page: int=Query(1,ge=1,le=100000)):
    if q:
        try:
            q=store.normalize(q)
        except ValueError as e:
            raise HTTPException(422,str(e))
    return store.list_images(q,page)


@app.post('/api/search')
def search(body: Search):
    try:
        result=store.search(body.name)
    except ValueError as e:
        raise HTTPException(422,str(e))
    return JSONResponse(result,status_code=200 if result['state']=='found' else 202)


@app.get('/api/jobs/{job_id}')
def job(job_id: str):
    row=store.get_job(job_id)
    if not row:
        raise HTTPException(404,'Không tìm thấy yêu cầu xử lý này')
    return row


@app.get('/api/stats')
def stats():
    return store.stats()


@app.get('/api/images/{image_id}/file')
def image_file(image_id: str):
    with store.connect() as c:
        row=c.execute('SELECT * FROM images WHERE id=?',(image_id,)).fetchone()
    if not row:
        raise HTTPException(404,'Ảnh không tồn tại')
    path=(config.IMAGES/row['relative_path']).resolve()
    if not path.is_relative_to(config.IMAGES.resolve()) or not path.is_file():
        raise HTTPException(404,'File ảnh hiện không khả dụng')
    return FileResponse(path,media_type='image/png',filename=row['filename'],content_disposition_type='inline',
                        headers={'Cache-Control':'public, max-age=86400','X-Content-Type-Options':'nosniff'})


@app.post('/internal/workers/{worker_id}/heartbeat')
def heartbeat(worker_id: str, body: Heartbeat, cfg=Depends(worker)):
    return store.heartbeat(worker_id,selected_models(cfg,body.models),body.job_id,body.lease)


@app.post('/internal/workers/{worker_id}/claim')
def claim(worker_id: str,body: Claim | None=None,cfg=Depends(worker)):
    models=selected_models(cfg, None if body is None else body.models)
    store.heartbeat(worker_id,models)
    item=store.claim(worker_id,models)
    return {'job':item,'poll_after':3 if item else 10}


@app.post('/internal/workers/{worker_id}/jobs/{job_id}/fail')
def fail(worker_id: str,job_id: str,body: Failure,cfg=Depends(worker)):
    return store.failed(worker_id,job_id,body.lease,body.message)


@app.post('/internal/workers/{worker_id}/jobs/{job_id}/complete')
def complete(worker_id: str,job_id: str,lease: str=Form(...),model_id: str=Form(...),
             file: UploadFile=File(...),cfg=Depends(worker)):
    # Check the lease before spending CPU on decoding. A completion replay is
    # idempotent and cannot overwrite an already committed image.
    with store.transaction() as c:
        row=store.owned_job(c,worker_id,job_id,lease)
        if row['state']=='succeeded':
            return {'image':store.image_dict(c.execute('SELECT * FROM images WHERE job_id=?',(job_id,)).fetchone()),'reused':True}
        if row['state']!='running' or model_id!=row['model_id'] or model_id not in cfg.get('allowed_models',cfg['models']):
            raise store.Conflict('Trạng thái hoặc mô hình không khớp công việc')
    raw=file.file.read(config.MAX_UPLOAD+1)
    if len(raw)>config.MAX_UPLOAD:
        raise HTTPException(413,'File tối đa 10 MB')
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format not in ('PNG','JPEG'):
                raise ValueError('Chỉ nhận ảnh PNG hoặc JPEG')
            width,height=probe.size
            if min(width,height)<128 or max(width,height)>4096:
                raise ValueError('Kích thước ảnh phải từ 128 đến 4096 pixel mỗi chiều')
            probe.verify()
        with Image.open(io.BytesIO(raw)) as image:
            buf=io.BytesIO()
            image.convert('RGB').save(buf,format='PNG')
            encoded=buf.getvalue()
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError) as e:
        raise HTTPException(422,f'Ảnh không hợp lệ: {e}')
    folder=config.IMAGES/job_id
    folder.mkdir(parents=True,exist_ok=True)
    temp=folder/f'.upload-{uuid.uuid4().hex}.tmp'
    try:
        temp.write_bytes(encoded)
        with store.transaction() as c:
            row=store.owned_job(c,worker_id,job_id,lease)
            if row['state']=='succeeded':
                return {'image':store.image_dict(c.execute('SELECT * FROM images WHERE job_id=?',(job_id,)).fetchone()),'reused':True}
            if row['state']!='running':
                raise store.Conflict('Công việc không còn chạy')
            filename=f"{row['name']} {worker_id}.png"
            destination=folder/filename
            os.replace(temp,destination)
            image_id=uuid.uuid4().hex
            c.execute('INSERT INTO images VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                      (image_id,job_id,row['name'],filename,f'{job_id}/{filename}',worker_id,model_id,
                       time.time(),width,height,hashlib.sha256(encoded).hexdigest(),row['seed']))
            c.execute("UPDATE jobs SET state='succeeded',updated=?,error=NULL WHERE id=?",(time.time(),job_id))
            store.event(c,'storage','image_saved',job_id,worker_id,name=row['name'],model_id=model_id,width=width,height=height)
            return {'image':store.image_dict(c.execute('SELECT * FROM images WHERE id=?',(image_id,)).fetchone()),'reused':False}
    finally:
        temp.unlink(missing_ok=True)


@app.get('/internal/status',dependencies=[Depends(admin)])
def status():
    with store.connect() as c:
        jobs=[dict(r) for r in c.execute('SELECT id,name,source,state,worker_id,model_id,attempts,error,created,updated FROM jobs ORDER BY created DESC LIMIT 100')]
        events=[dict(r) for r in c.execute('SELECT id,created,module,event,job_id,worker_id,detail,delivered,tries FROM events ORDER BY id DESC LIMIT 100')]
    return {'stats':store.stats(),'jobs':jobs,'events':events}


@app.put('/internal/settings/background',dependencies=[Depends(admin)])
def background(body: Background):
    with store.transaction() as c:
        c.execute("UPDATE settings SET value=? WHERE key='background_enabled'",('true' if body.enabled else 'false',))
        c.execute("UPDATE settings SET value=? WHERE key='background_interval'",(str(body.interval_seconds),))
        store.event(c,'scheduler','background_settings',enabled=body.enabled,interval_seconds=body.interval_seconds)
    return body.model_dump()


@app.post('/internal/jobs/{job_id}/retry',dependencies=[Depends(admin)])
def retry(job_id: str):
    return store.retry_job(job_id)


@app.post('/internal/jobs/{job_id}/cancel',dependencies=[Depends(admin)])
def cancel(job_id: str):
    with store.transaction() as c:
        row=c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if not row or row['state'] not in ('queued','running','failed'):
            raise store.Conflict('Không thể hủy công việc này')
        c.execute("UPDATE jobs SET state='cancelled',lease=NULL,expires=NULL,updated=? WHERE id=?",(time.time(),job_id))
        store.event(c,'dispatch','job_cancelled',job_id)
    return {'ok':True}
