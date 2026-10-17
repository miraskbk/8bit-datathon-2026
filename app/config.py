from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "jury-demo-key"
    model_id: str = "r3d_18_kinetics400_v1"
    model_checkpoint: Path = Path("artifacts/forte_r3d_head.pt")
    type_checkpoint: Path = Path("artifacts/forte_type_prototypes.pt")
    decision_threshold: float = Field(default=0.80, ge=0, le=1)
    max_video_mb: int = Field(default=35, ge=1)
    max_duration_seconds: float = Field(default=180, gt=0)
    sample_fps: float = Field(default=4.0, gt=0, le=12)
    window_seconds: float = Field(default=4.0, ge=2, le=8)
    inference_stride_seconds: float = Field(default=1.0, ge=0.5, le=5)
    inference_batch_size: int = Field(default=4, ge=1, le=16)
    max_events: int = Field(default=5, ge=1, le=10)
    min_event_gap_seconds: float = Field(default=10.0, ge=1, le=60)
    evidence_count: int = Field(default=3, ge=1, le=3)
    preload_model: bool = True
    job_ttl_seconds: int = Field(default=3600, ge=300)
    max_parallel_jobs: int = Field(default=1, ge=1, le=4)


settings = Settings()
