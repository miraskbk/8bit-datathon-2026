import time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.jobs import JobManager
from app.schemas import AnalysisResult


class FakeWorker:
    loaded = True
    def analyze(self, path, deadline):
        assert path.is_file() and deadline > time.monotonic()
        return AnalysisResult(verdict="no_violation",violations=[],metadata={"tested":True}).model_dump()
    def stop(self):
        pass


def wait_job(jobs, job_id):
    for _ in range(100):
        result = jobs.get(job_id)
        if result.status != "processing":
            return result
        time.sleep(.01)
    raise AssertionError("Job never finished")


def test_persistent_jobs_cleanup_and_restart_recovery(tmp_path):
    config = Settings(job_dir=tmp_path/"jobs")
    jobs = JobManager(config,FakeWorker())
    source = tmp_path/"upload.mov";source.write_bytes(b"test")
    job_id=jobs.submit(source)
    result=wait_job(jobs,job_id)
    assert result.status == "done" and result.metadata["tested"]
    assert not list(config.job_dir.glob("*.mov")) and not source.exists()
    jobs.close()
    restarted = JobManager(config,FakeWorker());restarted.start()
    assert restarted.get(job_id).status == "done"
    assert restarted.get("../../secret") is None
    restarted.close()


def test_model_failure_is_failed_not_negative(tmp_path):
    class Broken(FakeWorker):
        def analyze(self,*args):
            raise TimeoutError("hard deadline")
    jobs=JobManager(Settings(job_dir=tmp_path/"jobs"), Broken())
    source=tmp_path/"upload.mov";source.write_bytes(b"test")
    result=wait_job(jobs,jobs.submit(source))
    assert result.status == "failed" and result.verdict is None and not result.violations
    assert not list((tmp_path/"jobs").glob("*.mov"))
    jobs.close()


def test_api_upload_poll_schema_and_admission(tmp_path,monkeypatch):
    import av
    import app.main as main
    source=tmp_path/"tiny.mov"
    with av.open(str(source),"w") as container:
        stream=container.add_stream("mpeg4",rate=30);stream.width=32;stream.height=32;stream.pix_fmt="yuv420p"
        for _ in range(3):
            frame=av.VideoFrame.from_ndarray(np.zeros((32,32,3),dtype=np.uint8),format="rgb24")
            for packet in stream.encode(frame):container.mux(packet)
        for packet in stream.encode():container.mux(packet)
    monkeypatch.setattr(main,"JobManager",lambda config:JobManager(config,FakeWorker()))
    with TestClient(main.app) as client:
        headers={"X-API-Key":main.settings.api_key}
        assert client.post("/api/v1/analyze",files={"file":("x.mov",source.read_bytes())}).status_code==401
        assert client.post("/api/v1/analyze",headers=headers,files={"file":("x.mov",b"invalid")}).status_code==422
        accepted=client.post("/api/v1/analyze",headers=headers,files={"file":("x.mov",source.read_bytes())})
        assert accepted.status_code==202
        result=wait_job(main.jobs,accepted.json()["job_id"])
        polled=client.get('/api/v1/jobs/'+result.job_id,headers=headers)
        assert polled.status_code==200 and polled.json()["verdict"]=="no_violation"
        assert client.get('/api/v1/jobs/'+result.job_id,headers={"X-API-Key":"wrong"}).status_code==401
        main.jobs._active=main.settings.max_pending_jobs
        rejected=client.post("/api/v1/analyze",headers=headers,files={"file":("x.mov",source.read_bytes())})
        assert rejected.status_code==429 and rejected.headers["Retry-After"]=="15"
        main.jobs._active=0


def test_recovery_marks_interrupted_jobs_failed_and_expires_results(tmp_path):
    import json, os
    config=Settings(job_dir=tmp_path/"jobs")
    config.job_dir.mkdir()
    job_id="a"*32
    (config.job_dir/f"{job_id}.json").write_text(json.dumps({"created":time.time(),
        "response":{"job_id":job_id,"status":"processing"}}))
    (config.job_dir/f"{job_id}.mov").write_bytes(b"private")
    manager=JobManager(config,FakeWorker());manager.start()
    result=manager.get(job_id)
    assert result.status=="failed" and result.verdict is None
    assert not list(config.job_dir.glob("*.mov"))
    path=config.job_dir/f"{job_id}.json"
    os.utime(path,(time.time()-config.job_ttl_seconds-5,)*2)
    assert manager.get(job_id) is None
    manager.close()


def test_only_one_api_process_can_own_a_job_directory(tmp_path):
    config=Settings(job_dir=tmp_path/"jobs")
    first=JobManager(config,FakeWorker());first.start()
    second=JobManager(config,FakeWorker())
    try:
        with pytest.raises(RuntimeError,match="already used"):
            second.start()
    finally:
        first.close();second.close()
