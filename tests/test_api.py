from fastapi.testclient import TestClient

from app.main import app


def test_api_requires_key():
    with TestClient(app) as client:
        response = client.get("/api/v1/jobs/missing")
    assert response.status_code == 401


def test_unknown_job_is_404():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/jobs/missing",
            headers={"X-API-Key": "jury-demo-key"},
        )
    assert response.status_code == 404


def test_analyze_rejects_non_mov_before_processing():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze",
            headers={"X-API-Key": "jury-demo-key"},
            files={"file": ("sample.mp4", b"not a video", "video/mp4")},
        )
    assert response.status_code == 415
