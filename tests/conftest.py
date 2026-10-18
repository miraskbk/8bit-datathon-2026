import pytest


@pytest.fixture(autouse=True)
def no_real_model_startup(monkeypatch, tmp_path):
    # Unit/API contract tests must not allocate GPUs or invoke real models.
    from app.config import settings
    monkeypatch.setattr(settings, "api_key", "test-only-local-access-key-32-characters")
    monkeypatch.setattr(settings, "preload_model", False)
    monkeypatch.setattr(settings, "job_dir", tmp_path / "jobs")
