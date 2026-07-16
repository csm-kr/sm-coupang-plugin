#!/usr/bin/env python3
"""Record an explicit user approval bound to the exact planning artifact hash."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from hybrid_contract import (
    CONTENT_APPROVAL_PATH,
    CONTENT_PLAN_PATH,
    PRODUCT_APPROVAL_PATH,
    PRODUCT_PLAN_PATH,
    load_json,
    sha256,
    validate_content_plan,
    validate_planning,
    validate_product_plan,
)


LOGGER = logging.getLogger("record_user_approval")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record explicit user approval for an exact product or content plan")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--target", choices=("product-plan", "content-plan"), required=True)
    parser.add_argument("--actor-id", required=True, help="User identifier or user-provided approval label")
    parser.add_argument(
        "--confirm-user-approval",
        action="store_true",
        help="Confirm that the user explicitly approved the exact current artifact",
    )
    parser.add_argument("--note", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    if not args.confirm_user_approval:
        LOGGER.error("--confirm-user-approval is required; agent inference cannot replace user approval")
        return 2
    if not args.actor_id.strip():
        LOGGER.error("--actor-id must not be empty")
        return 2

    project = args.project.expanduser().resolve()
    errors: list[str] = []
    if args.target == "product-plan":
        target_relative = PRODUCT_PLAN_PATH
        approval_relative = PRODUCT_APPROVAL_PATH
        target = load_json(project / target_relative, errors, "product-plan")
        errors.extend(validate_product_plan(target))
    else:
        product_errors = validate_planning(project, "product")
        if product_errors:
            errors.extend(f"product-plan gate: {item}" for item in product_errors)
        product = load_json(project / PRODUCT_PLAN_PATH, errors, "product-plan")
        target_relative = CONTENT_PLAN_PATH
        approval_relative = CONTENT_APPROVAL_PATH
        target = load_json(project / target_relative, errors, "content-plan")
        errors.extend(validate_content_plan(project, target, product))

    for error in errors:
        LOGGER.error(error)
    if errors:
        LOGGER.error("approval blocked: errors=%d", len(errors))
        return 1

    target_path = project / target_relative
    record = {
        "schema_version": "1.0",
        "artifact_type": "approval",
        "target_type": args.target.replace("-", "_"),
        "target_path": target_relative,
        "target_sha256": sha256(target_path),
        "decision": "approved",
        "actor_type": "user",
        "actor_id": args.actor_id.strip(),
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": args.note.strip(),
    }
    approval_path = project / approval_relative
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("user approval recorded: target=%s sha256=%s", args.target, record["target_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
