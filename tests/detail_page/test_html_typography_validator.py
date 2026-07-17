from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "coupang-detail-page-generator" / "scripts" / "validate_html_typography.py"
PROBE = ROOT / "coupang-detail-page-generator" / "scripts" / "collect_html_typography_metrics.js"
COLLECTOR = ROOT / "coupang-detail-page-generator" / "scripts" / "collect_html_typography_metrics.mjs"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_validator(metrics: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--metrics", str(metrics), *(str(arg) for arg in args)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def element(
    selector: str,
    *,
    text: str = "햇빛은 가리고, 숨길은 열고",
    role: str = "headline",
    lines: list[dict[str, object]] | None = None,
    client_width: float = 300,
    scroll_width: float = 300,
) -> dict[str, object]:
    return {
        "selector": selector,
        "role": role,
        "text": text,
        "rect": {"left": 30, "right": 330, "top": 100, "bottom": 190},
        "client_width": client_width,
        "scroll_width": scroll_width,
        "font_size": 40,
        "line_height": 42,
        "max_lines": 3,
        "allow_short_last_line": False,
        "mid_token_breaks": [],
        "lines": lines
        or [
            {"text": "햇빛은 가리고,", "top": 100, "bottom": 140, "width": 260},
            {"text": "숨길은 열고", "top": 142, "bottom": 182, "width": 210},
        ],
    }


def good_metrics() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "page": "detail-page.html",
        "viewports": [
            {
                "width": width,
                "height": 900,
                "document": {"client_width": width, "scroll_width": width},
                "elements": [element("#title-01")],
            }
            for width in (360, 800)
        ],
    }


def test_typography_metrics_pass_when_required_viewports_are_clean(tmp_path: Path) -> None:
    metrics = tmp_path / "metrics.json"
    report = tmp_path / "report.json"
    write_json(metrics, good_metrics())

    result = run_validator(metrics, "--strict", "--report", report)

    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["summary"] == {"viewports": 2, "elements": 2, "errors": 0, "warnings": 0}


def test_typography_metrics_fail_on_overflow_mid_token_or_orphan_line(tmp_path: Path) -> None:
    payload = good_metrics()
    mobile = payload["viewports"][0]
    mobile["document"]["scroll_width"] = 381
    bad = element(
        "#title-08",
        text="운동복에 맞춰 고르는",
        client_width=300,
        scroll_width=326,
        lines=[
            {"text": "운동복에 맞", "top": 100, "bottom": 140, "width": 280},
            {"text": "춰 고르는", "top": 130, "bottom": 170, "width": 180},
            {"text": "색", "top": 172, "bottom": 212, "width": 28},
        ],
    )
    bad["mid_token_breaks"] = ["맞|춰"]
    mobile["elements"] = [bad]
    metrics = tmp_path / "bad-metrics.json"
    write_json(metrics, payload)

    result = run_validator(metrics, "--strict")

    assert result.returncode == 1
    assert "DOCUMENT_OVERFLOW_X" in result.stderr
    assert "ELEMENT_OVERFLOW_X" in result.stderr
    assert "MID_TOKEN_BREAK" in result.stderr
    assert "SINGLE_CHARACTER_LINE" in result.stderr
    assert "LINE_OVERLAP" in result.stderr
    assert "VERTICAL_CLIP" in result.stderr


def test_typography_metrics_require_360_and_800_viewports(tmp_path: Path) -> None:
    payload = good_metrics()
    payload["viewports"] = payload["viewports"][:1]
    metrics = tmp_path / "missing-wide.json"
    write_json(metrics, payload)

    result = run_validator(metrics, "--strict")

    assert result.returncode == 1
    assert "MISSING_VIEWPORT" in result.stderr


def test_browser_probe_exposes_versioned_metrics_contract() -> None:
    source = PROBE.read_text(encoding="utf-8")

    assert 'schema_version: "1.0"' in source
    assert "mid_token_breaks" in source
    assert "data-typography-max-lines" in source
    assert "window.__collectTypographyMetrics" in source


def test_cdp_collector_documents_repeatable_cli() -> None:
    source = COLLECTOR.read_text(encoding="utf-8")
    result = subprocess.run(
        ["node", str(COLLECTOR), "--help"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--cdp" in result.stdout
    assert "--url" in result.stdout
    assert "--viewports" in result.stdout
    assert "--output" in result.stdout
    assert "--screenshots" in result.stdout
    assert '"Network.setCacheDisabled"' in source
    assert "typography_qa" in source
    assert '"Page.captureScreenshot"' in source
    assert "Math.max(800, settleMs)" in source
    assert source.index("scrollBehavior='auto'") < source.index("document.querySelectorAll('[data-module]').length")
