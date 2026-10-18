"""The teammate distribution runs the integrated CashGuard pipeline only."""
from __future__ import annotations

import threading
from pathlib import Path

from app.config import Settings
from app.schemas import AnalysisResult


class InferenceService:
    def __init__(self, config: Settings) -> None:
        self.config = config
        self._cashguard = None
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._cashguard is not None

    def load(self) -> None:
        with self._load_lock:
            if self._cashguard is None:
                from app.cashguard_adapter import CashGuardAdapter
                self._cashguard = CashGuardAdapter(self.config)

    def analyze(self, path: Path) -> AnalysisResult:
        self.load()
        with self._inference_lock:
            return self._cashguard.analyze(path)
