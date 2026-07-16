#!/usr/bin/env python3
"""Validate a numbered detail-page image set."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


NAME_PATTERN = re.compile(r"^(\d{2})(?:-.+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate page count, numbering, format, and exact dimensions")
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--expected-count", type=int, default=10)
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=2400)
    parser.add_argument("--format", default="png")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Treat unrelated visible files as errors")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.images_dir.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    pages: dict[str, Path] = {}
    details: list[dict] = []
    if not root.is_dir():
        errors.append(f"images directory missing: {root}")
    else:
        for path in sorted((value for value in root.iterdir() if value.is_file() and not value.name.startswith(".")), key=lambda value: value.name.casefold()):
            match = NAME_PATTERN.fullmatch(path.stem)
            if not match:
                (errors if args.strict else warnings).append(f"unrecognized visible file: {path.name}")
                continue
            page = match.group(1)
            if page in pages:
                errors.append(f"duplicate page number {page}: {pages[page].name}, {path.name}")
                continue
            pages[page] = path
    expected = [f"{value:02d}" for value in range(1, args.expected_count + 1)]
    if sorted(pages) != expected:
        missing = sorted(set(expected) - set(pages))
        extra = sorted(set(pages) - set(expected))
        if missing:
            errors.append("missing page numbers: " + ", ".join(missing))
        if extra:
            errors.append("unexpected page numbers: " + ", ".join(extra))
    if len(pages) != args.expected_count:
        errors.append(f"expected {args.expected_count} numbered pages, found {len(pages)}")

    try:
        from PIL import Image
    except ImportError:
        errors.append("Pillow is required")
        Image = None
    if Image is not None:
        for page, path in sorted(pages.items()):
            detail = {"page": page, "file": path.name, "status": "fail"}
            if path.suffix.casefold() != "." + args.format.casefold().lstrip("."):
                errors.append(f"{path.name}: expected {args.format} format")
            try:
                with Image.open(path) as image:
                    detail.update({"width": image.width, "height": image.height, "mode": image.mode, "format": image.format})
                    if image.width != args.width or image.height != args.height:
                        errors.append(f"{path.name}: expected {args.width}x{args.height}, got {image.width}x{image.height}")
                    else:
                        detail["status"] = "pass"
            except Exception as exc:
                detail["error"] = str(exc)
                errors.append(f"{path.name}: unreadable image: {exc}")
            details.append(detail)

    report = {"status": "pass" if not errors else "fail", "errors": errors, "warnings": warnings, "pages": details}
    if args.json_output:
        output = args.json_output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in errors:
        print(f"ERROR: {item}", file=sys.stderr)
    for item in warnings:
        print(f"WARNING: {item}", file=sys.stderr)
    print(json.dumps({"status": report["status"], "page_count": len(details), "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
