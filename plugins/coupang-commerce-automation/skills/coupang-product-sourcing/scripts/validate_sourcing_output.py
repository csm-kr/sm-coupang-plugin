#!/usr/bin/env python3
"""Validate generated sourcing outputs and enforce shortlist integrity."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


FILES = ["evaluation.json", "candidate-table.csv", "candidate-report.md", "handoff-shortlist.json"]
DECISIONS = {"SHORTLIST", "WATCH", "REJECT"}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate(output_dir: Path, strict: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for name in FILES:
        if not (output_dir / name).is_file():
            errors.append(f"필수 파일 누락: {name}")
    if errors:
        return errors, warnings

    evaluation = json.loads((output_dir / "evaluation.json").read_text(encoding="utf-8-sig"))
    handoff = json.loads((output_dir / "handoff-shortlist.json").read_text(encoding="utf-8-sig"))
    rows = evaluation.get("candidates") or []
    shortlist = [row for row in rows if row.get("decision") == "SHORTLIST"]
    limit = min(int((evaluation.get("run") or {}).get("shortlist_limit", 5)), 5)
    if len(shortlist) > limit:
        errors.append(f"SHORTLIST 수 {len(shortlist)}개가 한도 {limit}개를 초과")
    if handoff.get("count") != len(handoff.get("shortlist") or []) or handoff.get("count") != len(shortlist):
        errors.append("handoff-shortlist.json 개수와 evaluation.json이 일치하지 않음")

    ids: set[str] = set()
    for index, row in enumerate(rows, 1):
        candidate_id = row.get("candidate_id")
        prefix = f"후보 {candidate_id or index}"
        if not candidate_id or candidate_id in ids:
            errors.append(f"{prefix}: 후보 id 누락 또는 중복")
        ids.add(candidate_id)
        if row.get("decision") not in DECISIONS:
            errors.append(f"{prefix}: 판정값 오류")
        if row.get("rank") != index:
            errors.append(f"{prefix}: 순위가 배열 순서와 불일치")
        evidence_urls = row.get("evidence_urls") or []
        if not evidence_urls or any(not is_url(url) for url in evidence_urls):
            errors.append(f"{prefix}: 근거 URL 누락 또는 형식 오류")
        if row.get("decision") == "SHORTLIST":
            total = (row.get("scores") or {}).get("total")
            economics = row.get("economics") or {}
            base = economics.get("base") or {}
            stress = economics.get("stress") or {}
            params = evaluation.get("effective_parameters") or {}
            checks = [
                (is_number(total) and total >= 75, "총점 75점 미만"),
                (not row.get("hard_filter_failures"), "하드 필터 실패 존재"),
                (not row.get("shortlist_blockers"), "SHORTLIST 차단 사유 존재"),
                (is_number(base.get("contribution_profit")) and base["contribution_profit"] >= params.get("min_contribution_profit", 3500), "공헌이익 기준 미달"),
                (is_number(base.get("contribution_margin_pct")) and base["contribution_margin_pct"] >= params.get("min_contribution_margin_pct", 40), "공헌이익률 기준 미달"),
                (is_number(stress.get("contribution_margin_pct")) and stress["contribution_margin_pct"] >= params.get("min_stress_margin_pct", 30), "가격 인하 내성 미달"),
                ((row.get("market_stats") or {}).get("research_complete") is True, "시장조사 미완료"),
                ((row.get("scenario_summary") or {}).get("scenario_complete") is True, "수요 시나리오 미완료"),
            ]
            for passed, message in checks:
                if not passed:
                    errors.append(f"{prefix}: {message}")
            content = row.get("content_handoff") or {}
            if not content.get("sample_checks") or len(content.get("differentiators") or []) != 3 or len(content.get("proof_scenes") or []) != 3 or not content.get("gif_idea"):
                errors.append(f"{prefix}: 콘텐츠 핸드오프 불완전")

    handoff_ids = {row.get("candidate_id") for row in handoff.get("shortlist") or []}
    if handoff_ids != {row.get("candidate_id") for row in shortlist}:
        errors.append("SHORTLIST 후보 id와 핸드오프 후보 id가 일치하지 않음")

    with (output_dir / "candidate-table.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    if len(csv_rows) != len(rows):
        errors.append("CSV 후보 수와 evaluation.json 후보 수가 일치하지 않음")
    report = (output_dir / "candidate-report.md").read_text(encoding="utf-8")
    if "# 쿠팡 상품 소싱 결과" not in report:
        errors.append("candidate-report.md 제목 누락")

    if strict:
        for row in rows:
            if row.get("decision") == "WATCH" and not row.get("decision_reasons"):
                errors.append(f"후보 {row.get('candidate_id')}: WATCH 사유 누락")
    else:
        warnings.extend(error for error in errors if "WATCH 사유" in error)
        errors = [error for error in errors if "WATCH 사유" not in error]
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    errors, warnings = validate(args.output_dir, args.strict)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"검증 실패: 오류 {len(errors)}개")
        return 1
    print("검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
