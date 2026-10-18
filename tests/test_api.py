from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


def test_api_requires_key():
    with TestClient(app) as client:
        response = client.get("/api/v1/jobs/missing")
    assert response.status_code == 401


def test_unknown_job_is_404():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/jobs/missing",
            headers={"X-API-Key": settings.api_key},
        )
    assert response.status_code == 404


def test_analyze_rejects_non_mov_before_processing():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze",
            headers={"X-API-Key": settings.api_key},
            files={"file": ("sample.mp4", b"not a video", "video/mp4")},
        )
    assert response.status_code == 415


def test_empty_and_oversized_uploads_are_rejected(monkeypatch):
    monkeypatch.setattr(settings,'max_video_mb',1)
    with TestClient(app) as client:
        headers={'X-API-Key':settings.api_key}
        empty=client.post('/api/v1/analyze',headers=headers,files={'file':('empty.MOV',b'')})
        large=client.post('/api/v1/analyze',headers=headers,files={'file':('large.mov',b'0'*(1024*1024+1))})
    assert empty.status_code==422 and large.status_code==413
