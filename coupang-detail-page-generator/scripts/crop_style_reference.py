#!/usr/bin/env python3
"""Split a tall commercial reference into role-specific art-direction crops."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

from PIL import Image

LOGGER = logging.getLogger("crop_style_reference")

ROLE_RANGES = [
    ("hero", 0.000, 0.135),
    ("problem", 0.115, 0.285),
    ("product", 0.260, 0.465),
    ("feature", 0.440, 0.665),
    ("lifestyle", 0.635, 0.875),
    ("closing", 0.850, 1.000),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crop a tall ecommerce reference by narrative role")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="style")
    parser.add_argument("--quality", type=int, default=95)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    source = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not source.is_file():
        LOGGER.error("reference image not found: %s", source)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [output_dir / f"{args.prefix}-{role}.png" for role, _, _ in ROLE_RANGES]
    manifest_path = output_dir / "manifest.json"
    if not args.force and (manifest_path.exists() or any(path.exists() for path in targets)):
        LOGGER.error("existing crops preserved; use --force to replace")
        return 2
    try:
        with Image.open(source) as image:
            image.load()
            width, height = image.size
            crops = []
            for (role, start_ratio, end_ratio), target in zip(ROLE_RANGES, targets):
                top = max(0, round(height * start_ratio))
                bottom = min(height, round(height * end_ratio))
                crop = image.crop((0, top, width, bottom)).convert("RGB")
                crop.save(target, "PNG", optimize=True)
                crops.append(
                    {
                        "role": role,
                        "file": target.name,
                        "crop_box": [0, top, width, bottom - top],
                        "normalized_y": [start_ratio, end_ratio],
                        "allowed_use": [
                            "composition",
                            "lighting",
                            "palette",
                            "spacing",
                            "scene_density",
                            "visual_rhythm",
                            "typography_hierarchy",
                            "conversion_flow",
                            "module_density",
                        ],
                        "prohibited_transfer": ["copy", "product_claims", "product_identity", "brand", "logo", "model_face", "model_identity", "person_pixels"],
                    }
                )
        manifest = {
            "version": "4.0",
            "source": source.name,
            "source_sha256": sha256(source),
            "source_size": [width, height],
            "policy": "art_direction_only_no_person_identity_no_person_pixels",
            "crops": crops,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        LOGGER.info("created %d role crops in %s", len(crops), output_dir)
    except Exception as exc:
        LOGGER.exception("reference crop failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
