"""Real process watchdog tests with cheap synthetic workers, no model allocations."""
import time
import pytest
from app.config import Settings
from app.worker import ModelWorker


def blocked_worker(connection, config):
    connection.send({"ready":True})
    connection.recv()
    time.sleep(60)


def healthy_worker(connection, config):
    connection.send({"ready":True})
    while connection.recv() is not None:
        connection.send({"result":{"verdict":"no_violation","violations":[]}})


def test_watchdog_kills_hung_process_and_next_job_recovers(tmp_path,monkeypatch):
    import app.worker as module
    monkeypatch.setattr(module,"inference_worker",blocked_worker)
    worker=ModelWorker(Settings(job_dir=tmp_path))
    worker.load(time.monotonic()+10)
    previous=worker.process
    start=time.monotonic()
    with pytest.raises(TimeoutError):
        worker.analyze(tmp_path/"x.mov",time.monotonic()+.15)
    assert time.monotonic()-start<5 and worker.process is None and not worker.loaded
    monkeypatch.setattr(module,"inference_worker",healthy_worker)
    result=worker.analyze(tmp_path/"y.mov",time.monotonic()+10)
    assert result["verdict"]=="no_violation" and worker.loaded
    worker.stop()


def disk_result_worker(connection, config):
    import json
    from pathlib import Path
    connection.send({'ready':True})
    while True:
        path=connection.recv()
        if path is None:
            break
        result=Path(path).with_suffix('.result.json')
        result.write_text(json.dumps({'verdict':'no_violation','violations':[], 'metadata':{'transport':'disk'}}))
        connection.send({'result_path':str(result)})


def test_worker_reads_atomic_result_file_and_removes_transport_copy(tmp_path,monkeypatch):
    import app.worker as module
    monkeypatch.setattr(module,'inference_worker',disk_result_worker)
    worker=ModelWorker(Settings(job_dir=tmp_path))
    source=tmp_path/'job.mov'
    try:
        result=worker.analyze(source,time.monotonic()+10)
        assert result['metadata']['transport']=='disk'
        assert not source.with_suffix('.result.json').exists()
        assert worker.ready
    finally:
        worker.stop()
