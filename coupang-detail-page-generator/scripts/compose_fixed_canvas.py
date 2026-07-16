#!/usr/bin/env python3
"""Compose approved typography pages to the exact project-manifest canvas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from compose_780x3000 import compose_page


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose pages to the exact project canvas")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--overlap", type=int, default=48)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    project_manifest_path = project / "output" / "project-manifest.yaml"
    project_manifest = yaml.safe_load(project_manifest_path.read_text(encoding="utf-8-sig")) or {}
    canvas = project_manifest.get("project", {}).get("canvas", {})
    width = int(canvas.get("width", 0))
    height = int(canvas.get("height", 0))
    if width <= 0 or height <= 0:
        raise SystemExit("[ERROR] project manifest requires positive canvas width and height")

    mapping_path = args.map.expanduser().resolve()
    mapping = json.loads(mapping_path.read_text(encoding="utf-8-sig"))
    output_dir = (args.output_dir or project / "output" / "images").expanduser().resolve()
    pages: list[dict[str, object]] = []
    for item in mapping["pages"]:
        page = str(item["page"]).zfill(2)
        primary = project / item["primary"]
        support = project / item["support"]
        centering_values = item.get("centering", [0.5, 0.5])
        result = compose_page(
            primary,
            support,
            output_dir / f"{page}.png",
            width,
            height,
            args.overlap,
            (float(centering_values[0]), float(centering_values[1])),
        )
        pages.append({"page": page, **result})

    manifest_path = args.manifest or project / "output" / "fixed-canvas-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "1.1",
                "method": "conditioned_typography_plus_synthetic_support",
                "width": width,
                "height": height,
                "pages": pages,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[OK] {len(pages)} pages -> {output_dir} ({width}x{height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
