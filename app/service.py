from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from app.config import Settings
from app.model import ViolationModel, event_peaks, window_centers
from app.schemas import (
    AnalysisResult,
    EvidenceFrame,
    RuleReference,
    ViolationEvent,
)
from app.video import decode_video, jpeg_base64


class InferenceService:
    def __init__(self, config: Settings) -> None:
        self.config = config
        self._model: ViolationModel | None = None
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def model_name(self) -> str:
        return self._model.name if self._model else self.config.model_id

    def load(self) -> None:
        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    self._model = ViolationModel(
                        self.config.model_checkpoint,
                        self.config.type_checkpoint,
                    )

    def analyze(self, path: Path) -> AnalysisResult:
        video = decode_video(
            path,
            sample_fps=self.config.sample_fps,
            max_duration_seconds=self.config.max_duration_seconds,
        )
        self.load()
        assert self._model is not None
        centers = window_centers(video.duration_seconds, self.config.inference_stride_seconds)
        with self._inference_lock:
            scores, features = self._model.analyze_windows(
                video, centers, self.config.inference_batch_size
            )
            peaks = event_peaks(
                centers,
                scores,
                self.config.decision_threshold,
                self.config.max_events,
                self.config.min_event_gap_seconds,
            )
            violations: list[ViolationEvent] = []
            for timestamp, score in peaks:
                offsets = np.linspace(-0.5, 0.5, self.config.evidence_count)
                evidence_frames = []
                for offset in offsets:
                    actual_time, image = video.nearest_frame(timestamp + offset)
                    evidence_frames.append(
                        EvidenceFrame(
                            timestamp_sec=round(actual_time, 2),
                            image_base64=jpeg_base64(image),
                        )
                    )
                feature_index = int(np.abs(centers - timestamp).argmin())
                rule = self._model.classify_rule(features[feature_index])
                violations.append(
                    ViolationEvent(
                        type=rule.title,
                        timecode_sec=round(timestamp, 2),
                        description=rule.description,
                        evidence_frames=evidence_frames,
                        rule=RuleReference(
                            document=rule.document,
                            section=rule.section,
                            url=rule.url,
                        ),
                        confidence=round(score, 4),
                    )
                )
        violations.sort(key=lambda event: event.timecode_sec)
        return AnalysisResult(
            verdict="violation" if violations else "no_violation",
            violations=violations,
        )
