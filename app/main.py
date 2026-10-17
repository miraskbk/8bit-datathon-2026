import asyncio
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import joblib
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.vision import analyze

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv('FORTE_DATA_DIR', ROOT / 'data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
MODEL = Path(os.getenv('FORTE_MODEL_PATH', ROOT / 'models/baseline.joblib'))
KEY = os.getenv('FORTE_API_KEY') or secrets.token_urlsafe(32)
LOCAL_REVIEW = os.getenv('FORTE_ENABLE_REVIEW') == '1'
MAX_BYTES = 100 * 1024 * 1024
QUEUE_LIMIT = 1


def db():
    conn = sqlite3.connect(DATA / 'jobs.sqlite')
    conn.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, status TEXT, payload TEXT, created REAL)')
    return conn


def save(job, status, payload):
    with db() as conn:
        conn.execute('INSERT OR REPLACE INTO jobs VALUES (?, ?, ?, ?)', (job, status, json.dumps(payload), time.time()))


def execute(path, model_path):
    # Only load team-generated artifacts. Never accept uploaded model files.
    return analyze(Path(path), joblib.load(model_path))


async def worker(app):
    while True:
        job, path = await app.state.queue.get()
        app.state.active = True
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(app.state.pool, execute, str(path), str(MODEL))
            save(job, 'done', result)
        except Exception:
            save(job, 'failed', {'error': 'Video analysis failed. Check decoding, duration, and the local model.'})
        finally:
            path.unlink(missing_ok=True)
            app.state.active = False
            app.state.queue.task_done()


@asynccontextmanager
async def lifespan(app):
    with db() as conn:
        conn.execute("UPDATE jobs SET status='failed', payload=? WHERE status='processing'", (json.dumps({'error': 'Server restarted; upload again.'}),))
        conn.execute('DELETE FROM jobs WHERE created < ?', (time.time()-86400,))
    for path in DATA.glob('upload-*.mov'):
        path.unlink(missing_ok=True)
    app.state.queue = asyncio.Queue(maxsize=QUEUE_LIMIT)
    app.state.pool = ProcessPoolExecutor(max_workers=1)
    task = asyncio.create_task(worker(app))
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    app.state.pool.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title='Forte Review', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT/'app/static'), name='static')


def authorized(x_api_key: str = Header(default='')):
    if not hmac.compare_digest(x_api_key, KEY):
        raise HTTPException(401, 'Invalid API key')


@app.get('/')
def index():
    return FileResponse(ROOT/'app/static/index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'model_ready': MODEL.is_file(), 'stage': 'experimental_baseline', 'review_enabled': LOCAL_REVIEW}


@app.post('/api/v1/analyze', dependencies=[Depends(authorized)], status_code=202)
async def submit(file: UploadFile = File(...)):
    if not MODEL.is_file():
        raise HTTPException(503, 'Train a local model before analyzing videos')
    if Path(file.filename or '').suffix.lower() != '.mov':
        raise HTTPException(415, 'Upload a .mov video')
    # Reserve capacity before streaming; concurrent uploads cannot bypass the bound.
    if int(getattr(app.state, 'active', False)) + getattr(app.state, 'uploads', 0) + app.state.queue.qsize() >= QUEUE_LIMIT:
        raise HTTPException(429, 'Analysis queue is full; retry later')
    app.state.uploads = getattr(app.state, 'uploads', 0) + 1
    job = secrets.token_hex(16)
    path = DATA/f'upload-{job}.mov'
    try:
        size = 0
        with path.open('wb') as out:
            while chunk := await file.read(1024*1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, 'Maximum upload size is 100 MB')
                out.write(chunk)
        if not size:
            raise HTTPException(400, 'Video is empty')
        save(job, 'processing', {})
        app.state.queue.put_nowait((job, path))
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        app.state.uploads -= 1
        await file.close()
    return {'job_id': job}


@app.get('/api/v1/jobs/{job_id}', dependencies=[Depends(authorized)])
def status(job_id: str):
    with db() as conn:
        row = conn.execute('SELECT status, payload FROM jobs WHERE id=?', (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Job not found')
    return {'job_id': job_id, 'status': row[0], **json.loads(row[1])}


def require_review():
    if not LOCAL_REVIEW:
        raise HTTPException(404, 'Local review is disabled')


@app.get('/api/local/dataset', dependencies=[Depends(authorized), Depends(require_review)])
def dataset():
    manifest = DATA/'manifest.json'
    if not manifest.exists():
        return []
    annotations = json.loads((DATA/'annotations.json').read_text()) if (DATA/'annotations.json').exists() else {}
    return [{k: v for k, v in r.items() if k != 'path'} | {'annotation': annotations.get(r['id'])} for r in json.loads(manifest.read_text())]


@app.get('/api/local/video/{video_id}', dependencies=[Depends(authorized), Depends(require_review)])
def video(video_id: str):
    for row in json.loads((DATA/'manifest.json').read_text()):
        if row['id'] == video_id:
            return FileResponse(row['path'], media_type='video/quicktime')
    raise HTTPException(404, 'Video not found')


class Annotation(BaseModel):
    start_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)
    type: str = Field(min_length=3, max_length=100)
    observation: str = Field(min_length=10, max_length=1000)
    rule_url: str = Field(default='', max_length=500)
    rule_clause: str = Field(default='', max_length=500)


@app.put('/api/local/annotations/{video_id}', dependencies=[Depends(authorized), Depends(require_review)])
async def annotate(video_id: str, annotation: Annotation):
    manifest = json.loads((DATA/'manifest.json').read_text())
    record = next((r for r in manifest if r['id'] == video_id), None)
    if not record or annotation.end_sec < annotation.start_sec or annotation.end_sec > record['duration_sec']:
        raise HTTPException(422, 'Invalid video or event interval')
    path = DATA/'annotations.json'
    values = json.loads(path.read_text()) if path.exists() else {}
    values[video_id] = annotation.model_dump()
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(values, ensure_ascii=False, indent=2))
    tmp.replace(path)
    return {'saved': video_id}
