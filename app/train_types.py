from __future__ import annotations

import argparse
import csv
from pathlib import Path

import torch
from torchvision.models.video import R3D_18_Weights, r3d_18

from app.train import decode_at_four_fps, make_clips, read_labels


def read_type_labels(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as source:
        return {row["video"]: row["type"] for row in csv.DictReader(source)}


def build_prototypes(
    labels_path: Path,
    types_path: Path,
    videos_dir: Path,
    output: Path,
) -> None:
    timestamps = read_labels(labels_path)
    types = read_type_labels(types_path)
    missing = {name for name, timestamp in timestamps.items() if timestamp is not None} - types.keys()
    if missing:
        raise ValueError(f"Missing type labels for: {sorted(missing)}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    weights = R3D_18_Weights.DEFAULT
    encoder = r3d_18(weights=weights)
    encoder.fc = torch.nn.Identity()
    encoder = encoder.to(device).eval()
    features: list[torch.Tensor] = []
    labels: list[str] = []
    names: list[str] = []

    for index, (stem, rule_code) in enumerate(types.items(), 1):
        event_time = timestamps.get(stem)
        if event_time is None:
            raise ValueError(f"{stem} has no positive timestamp in {labels_path}")
        frames, frame_times = decode_at_four_fps(videos_dir / f"{stem}.mov")
        centers = [event_time - 1, event_time, event_time + 1]
        clips = make_clips(frames, frame_times, centers, weights.transforms()).to(device)
        with torch.inference_mode():
            encoded = encoder(clips).cpu()
        features.append(encoded)
        labels.extend([rule_code] * len(centers))
        names.extend([stem] * len(centers))
        print(f"[{index:02d}/{len(types)}] {stem}: {rule_code}", flush=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "encoder": "r3d_18_kinetics400_v1",
            "features": torch.cat(features),
            "labels": labels,
            "video_names": names,
        },
        output,
    )
    print(f"Saved {len(labels)} visual prototypes to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build visual prototypes for violation types")
    parser.add_argument("--labels", type=Path, default=Path("open/open_labels.xlsx"))
    parser.add_argument("--types", type=Path, default=Path("open/violation_types.csv"))
    parser.add_argument("--videos", type=Path, default=Path("open/videos"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/forte_type_prototypes.pt"))
    args = parser.parse_args()
    build_prototypes(args.labels, args.types, args.videos, args.output)


def run() -> None:
    main()


if __name__ == "__main__":
    main()
