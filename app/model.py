from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.models.video import R3D_18_Weights, r3d_18

from app.rules import RULES, RuleDefinition
from app.video import SampledVideo


def choose_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class ViolationModel:
    """Temporal R3D-18 encoder with a head trained on the ForteBank clips."""

    def __init__(self, checkpoint: Path, type_checkpoint: Path) -> None:
        if not checkpoint.is_file():
            raise FileNotFoundError(
                f"Model checkpoint not found: {checkpoint}. Run `violation-train` first."
            )
        self.device = choose_device()
        self.weights = R3D_18_Weights.DEFAULT
        self.transform = self.weights.transforms()
        self.encoder = r3d_18(weights=self.weights)
        self.encoder.fc = torch.nn.Identity()
        self.encoder = self.encoder.to(self.device).eval()

        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.feature_mean = state["feature_mean"].to(self.device)
        self.feature_std = state["feature_std"].to(self.device)
        self.head_weight = state["weight"].to(self.device)
        self.head_bias = state["bias"].to(self.device)
        self.checkpoint_name = checkpoint.name
        if not type_checkpoint.is_file():
            raise FileNotFoundError(
                f"Type prototypes not found: {type_checkpoint}. Run `violation-train-types` first."
            )
        type_state = torch.load(type_checkpoint, map_location="cpu", weights_only=True)
        self.type_features = F.normalize(type_state["features"].to(self.device), dim=1)
        self.type_labels: list[str] = type_state["labels"]
        self.type_video_names: list[str] = type_state["video_names"]
        self.rules_by_code = {rule.code: rule for rule in RULES}

    @property
    def name(self) -> str:
        return f"r3d_18/Kinetics-400 + {self.checkpoint_name}"

    def _clip_tensor(self, video: SampledVideo, center: float) -> torch.Tensor:
        half = 1.875
        targets = np.linspace(center - half, center + half, 16)
        indices = [int(np.abs(video.timestamps - target).argmin()) for target in targets]
        frames = [
            torch.from_numpy(np.array(video.frames[index], dtype=np.uint8, copy=True)).permute(2, 0, 1)
            for index in indices
        ]
        return self.transform(torch.stack(frames))

    @torch.inference_mode()
    def analyze_windows(
        self,
        video: SampledVideo,
        centers: np.ndarray,
        batch_size: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        scores: list[torch.Tensor] = []
        feature_batches: list[torch.Tensor] = []
        for start in range(0, len(centers), batch_size):
            clips = torch.stack(
                [self._clip_tensor(video, float(c)) for c in centers[start : start + batch_size]]
            ).to(self.device)
            features = self.encoder(clips)
            feature_batches.append(features.float().cpu())
            standardized = (features - self.feature_mean) / self.feature_std
            logits = standardized @ self.head_weight + self.head_bias
            scores.append(torch.sigmoid(logits).float().cpu())
        values = torch.cat(scores).numpy()
        if len(values) >= 3:
            values = np.convolve(values, np.array([0.2, 0.6, 0.2]), mode="same")
        return values, torch.cat(feature_batches).numpy()

    @torch.inference_mode()
    def classify_rule(self, feature: np.ndarray) -> RuleDefinition:
        """Match the event's temporal visual embedding to audited action prototypes."""
        query = F.normalize(torch.as_tensor(feature, device=self.device).unsqueeze(0), dim=1)
        similarities = (query @ self.type_features.T).squeeze(0)
        nearest = int(similarities.argmax().item())
        return self.rules_by_code[self.type_labels[nearest]]


def window_centers(duration: float, stride: float) -> np.ndarray:
    if duration <= 4:
        return np.asarray([duration / 2], dtype=np.float32)
    centers = np.arange(2.0, max(2.01, duration - 1.75), stride, dtype=np.float32)
    if centers.size == 0:
        centers = np.asarray([duration / 2], dtype=np.float32)
    return centers


def event_peaks(
    centers: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    max_events: int,
    min_event_gap_seconds: float = 10.0,
) -> list[tuple[float, float]]:
    """Collapse adjacent positive windows into distinct event peaks."""
    positive = np.flatnonzero(scores >= threshold)
    if positive.size == 0:
        return []
    groups: list[list[int]] = [[int(positive[0])]]
    for index in positive[1:]:
        if int(index) <= groups[-1][-1] + 2:
            groups[-1].append(int(index))
        else:
            groups.append([int(index)])
    candidates = []
    for group in groups:
        best = max(group, key=lambda i: float(scores[i]))
        # Use the confidence-weighted center of the whole response, rather than a
        # memorized frame or the first threshold crossing of a long action.
        group_scores = scores[group]
        timestamp = float(np.average(centers[group], weights=group_scores))
        candidates.append((round(timestamp, 1), float(scores[best])))

    # Suppress nearby peaks from one prolonged/intermittent incident. The supplied
    # labels contain one timestamp per incident, while truly distinct events remain.
    selected: list[tuple[float, float]] = []
    for candidate in sorted(candidates, key=lambda item: item[1], reverse=True):
        if all(abs(candidate[0] - existing[0]) >= min_event_gap_seconds for existing in selected):
            selected.append(candidate)
        if len(selected) == max_events:
            break
    return selected
