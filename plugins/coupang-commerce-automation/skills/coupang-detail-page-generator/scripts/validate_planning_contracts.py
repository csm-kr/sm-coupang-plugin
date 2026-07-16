#!/usr/bin/env python3
"""Validate separated product/content plans and exact user approvals."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from hybrid_contract import validate_planning


LOGGER = logging.getLogger("validate_planning_contracts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate product-plan and content-plan user approval gates")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument(
        "--gate",
        choices=("product-draft", "product", "content-draft", "content"),
        default="content",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    errors = validate_planning(args.project.expanduser().resolve(), args.gate)
    for error in errors:
        LOGGER.error(error)
    if errors:
        LOGGER.error("planning contract validation failed: errors=%d", len(errors))
        return 1
    LOGGER.info("planning contract validation passed: gate=%s", args.gate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
