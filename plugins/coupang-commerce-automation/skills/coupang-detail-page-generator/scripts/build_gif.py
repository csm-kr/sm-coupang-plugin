#!/usr/bin/env python3
"""Build a normalized looping GIF from approved still-image frames."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PIL import Image, ImageOps


LOGGER = logging.getLogger("build_gif")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a looping crossfade GIF from still-image frames")
    parser.add_argument("--frames", type=Path, nargs="+", required=True, help="Ordered input still images")
    parser.add_argument("--output", type=Path, required=True, help="Output .gif path")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=960)
    parser.add_argument("--fit", choices=("cover", "contain"), default="cover")
    parser.add_argument("--background", default="#eef5f7", help="Contain-mode canvas color")
    parser.add_argument("--hold-ms", type=int, default=650, help="Duration of each source still")
    parser.add_argument("--transition-ms", type=int, default=90, help="Duration of each blend frame")
    parser.add_argument("--transition-frames", type=int, default=6)
    parser.add_argument("--loop", type=int, default=0, help="GIF loop count; 0 means infinite")
    args = parser.parse_args()
    if len(args.frames) < 2:
        parser.error("at least two input frames are required")
    if args.width < 1 or args.height < 1:
        parser.error("width and height must be positive")
    if args.hold_ms < 20 or args.transition_ms < 20:
        parser.error("frame durations must be at least 20ms")
    if args.transition_frames < 1:
        parser.error("transition-frames must be positive")
    if args.output.suffix.casefold() != ".gif":
        parser.error("output path must end with .gif")
    return args


def normalize_frame(path: Path, *, size: tuple[int, int], fit: str, background: str) -> Image.Image:
    with Image.open(path) as source:
        frame = ImageOps.exif_transpose(source).convert("RGBA")
    if fit == "cover":
        return ImageOps.fit(frame, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    contained = ImageOps.contain(frame, size, method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, background)
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    canvas.alpha_composite(contained, offset)
    return canvas


def build_animation(
    frames: list[Image.Image],
    *,
    hold_ms: int,
    transition_ms: int,
    transition_frames: int,
) -> tuple[list[Image.Image], list[int]]:
    animation: list[Image.Image] = []
    durations: list[int] = []
    for current, following in zip(frames, frames[1:]):
        animation.append(current.convert("P", palette=Image.Palette.ADAPTIVE))
        durations.append(hold_ms)
        for step in range(1, transition_frames + 1):
            alpha = step / (transition_frames + 1)
            blended = Image.blend(current, following, alpha)
            animation.append(blended.convert("P", palette=Image.Palette.ADAPTIVE))
            durations.append(transition_ms)
    animation.append(frames[-1].convert("P", palette=Image.Palette.ADAPTIVE))
    durations.append(hold_ms)
    return animation, durations


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    missing = [str(path) for path in args.frames if not path.is_file()]
    if missing:
        LOGGER.error("input frame missing: %s", ", ".join(missing))
        return 2
    try:
        normalized = [
            normalize_frame(
                path,
                size=(args.width, args.height),
                fit=args.fit,
                background=args.background,
            )
            for path in args.frames
        ]
        animation, durations = build_animation(
            normalized,
            hold_ms=args.hold_ms,
            transition_ms=args.transition_ms,
            transition_frames=args.transition_frames,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        animation[0].save(
            args.output,
            format="GIF",
            save_all=True,
            append_images=animation[1:],
            duration=durations,
            loop=args.loop,
            disposal=2,
            optimize=False,
        )
    except Exception as exc:
        LOGGER.error("GIF build failed: %s", exc)
        return 1
    LOGGER.info(
        "GIF created: %s frames=%d canvas=%dx%d",
        args.output,
        len(animation),
        args.width,
        args.height,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
