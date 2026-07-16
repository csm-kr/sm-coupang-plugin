#!/usr/bin/env python3
"""Validate material QA and the integrated editable HTML package."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from hybrid_contract import (
    ASSET_MANIFEST_PATH,
    CONTENT_PLAN_PATH,
    INTEGRATION_GATES,
    INTEGRATION_QA_PATH,
    MATERIAL_QA_PATH,
    load_json,
    sha256,
    validate_materials,
)


LOGGER = logging.getLogger("validate_hybrid_package")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a hybrid HTML detail-page package after material QA")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def relative_asset_url(value: str) -> str:
    normalized = PurePosixPath(value.replace("\\", "/"))
    return quote(PurePosixPath("..", "content-assets", *normalized.parts[2:]).as_posix(), safe="/._-")


def validate_package(project: Path, strict: bool = False) -> tuple[list[str], list[str]]:
    errors, content, assets, _ = validate_materials(project)
    warnings: list[str] = []
    html_path = project / "output" / "html" / "detail-page.html"
    css_path = project / "output" / "html" / "styles.css"
    package_path = project / "output" / "html" / "package-manifest.json"
    package = load_json(package_path, errors, "hybrid package manifest")
    if not html_path.is_file():
        errors.append("hybrid HTML missing: output/html/detail-page.html")
    if not css_path.is_file():
        errors.append("hybrid stylesheet missing: output/html/styles.css")
    if errors:
        return errors, warnings

    if package.get("schema_version") != "1.0" or package.get("workflow_version") != "5.3":
        errors.append("hybrid package must use schema 1.0 and workflow 5.3")
    if package.get("rendering_mode") != "hybrid_html":
        errors.append("hybrid package rendering_mode must be hybrid_html")
    expected_hashes = {
        "content_plan_sha256": sha256(project / CONTENT_PLAN_PATH),
        "asset_manifest_sha256": sha256(project / ASSET_MANIFEST_PATH),
        "material_qa_sha256": sha256(project / MATERIAL_QA_PATH),
    }
    for field, expected in expected_hashes.items():
        if str(package.get(field, "")).casefold() != expected:
            errors.append(f"hybrid package {field} is stale")
    for field, path in (("html", html_path), ("stylesheet", css_path)):
        record = package.get(field)
        if not isinstance(record, dict) or str(record.get("sha256", "")).casefold() != sha256(path):
            errors.append(f"hybrid package {field} SHA-256 is stale")

    html_text = html_path.read_text(encoding="utf-8-sig")
    css_text = css_path.read_text(encoding="utf-8-sig")
    if "data:image" in html_text.casefold():
        errors.append("hybrid HTML must keep visual assets external; data:image is forbidden")
    if '<meta name="viewport"' not in html_text:
        errors.append("hybrid HTML viewport metadata is missing")
    if '<html lang="ko">' not in html_text:
        errors.append("hybrid HTML language must be ko")
    if "overflow-x: hidden" not in css_text or "width: min(100%, var(--page-width))" not in css_text:
        errors.append("hybrid stylesheet must enforce mobile width and prevent horizontal overflow")

    modules = sorted(content.get("modules", []), key=lambda item: int(item.get("order", 0)))
    package_modules = package.get("modules")
    if not isinstance(package_modules, list) or [item.get("id") for item in package_modules] != [item.get("id") for item in modules]:
        errors.append("hybrid package module order differs from content-plan")
    for module in modules:
        module_id = str(module.get("id", ""))
        if f'data-module-id="{module_id}"' not in html_text:
            errors.append(f"hybrid HTML module missing: {module_id}")
        if str(module.get("headline", "")) not in html_text or str(module.get("body", "")) not in html_text:
            errors.append(f"hybrid HTML native copy differs from content-plan: {module_id}")
        if f'data-editable-field="headline"' not in html_text or f'data-editable-field="body"' not in html_text:
            errors.append("hybrid HTML must mark native headline and body fields as editable")
    for asset in assets.get("assets", []):
        if not isinstance(asset, dict):
            continue
        source = relative_asset_url(str(asset.get("path", "")))
        if source not in html_text:
            errors.append(f"hybrid HTML does not reference content asset: {asset.get('id', '')}")
        alt = str(asset.get("alt", ""))
        if alt not in html_text:
            errors.append(f"hybrid HTML alt text missing: {asset.get('id', '')}")

    integration = load_json(project / INTEGRATION_QA_PATH, errors, "integration QA")
    if integration:
        if integration.get("schema_version") != "1.0":
            errors.append("integration QA schema_version must be 1.0")
        if str(integration.get("package_manifest_sha256", "")).casefold() != sha256(package_path):
            errors.append("integration QA is stale or not bound to the current package")
        gates = integration.get("gates")
        if not isinstance(gates, dict) or not INTEGRATION_GATES.issubset(gates):
            errors.append("integration QA is missing required gates")
        else:
            failed = sorted(gate for gate in INTEGRATION_GATES if gates.get(gate) != "pass")
            if failed:
                errors.append(f"integration QA failed gates: {', '.join(failed)}")
        if integration.get("automated_status") != "pass":
            errors.append("integration QA automated_status must pass")
        if integration.get("visual_review_status") != "pass":
            errors.append("integration QA visual_review_status must pass")
        if integration.get("status") != "pass":
            errors.append("integration QA status must pass")
    if strict and not re.search(r"<h2\b", html_text, re.IGNORECASE):
        errors.append("strict hybrid QA requires semantic section headings")
    return errors, warnings


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    errors, warnings = validate_package(args.project.expanduser().resolve(), args.strict)
    for error in errors:
        LOGGER.error(error)
    for warning in warnings:
        LOGGER.warning(warning)
    if errors or (args.strict and warnings):
        LOGGER.error("hybrid package validation failed: errors=%d warnings=%d", len(errors), len(warnings))
        return 1
    LOGGER.info("hybrid package validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
