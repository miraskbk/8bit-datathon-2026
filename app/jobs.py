"""Bounded admission, atomic on-disk results, interrupted-job recovery and TTL."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.schemas import AnalysisResult, JobResponse
from app.worker import ModelWorker

log = logging.getLogger(__name__)


class QueueFull(RuntimeError):
    pass


class JobManager:
    def __init__(self, config, worker=None):
        self.config = config
        self.worker = worker or ModelWorker(config)
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._active = 0
        self._started = False
        self._shutdown = threading.Event()
        self._lease = None
        self._janitor_thread = None

    def start(self):
        with self._lock:
            if self._started:
                return
            self.config.job_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.config.job_dir.chmod(0o700)
            import fcntl
            self._lease = (self.config.job_dir / ".service.lock").open("a")
            try:
                fcntl.flock(self._lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                self._lease.close()
                self._lease = None
                raise RuntimeError("Job directory is already used by another API process; use --workers 1") from exc
            for path in self.config.job_dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text())
                    if data["response"]["status"] == "processing":
                        self._save(data["created"], JobResponse(job_id=data["response"]["job_id"], status="failed",
                            error="Service restarted during processing; upload the recording again"))
                except (ValueError, KeyError):
                    continue
            # Uploads are private runtime data, never training inputs.
            for path in self.config.job_dir.glob("*.mov"):
                path.unlink(missing_ok=True)
            for pattern in ('*.tmp', '*.result.json'):
                for path in self.config.job_dir.glob(pattern):
                    path.unlink(missing_ok=True)
            self._cleanup()
            self._started = True
            self._janitor_thread = threading.Thread(target=self._janitor, daemon=True)
            self._janitor_thread.start()

    def _janitor(self):
        while not self._shutdown.wait(60):
            try:
                with self._lock:
                    self._cleanup()
            except OSError:
                log.exception('Runtime cleanup failed; will retry')

    def _save(self, created, response):
        path = self.config.job_dir / f"{response.job_id}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"created": created, "response": response.model_dump()}))
        temporary.chmod(0o600)
        temporary.replace(path)

    def _cleanup(self):
        def expired(path):
            try:
                return path.stat().st_mtime < time.time()-self.config.job_ttl_seconds
            except FileNotFoundError:
                return False  # The worker can remove its own cache concurrently.

        # A killed model cannot run its finally block; remove stale feature/state caches too.
        for directory in (Path(__file__).resolve().parents[1] / "runtime/cashguard").glob("*"):
            if directory.is_dir():
                for cached in directory.glob("*.json"):
                    if expired(cached):
                        cached.unlink(missing_ok=True)
        for path in self.config.job_dir.glob("*.json"):
            if expired(path):
                path.unlink(missing_ok=True)

    def submit(self, path: Path, started=None):
        self.start()
        created = time.time()
        deadline = (started if started is not None else time.monotonic()) + self.config.analysis_timeout_seconds
        with self._lock:
            if self._active >= self.config.max_pending_jobs:
                raise QueueFull("Analysis capacity is full; retry after the running job completes")
            job_id = uuid.uuid4().hex
            destination = self.config.job_dir / f"{job_id}.mov"
            path.replace(destination)
            self._save(created, JobResponse(job_id=job_id, status="processing"))
            self._active += 1
        self._executor.submit(self._run, job_id, destination, created, deadline)
        return job_id

    def _run(self, job_id, path, created, deadline):
        try:
            result = AnalysisResult.model_validate(self.worker.analyze(path, deadline))
            response = JobResponse(job_id=job_id, status="done", **result.model_dump())
        except Exception as exc:
            log.exception('Analysis failed for job %s', job_id)
            error = ('Analysis deadline exceeded; retry or contact the service operator'
                     if isinstance(exc, TimeoutError) else
                     'Analysis failed; contact the service operator with this job_id')
            response = JobResponse(job_id=job_id, status="failed", error=error)
        finally:
            path.unlink(missing_ok=True)
            path.with_suffix(".result.json").unlink(missing_ok=True)
            path.with_suffix(".result.tmp").unlink(missing_ok=True)
        with self._lock:
            self._save(created, response)
            self._active -= 1
            self._cleanup()

    def get(self, job_id):
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            return None
        self.start()
        with self._lock:
            self._cleanup()
            path = self.config.job_dir / f"{job_id}.json"
            return JobResponse.model_validate(json.loads(path.read_text())["response"]) if path.exists() else None

    def close(self):
        self._shutdown.set()
        self.worker.stop()
        self._executor.shutdown(wait=True, cancel_futures=False)
        if self._janitor_thread:
            self._janitor_thread.join(1)
        if self._lease:
            self._lease.close()
            self._lease = None
