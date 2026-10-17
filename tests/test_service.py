import base64
import importlib
from pathlib import Path
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.vision import analyze, samples


class PositiveModel:
    classes_ = np.array(['normal', 'possible_violation_unclassified'])
    def predict_proba(self, x):
        return np.array([[.05, .95]] * len(x))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('FORTE_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('FORTE_API_KEY', 'test-key')
    monkeypatch.setenv('FORTE_MODEL_PATH', str(tmp_path/'missing.joblib'))
    monkeypatch.delenv('FORTE_ENABLE_REVIEW', raising=False)
    import app.main as main
    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c, main


def test_auth_and_missing_model(client):
    c, _ = client
    assert c.get('/api/v1/jobs/unknown').status_code == 401
    assert c.post('/api/v1/analyze', headers={'X-API-Key':'test-key'}, files={'file':('x.mov', b'x')}).status_code == 503
    assert c.get('/api/local/dataset', headers={'X-API-Key':'test-key'}).status_code == 404


def test_persisted_result_contract(client):
    c, main = client
    main.save('example', 'done', {'verdict':'no_violation', 'violations':[]})
    response = c.get('/api/v1/jobs/example', headers={'X-API-Key':'test-key'})
    assert response.json() == {'job_id':'example', 'status':'done', 'verdict':'no_violation', 'violations':[]}
    assert c.get('/api/v1/jobs/missing', headers={'X-API-Key':'test-key'}).status_code == 404


def test_upload_validation(client):
    c, main = client
    main.MODEL.touch()
    auth={'X-API-Key':'test-key'}
    assert c.post('/api/v1/analyze', headers=auth, files={'file':('x.txt',b'bad')}).status_code == 415
    assert c.post('/api/v1/analyze', headers=auth, files={'file':('x.mov',b'')}).status_code == 400
    main.MAX_BYTES=3
    assert c.post('/api/v1/analyze', headers=auth, files={'file':('x.mov',b'1234')}).status_code == 413
    assert not list(main.DATA.glob('upload-*.mov'))


def test_video_evidence_and_timestamp(tmp_path):
    path=tmp_path/'synthetic.mov'
    writer=cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 10, (64,64))
    assert writer.isOpened()
    for i in range(30):
        frame=np.full((64,64,3), i*7, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    frames=list(samples(path))
    assert [f[0] for f in frames] == [0.,1.,2.]
    result=analyze(path, {'feature_version':1,'model':PositiveModel(),'threshold':.65})
    assert result['verdict']=='violation'
    assert len(result['violations'])==1
    evidence=result['violations'][0]['evidence_frames'][0]
    decoded=cv2.imdecode(np.frombuffer(base64.b64decode(evidence['image_base64']),dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape==(64,64,3)
    assert 0<=evidence['timestamp_sec']<3


def test_invalid_video_fails(tmp_path):
    path=tmp_path/'bad.mov';path.write_bytes(b'not video')
    with pytest.raises(ValueError):
        list(samples(path))
