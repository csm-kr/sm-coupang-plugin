#!/usr/bin/env python3
"""Inspect image files and emit deterministic metadata as JSON and a table."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect image dimensions, mode, ratio, and readability")
    parser.add_argument("--input", type=Path, nargs="+", required=True, help="Image files or directories")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--table-output", type=Path)
    return parser.parse_args()


def hidden(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        relative = path
    return any(part.startswith(".") for part in relative.parts)


def collect(inputs: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for raw in inputs:
        path = raw.expanduser().resolve()
        if path.is_file():
            if not path.name.startswith("."):
                files.add(path)
            continue
        if path.is_dir():
            for item in path.rglob("*"):
                if item.is_file() and item.suffix.casefold() in IMAGE_EXTENSIONS and not hidden(item, path):
                    files.add(item)
    return sorted(files, key=lambda value: value.as_posix().casefold())


def inspect(path: Path) -> dict:
    record = {"file": str(path), "status": "invalid", "error": ""}
    if path.suffix.casefold() not in IMAGE_EXTENSIONS:
        record["error"] = "unsupported extension"
        return record
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            record.update(
                {
                    "status": "valid",
                    "width": width,
                    "height": height,
                    "mode": image.mode,
                    "format": image.format or path.suffix.lstrip(".").upper(),
                    "aspect_ratio": round(width / height, 6) if height else None,
                }
            )
        return record
    except Exception as exc:
        record["error"] = str(exc)
        return record


def table(records: list[dict]) -> str:
    lines = [
        "| 파일 | 상태 | 크기 | 모드 | 비율 | 오류 |",
        "|---|---|---:|---|---:|---|",
    ]
    for item in records:
        size = f"{item.get('width', '')}×{item.get('height', '')}" if item.get("status") == "valid" else ""
        lines.append(
            f"| {Path(item['file']).name} | {item['status']} | {size} | {item.get('mode', '')} | "
            f"{item.get('aspect_ratio', '')} | {str(item.get('error', '')).replace('|', '/')} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    records = [inspect(path) for path in collect(args.input)]
    valid = sum(item["status"] == "valid" for item in records)
    invalid = len(records) - valid
    report = {
        "status": "pass" if records and invalid == 0 else "partial" if valid else "fail",
        "valid_count": valid,
        "invalid_count": invalid,
        "images": records,
    }
    rendered = table(records)
    print(rendered, end="")
    print(json.dumps({key: value for key, value in report.items() if key != "images"}, ensure_ascii=False))
    if args.json_output:
        output = args.json_output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.table_output:
        output = args.table_output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    return 0 if records and invalid == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
