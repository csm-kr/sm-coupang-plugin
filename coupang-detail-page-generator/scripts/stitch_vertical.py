#!/usr/bin/env python3
"""Stitch numbered page PNGs into one vertical JPEG preview."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--quality", type=int, default=92)
    args = parser.parse_args()

    paths = [args.images_dir / f"{page:02d}.png" for page in range(1, 11)]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        for path in missing:
            print(f"[ERROR] missing: {path}")
        return 1

    images: list[Image.Image] = []
    try:
        for path in paths:
            with Image.open(path) as source:
                images.append(source.convert("RGB"))
        widths = {image.width for image in images}
        if len(widths) != 1:
            print(f"[ERROR] widths differ: {sorted(widths)}")
            return 1
        width = images[0].width
        height = sum(image.height for image in images)
        canvas = Image.new("RGB", (width, height), "white")
        y = 0
        for image in images:
            canvas.paste(image, (0, y))
            y += image.height
        args.output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.output, "JPEG", quality=args.quality, optimize=True)
        print(f"[OK] {args.output} ({width}x{height})")
        return 0
    finally:
        for image in images:
            image.close()


if __name__ == "__main__":
    raise SystemExit(main())
