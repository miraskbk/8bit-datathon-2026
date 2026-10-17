from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.train import read_labels
from app.video import decode_video


def build_sheet(items: list[tuple[str, float]], videos: Path, output: Path) -> None:
    offsets = (-3, -2, -1, 0, 1, 2, 3)
    cell_width, cell_height = 250, 165
    header = 34
    sheet = Image.new(
        "RGB",
        (cell_width * len(offsets), (cell_height + header) * len(items)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    for row, (stem, event_time) in enumerate(items):
        video = decode_video(
            videos / f"{stem}.mov",
            sample_fps=4,
            max_duration_seconds=180,
        )
        y = row * (cell_height + header)
        draw.text((8, y + 7), f"{stem} — annotated {event_time:.0f}s", fill="black", font=font)
        for column, offset in enumerate(offsets):
            actual, frame = video.nearest_frame(event_time + offset)
            frame.thumbnail((cell_width, cell_height))
            x = column * cell_width
            canvas = Image.new("RGB", (cell_width, cell_height), "#111111")
            canvas.paste(frame, ((cell_width - frame.width) // 2, 0))
            sheet.paste(canvas, (x, y + header))
            draw.text((x + 7, y + header + 6), f"{actual:.1f}s", fill="white", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def build_overview(items: list[tuple[str, float]], videos: Path, output: Path) -> None:
    columns, cell_width, cell_height, header = 5, 360, 430, 30
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * cell_width, rows * (cell_height + header)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    for index, (stem, event_time) in enumerate(items):
        video = decode_video(videos / f"{stem}.mov", sample_fps=4, max_duration_seconds=180)
        actual, frame = video.nearest_frame(event_time)
        # The camera is portrait; crop unused ceiling/floor while retaining the desk.
        crop = frame.crop((0, 90, frame.width, min(frame.height, 645)))
        crop.thumbnail((cell_width, cell_height))
        column, row = index % columns, index // columns
        x, y = column * cell_width, row * (cell_height + header)
        canvas = Image.new("RGB", (cell_width, cell_height), "#111111")
        canvas.paste(crop, ((cell_width - crop.width) // 2, 0))
        sheet.paste(canvas, (x, y + header))
        draw.text((x + 8, y + 6), f"{stem} @ {actual:.1f}s", fill="black", font=font)
    sheet.save(output, quality=94)


def build_closeups(items: list[tuple[str, float]], videos: Path, output: Path) -> None:
    offsets = (-1.0, 0.0, 1.0, 2.0)
    cell_width, cell_height, header = 464, 400, 30
    sheet = Image.new("RGB", (len(offsets) * cell_width, len(items) * (cell_height + header)), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    for row, (stem, event_time) in enumerate(items):
        video = decode_video(videos / f"{stem}.mov", sample_fps=4, max_duration_seconds=180)
        y = row * (cell_height + header)
        draw.text((8, y + 6), f"{stem} — {event_time:.0f}s", fill="black", font=font)
        for column, offset in enumerate(offsets):
            actual, frame = video.nearest_frame(event_time + offset)
            crop = frame.crop((0, 285, frame.width, min(frame.height, 685)))
            sheet.paste(crop, (column * cell_width, y + header))
            draw.text(
                (column * cell_width + 7, y + header + 6),
                f"{actual:.1f}s",
                fill="white",
                stroke_width=2,
                stroke_fill="black",
                font=font,
            )
    sheet.save(output, quality=95)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=Path("open/open_labels.xlsx"))
    parser.add_argument("--videos", type=Path, default=Path("open/videos"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/event-sheets"))
    parser.add_argument("--rows", type=int, default=4)
    args = parser.parse_args()
    positives = [(name, time) for name, time in read_labels(args.labels).items() if time]
    build_overview(positives, args.videos, args.output / "positive-overview.jpg")
    for index in range(math.ceil(len(positives) / args.rows)):
        chunk = positives[index * args.rows : (index + 1) * args.rows]
        path = args.output / f"positive-{index + 1:02d}.jpg"
        build_sheet(chunk, args.videos, path)
        print(path)
    for index in range(math.ceil(len(positives) / 3)):
        chunk = positives[index * 3 : (index + 1) * 3]
        build_closeups(chunk, args.videos, args.output / f"closeup-{index + 1:02d}.jpg")


if __name__ == "__main__":
    main()
