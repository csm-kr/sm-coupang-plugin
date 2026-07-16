#!/usr/bin/env python3
"""Compose approved typography pages and synthetic support visuals to 780x3000 PNGs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resize_to_width(image: Image.Image, width: int) -> Image.Image:
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def compose_page(
    primary_path: Path,
    support_path: Path,
    output_path: Path,
    width: int,
    height: int,
    overlap: int,
    centering: tuple[float, float],
) -> dict[str, object]:
    with Image.open(primary_path) as source:
        primary = resize_to_width(source.convert("RGB"), width)

    if primary.height >= height:
        final = ImageOps.fit(
            primary,
            (width, height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.0),
        )
        support_start = height
        actual_overlap = 0
    else:
        actual_overlap = min(overlap, max(0, primary.height // 8))
        support_start = primary.height - actual_overlap
        support_height = height - support_start

        with Image.open(support_path) as source:
            support = ImageOps.fit(
                source.convert("RGB"),
                (width, support_height),
                method=Image.Resampling.LANCZOS,
                centering=centering,
            )

        final = Image.new("RGB", (width, height), "white")
        final.paste(primary, (0, 0))
        final.paste(support, (0, support_start))

        if actual_overlap:
            primary_overlap = primary.crop(
                (0, primary.height - actual_overlap, width, primary.height)
            )
            support_overlap = support.crop((0, 0, width, actual_overlap))
            mask = Image.linear_gradient("L").resize((width, actual_overlap))
            blended = Image.composite(support_overlap, primary_overlap, mask)
            final.paste(blended, (0, support_start))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(output_path, "PNG", optimize=True)

    return {
        "file": output_path.name,
        "width": final.width,
        "height": final.height,
        "sha256": sha256(output_path),
        "primary": str(primary_path),
        "support": str(support_path),
        "primary_scaled_height": primary.height,
        "support_start": support_start,
        "overlap": actual_overlap,
        "source_person_pixels": "none",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--width", type=int, default=780)
    parser.add_argument("--height", type=int, default=3000)
    parser.add_argument("--overlap", type=int, default=48)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapping = json.loads(args.map.read_text(encoding="utf-8"))
    pages: list[dict[str, object]] = []

    for item in mapping["pages"]:
        page = str(item["page"]).zfill(2)
        primary = args.project / item["primary"]
        support = args.project / item["support"]
        output = args.output_dir / f"{page}.png"
        centering_values = item.get("centering", [0.5, 0.5])
        centering = (float(centering_values[0]), float(centering_values[1]))
        pages.append(
            {
                "page": page,
                **compose_page(
                    primary,
                    support,
                    output,
                    args.width,
                    args.height,
                    args.overlap,
                    centering,
                ),
            }
        )

    manifest_path = args.manifest or args.output_dir / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "method": "conditioned_typography_plus_synthetic_support",
                "width": args.width,
                "height": args.height,
                "pages": pages,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[OK] {len(pages)} pages -> {args.output_dir}")
    print(f"[OK] manifest -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
