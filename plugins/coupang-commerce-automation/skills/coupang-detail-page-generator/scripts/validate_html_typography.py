#!/usr/bin/env python3
"""Validate browser-measured HTML typography and line-break metrics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
DEFAULT_REQUIRED_VIEWPORTS = (360, 800)
ALNUM_HANGUL = re.compile(r"[0-9A-Za-z가-힣]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="브라우저에서 수집한 HTML 줄바꿈·타이포그래피 좌표를 검증합니다."
    )
    parser.add_argument("--metrics", required=True, type=Path, help="수집된 typography-metrics.json")
    parser.add_argument("--report", type=Path, help="검증 결과 JSON 저장 경로")
    parser.add_argument(
        "--required-viewports",
        nargs="+",
        type=int,
        default=list(DEFAULT_REQUIRED_VIEWPORTS),
        help="필수 CSS viewport 폭. 기본값: 360 800",
    )
    parser.add_argument("--strict", action="store_true", help="경고도 실패로 처리")
    return parser.parse_args()


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compact_chars(text: str) -> str:
    return "".join(ALNUM_HANGUL.findall(text or ""))


def add_issue(
    issues: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    viewport: int | None,
    selector: str | None,
    message: str,
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "viewport": viewport,
            "selector": selector,
            "message": message,
        }
    )


def validate_element(
    element: dict[str, Any],
    *,
    viewport: int,
    document_width: float,
    issues: list[dict[str, Any]],
) -> None:
    selector = str(element.get("selector") or "<unknown>")
    role = str(element.get("role") or "text")
    client_width = number(element.get("client_width"))
    scroll_width = number(element.get("scroll_width"))
    if scroll_width > client_width + 1:
        add_issue(
            issues,
            severity="error",
            code="ELEMENT_OVERFLOW_X",
            viewport=viewport,
            selector=selector,
            message=f"요소 폭 {client_width:g}px보다 내용 폭 {scroll_width:g}px가 큽니다.",
        )

    rect = element.get("rect") or {}
    left = number(rect.get("left"))
    right = number(rect.get("right"))
    if left < -1 or right > document_width + 1:
        add_issue(
            issues,
            severity="error",
            code="ELEMENT_CLIPPED_X",
            viewport=viewport,
            selector=selector,
            message=f"요소 좌우 좌표 {left:g}~{right:g}px가 문서 폭 {document_width:g}px를 벗어납니다.",
        )

    lines = [line for line in element.get("lines", []) if str(line.get("text") or "").strip()]
    if not lines:
        add_issue(
            issues,
            severity="error",
            code="NO_RENDERED_LINES",
            viewport=viewport,
            selector=selector,
            message="표시 텍스트의 렌더링 행을 찾지 못했습니다.",
        )
        return

    max_lines = int(number(element.get("max_lines"), 0))
    if max_lines and len(lines) > max_lines:
        add_issue(
            issues,
            severity="error",
            code="TOO_MANY_LINES",
            viewport=viewport,
            selector=selector,
            message=f"허용 {max_lines}행을 넘어 {len(lines)}행으로 표시됩니다.",
        )

    for boundary in element.get("mid_token_breaks", []):
        add_issue(
            issues,
            severity="error",
            code="MID_TOKEN_BREAK",
            viewport=viewport,
            selector=selector,
            message=f"단어 또는 숫자 중간에서 줄이 끊겼습니다: {boundary}",
        )

    rect_top = number(rect.get("top"))
    rect_bottom = number(rect.get("bottom"))
    font_size = number(element.get("font_size"))
    line_height = number(element.get("line_height"), font_size * 1.2)
    for index, line in enumerate(lines):
        text = str(line.get("text") or "").strip()
        line_top = number(line.get("top"))
        line_bottom = number(line.get("bottom"))
        vertical_tolerance = max(2.0, font_size * 0.4)
        if line_top < rect_top - vertical_tolerance or line_bottom > rect_bottom + vertical_tolerance:
            add_issue(
                issues,
                severity="error",
                code="VERTICAL_CLIP",
                viewport=viewport,
                selector=selector,
                message=f"{index + 1}행이 텍스트 요소의 세로 경계를 벗어납니다.",
            )
        if len(lines) > 1 and len(compact_chars(text)) <= 1:
            add_issue(
                issues,
                severity="error",
                code="SINGLE_CHARACTER_LINE",
                viewport=viewport,
                selector=selector,
                message=f"{index + 1}행이 한 글자만 남았습니다: {text!r}",
            )
        if index:
            previous = lines[index - 1]
            previous_top = number(previous.get("top"))
            line_advance = line_top - previous_top
            if line_height and line_advance < line_height * 0.82:
                add_issue(
                    issues,
                    severity="error",
                    code="LINE_OVERLAP",
                    viewport=viewport,
                    selector=selector,
                    message=f"{index}행과 {index + 1}행의 글자 영역이 겹칩니다.",
                )
            elif line_height and line_advance < line_height * 0.88:
                add_issue(
                    issues,
                    severity="error",
                    code="LINE_ADVANCE_TOO_TIGHT",
                    viewport=viewport,
                    selector=selector,
                    message="행 기준선 간격이 CSS line-height의 88%보다 좁습니다.",
                )

    if "\ufffd" in str(element.get("text") or ""):
        add_issue(
            issues,
            severity="error",
            code="BROKEN_GLYPH",
            viewport=viewport,
            selector=selector,
            message="대체 문자 U+FFFD가 포함되어 있습니다.",
        )

    allow_short = bool(element.get("allow_short_last_line"))
    if len(lines) > 1 and role in {"headline", "body"} and not allow_short:
        widths = [number(line.get("width")) for line in lines]
        widest = max(widths, default=0)
        last_text = str(lines[-1].get("text") or "").strip()
        last_chars = len(compact_chars(last_text))
        if widest and widths[-1] / widest < 0.28 and last_chars <= 4:
            add_issue(
                issues,
                severity="warning",
                code="SHORT_LAST_LINE",
                viewport=viewport,
                selector=selector,
                message=f"마지막 행이 지나치게 짧습니다: {last_text!r}",
            )


def validate(payload: dict[str, Any], required_viewports: list[int]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        add_issue(
            issues,
            severity="error",
            code="SCHEMA_VERSION",
            viewport=None,
            selector=None,
            message=f"schema_version은 {SCHEMA_VERSION!r}이어야 합니다.",
        )

    viewports = payload.get("viewports")
    if not isinstance(viewports, list):
        viewports = []
        add_issue(
            issues,
            severity="error",
            code="INVALID_VIEWPORTS",
            viewport=None,
            selector=None,
            message="viewports는 배열이어야 합니다.",
        )

    found = {int(number(viewport.get("width"))) for viewport in viewports if isinstance(viewport, dict)}
    for required in required_viewports:
        if required not in found:
            add_issue(
                issues,
                severity="error",
                code="MISSING_VIEWPORT",
                viewport=required,
                selector=None,
                message=f"필수 {required}px 렌더링 측정값이 없습니다.",
            )

    element_count = 0
    for viewport_data in viewports:
        if not isinstance(viewport_data, dict):
            continue
        viewport = int(number(viewport_data.get("width")))
        document = viewport_data.get("document") or {}
        client_width = number(document.get("client_width"), viewport)
        scroll_width = number(document.get("scroll_width"), client_width)
        if scroll_width > client_width + 1:
            add_issue(
                issues,
                severity="error",
                code="DOCUMENT_OVERFLOW_X",
                viewport=viewport,
                selector=None,
                message=f"문서 폭 {client_width:g}px보다 스크롤 폭 {scroll_width:g}px가 큽니다.",
            )
        elements = viewport_data.get("elements") or []
        element_count += len(elements)
        for element_data in elements:
            if isinstance(element_data, dict):
                validate_element(
                    element_data,
                    viewport=viewport,
                    document_width=client_width,
                    issues=issues,
                )

    errors = sum(issue["severity"] == "error" for issue in issues)
    warnings = sum(issue["severity"] == "warning" for issue in issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "html_typography_qa",
        "source_page": payload.get("page"),
        "status": "pass" if not errors and not warnings else "fail" if errors else "pass_with_warnings",
        "summary": {
            "viewports": len(viewports),
            "elements": element_count,
            "errors": errors,
            "warnings": warnings,
        },
        "issues": issues,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    try:
        payload = json.loads(args.metrics.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"metrics 파일을 읽을 수 없습니다: {exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("metrics 루트는 객체여야 합니다.", file=sys.stderr)
        return 2

    report = validate(payload, list(dict.fromkeys(args.required_viewports)))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for issue in report["issues"]:
        viewport = f" [{issue['viewport']}px]" if issue["viewport"] is not None else ""
        selector = f" {issue['selector']}:" if issue["selector"] else ":"
        print(f"{issue['code']}{viewport}{selector} {issue['message']}", file=sys.stderr)

    summary = report["summary"]
    print(
        "typography-qa: "
        f"{report['status']} | viewports={summary['viewports']} elements={summary['elements']} "
        f"errors={summary['errors']} warnings={summary['warnings']}"
    )
    if summary["errors"]:
        return 1
    if args.strict and summary["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
