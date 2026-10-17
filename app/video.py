from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

import av
import numpy as np
from PIL import Image


class VideoError(ValueError):
    pass


@dataclass(frozen=True)
class SampledVideo:
    frames: list[Image.Image]
    timestamps: np.ndarray
    duration_seconds: float

    def nearest_frame(self, timestamp: float) -> tuple[float, Image.Image]:
        index = int(np.abs(self.timestamps - timestamp).argmin())
        return float(self.timestamps[index]), self.frames[index]


def decode_video(
    path: Path,
    *,
    sample_fps: float,
    max_duration_seconds: float,
) -> SampledVideo:
    """Decode a video locally and sample it at a stable temporal rate."""
    try:
        container = av.open(str(path))
    except Exception as exc:
        raise VideoError(f"Не удалось открыть видео: {exc}") from exc

    try:
        if not container.streams.video:
            raise VideoError("В файле отсутствует видеопоток")
        stream = container.streams.video[0]
        fps = float(stream.average_rate or 25)
        duration = 0.0
        if stream.duration is not None and stream.time_base is not None:
            duration = float(stream.duration * stream.time_base)
        elif container.duration is not None:
            duration = float(container.duration / av.time_base)
        if duration > max_duration_seconds:
            raise VideoError(
                f"Длительность {duration:.1f} с превышает лимит {max_duration_seconds:.0f} с"
            )

        frames: list[Image.Image] = []
        timestamps: list[float] = []
        interval = 1.0 / sample_fps
        next_sample = 0.0
        last_time = 0.0
        for index, frame in enumerate(container.decode(stream)):
            timestamp = float(frame.time) if frame.time is not None else index / fps
            last_time = max(last_time, timestamp)
            if timestamp > max_duration_seconds:
                raise VideoError(f"Видео превышает лимит {max_duration_seconds:.0f} с")
            if timestamp + 1e-4 >= next_sample:
                frames.append(frame.to_image().convert("RGB"))
                timestamps.append(timestamp)
                next_sample += interval
        if not frames:
            raise VideoError("В видео не найдено декодируемых кадров")
        return SampledVideo(
            frames=frames,
            timestamps=np.asarray(timestamps, dtype=np.float32),
            duration_seconds=round(duration or last_time + 1 / fps, 3),
        )
    except VideoError:
        raise
    except Exception as exc:
        raise VideoError(f"Не удалось декодировать видео: {exc}") from exc
    finally:
        container.close()


def jpeg_base64(image: Image.Image, quality: int = 86) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")
