from __future__ import annotations

import os
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.schemas import AnalyzeAccepted, Health, JobResponse
from app.service import InferenceService


service = InferenceService(settings)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
static_dir = Path(__file__).parent / "static"


def require_api_key(api_key: str | None = Depends(api_key_header)) -> None:
    if not api_key or api_key != settings.api_key:
        raise HTTPException(401, "Invalid or missing X-API-Key")


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, tuple[float, JobResponse]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=settings.max_parallel_jobs)

    def _cleanup(self) -> None:
        cutoff = time.time() - settings.job_ttl_seconds
        expired = [key for key, (created, _) in self._jobs.items() if created < cutoff]
        for key in expired:
            del self._jobs[key]

    def submit(self, path: Path) -> str:
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._cleanup()
            self._jobs[job_id] = (
                time.time(),
                JobResponse(job_id=job_id, status="processing"),
            )
        self._executor.submit(self._run, job_id, path)
        return job_id

    def _run(self, job_id: str, path: Path) -> None:
        try:
            result = service.analyze(path)
            response = JobResponse(
                job_id=job_id,
                status="done",
                verdict=result.verdict,
                violations=result.violations,
            )
        except Exception as exc:
            response = JobResponse(job_id=job_id, status="failed", error=str(exc))
        finally:
            path.unlink(missing_ok=True)
        with self._lock:
            created = self._jobs.get(job_id, (time.time(), response))[0]
            self._jobs[job_id] = (created, response)

    def get(self, job_id: str) -> JobResponse | None:
        with self._lock:
            self._cleanup()
            item = self._jobs.get(job_id)
            return item[1] if item else None


jobs = JobManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.preload_model:
        await run_in_threadpool(service.load)
    yield


app = FastAPI(
    title="ForteBank Cash Discipline Video Review",
    version="1.0.0",
    description=(
        "Локальный AI-сервис анализа визуальных признаков возможных нарушений "
        "кассовой дисциплины. Результат является подсказкой для проверки человеком."
    ),
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health", response_model=Health, tags=["service"])
def health() -> Health:
    return Health(status="ok", model_loaded=service.loaded, model=service.model_name)


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
    suffix = Path(file.filename or "video.mov").suffix.lower()
    if suffix != ".mov":
        raise HTTPException(415, "The jury API accepts .mov files")
    fd, raw_path = tempfile.mkstemp(prefix="forte-analysis-", suffix=".mov")
    os.close(fd)
    path = Path(raw_path)
    accepted = False
    try:
        await save_upload(file, path)
        # Decode enough metadata before accepting so corrupt uploads fail immediately.
        import av

        await run_in_threadpool(lambda: av.open(str(path)).close())
        job_id = jobs.submit(path)
        accepted = True
        return AnalyzeAccepted(job_id=job_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, f"Invalid MOV video: {exc}") from exc
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
