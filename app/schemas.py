from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceFrame(BaseModel):
    timestamp_sec: float = Field(ge=0, allow_inf_nan=False)
    image_base64: str


class RuleReference(BaseModel):
    document: str
    section: str
    url: str


class ViolationEvent(BaseModel):
    type: str
    timecode_sec: float = Field(ge=0, allow_inf_nan=False)
    description: str
    evidence_frames: list[EvidenceFrame] = Field(min_length=1, max_length=3)
    rule: RuleReference
    confidence: float | None = Field(default=None, ge=0, le=1)


class AnalysisResult(BaseModel):
    metadata: dict = Field(default_factory=dict)
    verdict: Literal["no_violation", "violation"]
    violations: list[ViolationEvent]

    @model_validator(mode='after')
    def consistent_verdict(self):
        if (self.verdict == 'violation') != bool(self.violations):
            raise ValueError('Verdict and violations must agree')
        return self


class AnalyzeAccepted(BaseModel):
    job_id: str
    status: Literal["processing"] = "processing"


class JobResponse(BaseModel):
    job_id: str
    status: Literal["processing", "done", "failed"]
    verdict: Literal["no_violation", "violation"] | None = None
    violations: list[ViolationEvent] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    error: str | None = None


class Health(BaseModel):
    status: str
    model_loaded: bool
    model: str
    pipeline_version: str = "visioncore-integrated-v1"
    semantic_enabled: bool = False
