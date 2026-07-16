#!/usr/bin/env python3
"""Validate evidence states and source boundaries in product-facts.json."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Iterator

LOGGER = logging.getLogger("validate_product_facts")

CANONICAL_STATUSES = {
    "CONFIRMED_USER",
    "CONFIRMED_SOURCE",
    "OBSERVED_IMAGE",
    "INFERRED",
    "CONFLICT",
    "UNKNOWN",
    "FORBIDDEN",
}
LEGACY_STATUSES = {
    "verified_text",
    "verified_visual",
    "verified_evidence",
    "uncertain",
    "not_provided",
    "prohibited",
}
ALLOWED_STATUSES = CANONICAL_STATUSES | LEGACY_STATUSES
AD_ALLOWED = {
    "CONFIRMED_USER",
    "CONFIRMED_SOURCE",
    "OBSERVED_IMAGE",
    "verified_text",
    "verified_visual",
    "verified_evidence",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate product fact states, evidence, and sources")
    parser.add_argument("--facts", type=Path, required=True, help="Path to product-facts.json")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--report", type=Path, help="Optional Markdown validation report")
    return parser.parse_args()


def iter_facts(node: Any, path: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(node, dict):
        if "status" in node:
            yield path or "<root>", node
            return
        for key, value in node.items():
            if str(key).startswith("_"):
                continue
            child = f"{path}.{key}" if path else str(key)
            yield from iter_facts(value, child)


def is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def validate_fact(name: str, fact: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    status = fact.get("status")
    value = fact.get("value")
    evidence = fact.get("evidence")
    source = fact.get("source")

    if status not in ALLOWED_STATUSES:
        errors.append(f"{name}: 허용되지 않은 status={status!r}")
        return errors, warnings
    if "value" not in fact:
        errors.append(f"{name}: value 필드가 없습니다")
    if "evidence" not in fact:
        errors.append(f"{name}: evidence 필드가 없습니다")
    if "source" not in fact:
        errors.append(f"{name}: source 필드가 없습니다")
    if source is not None and not isinstance(source, list):
        errors.append(f"{name}: source는 배열이어야 합니다")
        source = []

    if status in AD_ALLOWED:
        if is_empty(value):
            errors.append(f"{name}: {status}에는 비어 있지 않은 value가 필요합니다")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"{name}: {status}에는 구체적인 evidence가 필요합니다")
        if not source:
            errors.append(f"{name}: {status}에는 하나 이상의 source가 필요합니다")
        for item in source or []:
            normalized = str(item).replace("\\", "/").casefold().lstrip("./")
            if normalized.startswith("reference/") or "/reference/" in normalized:
                errors.append(f"{name}: reference 자산을 사실 출처로 사용할 수 없습니다: {item}")
            elif not (
                normalized.startswith("raw/")
                or "/raw/" in normalized
                or normalized.startswith("user:")
                or normalized in {"user", "conversation"}
            ):
                warnings.append(f"{name}: source가 raw/ 또는 사용자 명시 정보인지 확인 필요: {item}")
    elif status in {"INFERRED", "CONFLICT", "UNKNOWN", "uncertain", "not_provided"} and not is_empty(value):
        warnings.append(f"{name}: {status}의 value는 광고에 사용할 수 없습니다; notes로 이동 권장")
    elif status in {"FORBIDDEN", "prohibited"} and not is_empty(value):
        errors.append(f"{name}: {status} 정보에는 광고용 value를 둘 수 없습니다")

    if status == "verified_evidence" and source:
        likely_evidence = ("certificate", "cert", "test", "report", "인증", "시험", "성적")
        if not any(any(token in str(item).casefold() for token in likely_evidence) for item in source):
            warnings.append(f"{name}: verified_evidence 출처가 증빙 파일인지 수동 확인 필요")
    return errors, warnings


def render_report(path: Path, facts_count: int, errors: list[str], warnings: list[str]) -> str:
    lines = [
        "# Product Facts Validation",
        "",
        f"- 파일: `{path}`",
        f"- 검사 사실 수: {facts_count}",
        f"- 오류: {len(errors)}",
        f"- 경고: {len(warnings)}",
        "",
        "## 오류",
        "",
    ]
    lines.extend(f"- {item}" for item in errors)
    if not errors:
        lines.append("- 없음")
    lines.extend(["", "## 경고", ""])
    lines.extend(f"- {item}" for item in warnings)
    if not warnings:
        lines.append("- 없음")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    facts_path = args.facts.expanduser().resolve()
    if not facts_path.is_file():
        LOGGER.error("사실 파일을 찾을 수 없습니다: %s", facts_path)
        return 2
    try:
        data = json.loads(facts_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        LOGGER.error("JSON 구문 오류 %s:%d:%d: %s", facts_path, exc.lineno, exc.colno, exc.msg)
        return 1
    except Exception as exc:
        LOGGER.exception("사실 파일 읽기 실패: %s", exc)
        return 1
    if not isinstance(data, dict):
        LOGGER.error("최상위 JSON 값은 객체여야 합니다")
        return 1

    schema_version = str(data.get("_meta", {}).get("schema_version", ""))

    facts = list(iter_facts(data))
    errors: list[str] = []
    warnings: list[str] = []
    if not facts:
        errors.append("검사 가능한 fact 객체가 없습니다")
    for name, fact in facts:
        fact_errors, fact_warnings = validate_fact(name, fact)
        errors.extend(fact_errors)
        warnings.extend(fact_warnings)
    if schema_version.startswith("3"):
        legacy_used = [name for name, fact in facts if fact.get("status") in LEGACY_STATUSES]
        if legacy_used:
            errors.append("schema 3.x product-facts.json must use canonical Evidence Ledger states: " + ", ".join(legacy_used))

    for item in errors:
        LOGGER.error(item)
    for item in warnings:
        LOGGER.warning(item)
    if args.report:
        report = args.report.expanduser().resolve()
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(render_report(facts_path, len(facts), errors, warnings), encoding="utf-8")
        LOGGER.info("보고서 저장: %s", report)
    if errors or (args.strict and warnings):
        LOGGER.error("검증 실패: 오류 %d, 경고 %d", len(errors), len(warnings))
        return 1
    LOGGER.info("검증 통과: 사실 %d개, 경고 %d개", len(facts), len(warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
