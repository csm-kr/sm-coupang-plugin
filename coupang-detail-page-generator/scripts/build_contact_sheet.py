#!/usr/bin/env python3
"""Build a ten-page QA contact sheet with role, density, and asset provenance."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger("build_contact_sheet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build output/contact-sheet.jpg from ten page images")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--images-dir", type=Path, help="Defaults to <project>/output/images")
    parser.add_argument("--output", type=Path, help="Defaults to <project>/output/contact-sheet.jpg")
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--thumb-width", type=int, default=220)
    parser.add_argument("--gap", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    if args.columns < 1 or args.thumb_width < 64 or args.gap < 0:
        LOGGER.error("columns, thumb-width, gap 값을 확인하세요")
        return 2
    project = args.project.expanduser().resolve()
    images_dir = (args.images_dir or project / "output" / "images").expanduser().resolve()
    output = (args.output or project / "output" / "contact-sheet.jpg").expanduser().resolve()
    paths = [images_dir / f"{index:02d}.png" for index in range(1, 11)]
    missing = [path for path in paths if not path.is_file()]
    if missing:
        for path in missing:
            LOGGER.error("이미지 누락: %s", path)
        return 2
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError:
        LOGGER.error("Pillow가 필요합니다: python -m pip install Pillow")
        return 2
    opened = []
    try:
        max_ratio = 0.0
        for path in paths:
            image = Image.open(path).convert("RGB")
            opened.append(image)
            max_ratio = max(max_ratio, image.height / image.width)
        thumb_height = int(args.thumb_width * max_ratio)
        label_height = max(66, args.thumb_width // 3)
        cell_width = args.thumb_width
        cell_height = thumb_height + label_height
        rows = (len(paths) + args.columns - 1) // args.columns
        sheet_width = args.gap + args.columns * (cell_width + args.gap)
        sheet_height = args.gap + rows * (cell_height + args.gap)
        sheet = Image.new("RGB", (sheet_width, sheet_height), "#f2f2f2")
        draw = ImageDraw.Draw(sheet)
        font = ImageFont.load_default()
        manifest_path = project / "output" / "render-manifest.json"
        manifest = {}
        if manifest_path.is_file():
            data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            manifest = {str(item["page"]).zfill(2): item for item in data.get("pages", [])}
        for index, image in enumerate(opened, start=1):
            row = (index - 1) // args.columns
            column = (index - 1) % args.columns
            x = args.gap + column * (cell_width + args.gap)
            y = args.gap + row * (cell_height + args.gap)
            thumb = ImageOps.contain(image, (cell_width, thumb_height), method=Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (cell_width, thumb_height), "white")
            tile.paste(thumb, ((cell_width - thumb.width) // 2, (thumb_height - thumb.height) // 2))
            sheet.paste(tile, (x, y))
            page = f"{index:02d}"
            item = manifest.get(page, {})
            layout = item.get("layout", "")
            role = item.get("role", "")
            asset_ids = item.get("asset_ids", [])
            density = item.get("content_span_ratio")
            label = f"{page} · {layout}"
            density_label = f"content {density:.0%}" if isinstance(density, (int, float)) else ""
            campaign_label = f"{role} · assets {len(asset_ids)}"
            draw.text((x + 4, y + thumb_height + 6), label, fill="#111111", font=font)
            draw.text((x + 4, y + thumb_height + 22), density_label, fill="#555555", font=font)
            draw.text((x + 4, y + thumb_height + 38), campaign_label, fill="#355f8a", font=font)
        output.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output, format="JPEG", quality=92, optimize=True)
    except Exception as exc:
        LOGGER.exception("contact sheet 생성 실패: %s", exc)
        return 1
    finally:
        for image in opened:
            image.close()
    LOGGER.info("contact sheet 저장: %s", output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
