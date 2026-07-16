#!/usr/bin/env python3
"""Validate every visual material and module QA record before HTML assembly."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from hybrid_contract import validate_materials


LOGGER = logging.getLogger("validate_material_qa")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate content assets and per-module automated and visual QA")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    errors, content, assets, material_qa = validate_materials(args.project.expanduser().resolve())
    for error in errors:
        LOGGER.error(error)
    if errors:
        LOGGER.error("material QA validation failed: errors=%d", len(errors))
        return 1
    LOGGER.info(
        "material QA validation passed: modules=%d assets=%d records=%d",
        len(content.get("modules", [])),
        len(assets.get("assets", [])),
        len(material_qa.get("materials", [])),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
