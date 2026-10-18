from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    pipeline: Literal['visioncore'] = 'visioncore'
    api_key: str = ''
    device: str | None = None
    vlm_backend: Literal['mlx', 'transformers'] = 'mlx'
    vlm_model: Path = ROOT / 'models/Qwen3-VL-8B-Instruct-4bit'
    job_dir: Path = ROOT / 'runtime/jobs'
    max_pending_jobs: int = Field(default=1, ge=1, le=4)
    max_video_mb: int = Field(default=35, ge=1)
    max_duration_seconds: float = Field(default=180, gt=0)
    analysis_timeout_seconds: float = Field(default=270, ge=30, le=290)
    preload_model: bool = True
    job_ttl_seconds: int = Field(default=3600, ge=300)
    max_video_pixels: int = Field(default=3840 * 2160, ge=1024)
    allowed_hosts: list[str] = ['*']

    @field_validator('vlm_model', 'job_dir')
    @classmethod
    def absolute_paths(cls, value: Path) -> Path:
        return value if value.is_absolute() else ROOT / value


settings = Settings()
