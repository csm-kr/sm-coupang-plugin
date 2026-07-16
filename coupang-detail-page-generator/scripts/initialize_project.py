#!/usr/bin/env python3
"""Initialize a versioned Coupang detail-page workflow project."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

LOGGER = logging.getLogger("initialize_project")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the workflow 5.3 product/content plans, hybrid HTML, and QA templates")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root")
    parser.add_argument("--force", action="store_true", help="Replace existing template files; use only for an empty or disposable project")
    return parser.parse_args()


def copy_file(source: Path, target: Path, force: bool) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    if existed and not force:
        return "preserved"
    shutil.copy2(source, target)
    return "replaced" if existed else "created"


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    skill_dir = Path(__file__).resolve().parent.parent
    template_root = skill_dir / "assets" / "project-template"
    facts_template = skill_dir / "templates" / "product-facts.json"
    if not template_root.is_dir() or not facts_template.is_file():
        LOGGER.error("skill templates are incomplete: %s", skill_dir)
        return 2

    for directory in (
        project / "raw",
        project / "reference",
        project / "output" / "browser-research" / "competitor-pages",
        project / "output" / "copy",
        project / "output" / "planning",
        project / "output" / "approvals",
        project / "output" / "content-assets",
        project / "output" / "html",
        project / "output" / "qa",
        project / "output" / "generated-pages",
        project / "output" / "typography-pages",
        project / "output" / "images",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    counts = {"created": 0, "replaced": 0, "preserved": 0}
    for source in sorted(path for path in template_root.rglob("*") if path.is_file()):
        relative = source.relative_to(template_root)
        result = copy_file(source, project / "output" / relative, args.force)
        counts[result] += 1
    result = copy_file(facts_template, project / "output" / "product-facts.json", args.force)
    counts[result] += 1

    LOGGER.info(
        "workflow project initialized: %s (created=%d replaced=%d preserved=%d)",
        project,
        counts["created"],
        counts["replaced"],
        counts["preserved"],
    )
    if args.force:
        LOGGER.warning("--force replaced existing template paths; verify that no user content was unintentionally overwritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
