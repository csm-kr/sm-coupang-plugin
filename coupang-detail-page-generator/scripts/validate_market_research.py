#!/usr/bin/env python3
"""Validate Browser Use competitor research before detail-page planning."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

LOGGER = logging.getLogger("validate_market_research")


def load_json(path: Path, errors: list[str]) -> dict:
    if not path.is_file():
        errors.append(f"missing: {path}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"invalid JSON {path}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path}")
        return {}
    return value


def nonempty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(str(item).strip() for item in value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Browser Use market research artifacts")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", default="output")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    root = project / args.output_root / "browser-research"
    workflow_v5 = (project / args.output_root / "project-manifest.yaml").is_file()
    workflow_v52 = False
    if workflow_v5:
        manifest_text = (project / args.output_root / "project-manifest.yaml").read_text(encoding="utf-8-sig")
        workflow_v52 = bool(re.search(r"^workflow_version:\s*[\"']?5\.[23][\"']?\s*$", manifest_text, re.MULTILINE))
    errors: list[str] = []
    warnings: list[str] = []

    source = load_json(root / "source-product.json", errors)
    competitors_doc = load_json(root / "competitors.json", errors)
    appeal_map = load_json(root / "appeal-map.json", errors)
    sources_md = root / "sources.md"
    principles_md = project / args.output_root / "planning-principles.md"
    pain_map_md = project / args.output_root / "competitor-pain-map.md"
    if not sources_md.is_file():
        errors.append(f"missing: {sources_md}")
    if not principles_md.is_file():
        errors.append(f"missing: {principles_md}")
    if workflow_v5 and not pain_map_md.is_file():
        errors.append(f"missing: {pain_map_md}")

    if source:
        for field in ("source_url", "captured_at", "product_name", "detail_asset"):
            if not str(source.get(field, "")).strip():
                errors.append(f"source-product.json missing {field}")
        if not nonempty_list(source.get("verified_facts")):
            errors.append("source-product.json requires verified_facts")
        asset = project / str(source.get("detail_asset", ""))
        if str(source.get("detail_asset", "")).strip() and not asset.is_file():
            errors.append(f"source detail asset missing: {asset}")

    competitors = competitors_doc.get("competitors", []) if competitors_doc else []
    if not isinstance(competitors, list) or len(competitors) < 5:
        errors.append("competitors.json requires at least five competitors")
        competitors = []
    urls: set[str] = set()
    evidence_kinds: set[str] = set()
    competitor_types: set[str] = set()
    for index, item in enumerate(competitors, start=1):
        if not isinstance(item, dict):
            errors.append(f"competitor {index} must be an object")
            continue
        url = str(item.get("url", "")).strip()
        host = urlparse(url).netloc.lower()
        if "coupang.com" not in host:
            errors.append(f"competitor {index} is not a Coupang URL")
        if url in urls:
            errors.append(f"duplicate competitor URL: {url}")
        urls.add(url)
        if not str(item.get("title", "")).strip():
            errors.append(f"competitor {index} missing title")
        if workflow_v5:
            competitor_type = str(item.get("competitor_type", "")).strip()
            if competitor_type not in {"same_model", "direct_structure", "alternative_solution"}:
                errors.append(f"competitor {index} requires a valid competitor_type")
            else:
                competitor_types.add(competitor_type)
            if not nonempty_list(item.get("buyer_tension")):
                errors.append(f"competitor {index} requires buyer_tension")
            if str(item.get("review_evidence_status", "")) not in {"verified", "limited", "unavailable"}:
                errors.append(f"competitor {index} requires review_evidence_status")
            if workflow_v52:
                scope = item.get("review_scope", {})
                if not isinstance(scope, dict):
                    errors.append(f"competitor {index} review_scope must be an object")
                else:
                    if scope.get("source_mode") not in {"full_review", "partial_review", "search_snippet", "unavailable"}:
                        errors.append(f"competitor {index} review_scope.source_mode is invalid")
                    if not str(scope.get("captured_at", "")).strip():
                        errors.append(f"competitor {index} review_scope.captured_at is required")
                    if not isinstance(scope.get("accessed_reviews"), int) or int(scope.get("accessed_reviews", -1)) < 0:
                        errors.append(f"competitor {index} review_scope.accessed_reviews must be a non-negative integer")
        if not nonempty_list(item.get("observed_appeals")):
            errors.append(f"competitor {index} requires observed_appeals")
        modules = item.get("evidence_modules", [])
        if not nonempty_list(modules):
            errors.append(f"competitor {index} requires evidence_modules")
        else:
            evidence_kinds.update(str(value).strip() for value in modules)
        detail_asset = str(item.get("detail_asset", "")).strip()
        if not detail_asset:
            errors.append(f"competitor {index} missing detail_asset")
        elif not (project / detail_asset).is_file():
            errors.append(f"competitor detail asset missing: {project / detail_asset}")
    if competitors and len(evidence_kinds) < 3:
        errors.append("competitor research requires at least three distinct evidence modules")
    if workflow_v5 and "direct_structure" not in competitor_types:
        errors.append("version-5 market research requires direct_structure competitors")

    principles = appeal_map.get("category_decision_principles", []) if appeal_map else []
    appeals = appeal_map.get("appeals", []) if appeal_map else []
    selected = appeal_map.get("selected_appeals", []) if appeal_map else []
    forbidden = appeal_map.get("forbidden_transfers", []) if appeal_map else []
    planning_rule = appeal_map.get("planning_rule", {}) if appeal_map else {}
    if not nonempty_list(principles) or len(principles) < 3:
        errors.append("appeal-map.json requires at least three category_decision_principles")
    if not isinstance(appeals, list) or len(appeals) < 3:
        errors.append("appeal-map.json requires at least three appeals")
        appeals = []
    approved_names: set[str] = set()
    for index, item in enumerate(appeals, start=1):
        if not isinstance(item, dict):
            errors.append(f"appeal {index} must be an object")
            continue
        name = str(item.get("appeal", "")).strip()
        status = str(item.get("status", "")).strip()
        if not name or status not in {"approved", "rejected"}:
            errors.append(f"appeal {index} requires appeal and approved/rejected status")
            continue
        if status == "approved":
            approved_names.add(name)
            if not nonempty_list(item.get("competitor_support")):
                errors.append(f"approved appeal lacks competitor_support: {name}")
            if not nonempty_list(item.get("own_product_evidence")):
                errors.append(f"approved appeal lacks own_product_evidence: {name}")
    if not nonempty_list(selected) or len(selected) < 3:
        errors.append("appeal-map.json requires at least three selected_appeals")
    else:
        for name in selected:
            if str(name).strip() not in approved_names:
                errors.append(f"selected appeal is not approved: {name}")
    if not nonempty_list(forbidden):
        warnings.append("forbidden_transfers is empty")

    if not isinstance(planning_rule, dict):
        errors.append("appeal-map.json planning_rule must be an object")
    else:
        for field in ("market_problem", "category_decision", "own_product_answer", "proof_strategy"):
            if not str(planning_rule.get(field, "")).strip():
                errors.append(f"appeal-map.json planning_rule missing {field}")
        if not nonempty_list(planning_rule.get("page_flow")):
            errors.append("appeal-map.json planning_rule requires page_flow")

    if principles_md.is_file():
        principles_text = principles_md.read_text(encoding="utf-8-sig")
        for heading in ("## 한 줄 기획 원리", "## 구매 판단 흐름", "## 승인 소구", "## 금지 전이"):
            if heading not in principles_text:
                errors.append(f"planning-principles.md missing heading: {heading}")
    if workflow_v5 and pain_map_md.is_file():
        pain_text = pain_map_md.read_text(encoding="utf-8-sig")
        data_rows = [
            line for line in pain_text.splitlines()
            if line.strip().startswith("|")
            and not set(line.replace("|", "").replace(":", "").strip()) <= {"-"}
            and "Pain ID" not in line
        ]
        if not any(len([cell for cell in row.strip("|").split("|") if cell.strip()]) >= 6 for row in data_rows):
            errors.append("competitor-pain-map.md requires at least one completed evidence row")

    for item in errors:
        LOGGER.error(item)
    for item in warnings:
        LOGGER.warning(item)
    if errors or (args.strict and warnings):
        LOGGER.error("market research validation failed: errors=%d warnings=%d", len(errors), len(warnings))
        return 1
    LOGGER.info(
        "market research validation passed: competitors=%d selected_appeals=%d evidence_modules=%d",
        len(competitors),
        len(selected) if isinstance(selected, list) else 0,
        len(evidence_kinds),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
