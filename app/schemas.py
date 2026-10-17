from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvidenceFrame(BaseModel):
    timestamp_sec: float
    image_base64: str


class RuleReference(BaseModel):
    document: str
    section: str
    url: str


class ViolationEvent(BaseModel):
    type: str
    timecode_sec: float
    description: str
    evidence_frames: list[EvidenceFrame]
    rule: RuleReference
    confidence: float = Field(ge=0, le=1)


class AnalysisResult(BaseModel):
    verdict: Literal["no_violation", "violation"]
    violations: list[ViolationEvent]


class AnalyzeAccepted(BaseModel):
    job_id: str
    status: Literal["processing"] = "processing"


class JobResponse(BaseModel):
    job_id: str
    status: Literal["processing", "done", "failed"]
    verdict: Literal["no_violation", "violation"] | None = None
    violations: list[ViolationEvent] = Field(default_factory=list)
    error: str | None = None


class Health(BaseModel):
    status: str
    model_loaded: bool
    model: str
