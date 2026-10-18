from __future__ import annotations

import os
import math
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.schemas import AnalyzeAccepted, Health, JobResponse
from app.jobs import JobManager, QueueFull
from app.security import RequestProtection
import secrets


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
static_dir = Path(__file__).parent / "static"


def require_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    if not api_key or not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(401, "Invalid or missing X-API-Key")


jobs = JobManager(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global jobs
    if len(settings.api_key) < 32 or settings.api_key == "replace-with-a-private-jury-key":
        raise RuntimeError("Set a private API_KEY of at least 32 characters before starting the service")
    jobs = JobManager(settings)
    jobs.start()
    try:
        if settings.preload_model:
            await run_in_threadpool(jobs.worker.load)
        yield
    finally:
        await run_in_threadpool(jobs.close)



app = FastAPI(
    title="ForteBank Cash Discipline Video Review",
    version="1.0.0",
    description=(
        "Локальный AI-сервис анализа визуальных признаков возможных нарушений "
        "кассовой дисциплины. Результат является подсказкой для проверки человеком."
    ),
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(RequestProtection, config=settings)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get('/docs', include_in_schema=False)
def api_docs() -> FileResponse:
    return FileResponse(static_dir / 'api.html')


@app.get("/health", response_model=Health, tags=["service"])
def health() -> Health:
    ready = getattr(jobs.worker, "ready", jobs.worker.loaded)
    return Health(status="ok" if ready else "starting", model_loaded=ready,
                  model="VisionCore RT-DETRv2 + OWLv2 + DINOv2 + local Qwen",
                  pipeline_version="visioncore-integrated-v1",
                  semantic_enabled=True)


@app.get('/ready', tags=['service'])
def readiness():
    if not getattr(jobs.worker, 'ready', jobs.worker.loaded):
        raise HTTPException(503, 'Models are not ready; check local weights and service logs')
    return {'status': 'ready'}


@app.get("/api/v1/capabilities", tags=["service"])
def capabilities():
    return {"max_video_mb": settings.max_video_mb, "max_duration_seconds": settings.max_duration_seconds,
            "analysis_timeout_seconds": settings.analysis_timeout_seconds, "formats": [".mov"],
            "local_only": True, "audio": False, "face_identification": False,
            "pipeline": settings.pipeline, "max_video_pixels": settings.max_video_pixels,
            "result_ttl_seconds": settings.job_ttl_seconds, "max_pending_jobs": settings.max_pending_jobs}



async def save_upload(upload: UploadFile, path: Path) -> None:
    limit = settings.max_video_mb * 1024 * 1024
    size = 0
    with path.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, f"Video exceeds {settings.max_video_mb} MB limit")
            output.write(chunk)
    if size == 0:
        raise HTTPException(422, "Uploaded video is empty")


@app.post(
    "/api/v1/analyze",
    response_model=AnalyzeAccepted,
    status_code=202,
    dependencies=[Depends(require_api_key)],
    tags=["jury API"],
)
async def analyze(file: UploadFile = File(..., description="Video in .mov format")) -> AnalyzeAccepted:
    request_started = time.monotonic()
    suffix = Path(file.filename or "video.mov").suffix.lower()
    if suffix != ".mov":
        await file.close()
        raise HTTPException(415, "The jury API accepts .mov files")
    fd, raw_path = tempfile.mkstemp(prefix="upload-", suffix=".mov", dir=settings.job_dir)
    os.close(fd)
    path = Path(raw_path)
    accepted = False
    try:
        await save_upload(file, path)
        # Decode enough metadata before accepting so corrupt uploads fail immediately.
        import av

        def validate_video():
            with av.open(str(path)) as container:
                if not container.streams.video:
                    raise ValueError("No video stream")
                stream = container.streams.video[0]
                duration = float(stream.duration * stream.time_base) if stream.duration is not None else float(container.duration or 0)/av.time_base
                if not math.isfinite(duration) or duration <= 0:
                    raise HTTPException(422, 'Video must have a known positive duration')
                if duration > settings.max_duration_seconds:
                    raise HTTPException(422, f"Video exceeds {settings.max_duration_seconds:g} seconds")
                if stream.width * stream.height > settings.max_video_pixels:
                    raise HTTPException(422, 'Video resolution exceeds the supported pixel limit')
                # A header alone does not establish a decodable video.
                next(container.decode(stream))
        await run_in_threadpool(validate_video)
        job_id = jobs.submit(path, request_started)
        accepted = True
        return AnalyzeAccepted(job_id=job_id)
    except HTTPException:
        raise
    except QueueFull as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "15"}) from exc
    except Exception as exc:
        raise HTTPException(422, "Invalid or unsupported MOV video") from exc
    finally:
        if not accepted:
            path.unlink(missing_ok=True)
        await file.close()


@app.get(
    "/api/v1/jobs/{job_id}",
    response_model=JobResponse,
    dependencies=[Depends(require_api_key)],
    tags=["jury API"],
)
def job_status(job_id: str) -> JobResponse:
    result = jobs.get(job_id)
    if result is None:
        raise HTTPException(404, "Job not found or expired")
    return result


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
