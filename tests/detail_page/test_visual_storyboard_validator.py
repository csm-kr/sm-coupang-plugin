from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "coupang-detail-page-generator" / "scripts"
STORYBOARD_VALIDATOR = SCRIPTS / "validate_visual_storyboard.py"
LAYOUT_VALIDATOR = SCRIPTS / "validate_visual_layout.py"
PROBE = SCRIPTS / "collect_visual_layout_metrics.js"
COLLECTOR = SCRIPTS / "collect_visual_layout_metrics.mjs"


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_python(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *(str(arg) for arg in args)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def prompt() -> dict[str, object]:
    return {
        "use_case": "ads-marketing",
        "asset_type": "detail-page evidence visual",
        "primary_request": "합성 성인 모델이 목까지 이어지는 페이스커버를 착용한 장면",
        "subject": "텍스트에서 새로 만든 성인 합성 모델과 연출용 페이스커버",
        "composition": "가슴 위 세로 구도, 눈 아래부터 쇄골 위까지 모두 보이게",
        "claim_link": "얼굴과 목을 함께 감싸는 커버 범위를 시각화",
        "measurement_guidance": "숫자는 생성하지 않고 A~E 기준점용 여백만 확보",
        "constraints": [
            "실제 사람 픽셀 사용 금지",
            "문자·숫자·로고 생성 금지",
            "concept_only 제품을 실제 SKU 증거로 표현 금지",
        ],
        "avoid": ["잘린 턱선", "가려진 목 끝단", "추가 스트랩", "워터마크"],
    }


def good_storyboard() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "artifact_type": "visual_storyboard",
        "asset_scope": "concept_only",
        "module_count": 2,
        "primary_claim_ids": ["CLAIM-COVER"],
        "required_measurement_ids": ["A", "B"],
        "acceptance_criteria": {
            "claim_evidence_binding_ratio_min": 1.0,
            "primary_claim_direct_visual_ratio_min": 1.0,
            "claim_visual_relevance_min": 80,
            "subject_visibility_ratio_min": 0.95,
            "critical_region_visibility_ratio_min": 1.0,
            "module_order_match_ratio_min": 1.0,
            "model_scene_count_min": 1,
            "model_scene_count_max": 2,
        },
        "measurement_anchors": [
            {
                "id": "A",
                "label": "총 길이",
                "value": 25,
                "unit": "cm",
                "start": "제품 상단 중앙",
                "end": "제품 하단 중앙",
                "verification": "actual_sample_required",
            },
            {
                "id": "B",
                "label": "코 부분 높이",
                "value": 13.7,
                "unit": "cm",
                "start": "공급처 측정 시작점",
                "end": "공급처 측정 끝점",
                "verification": "anchor_definition_pending",
            },
        ],
        "modules": [
            {
                "id": "M01",
                "order": 1,
                "role": "hero",
                "commercial_job": "핵심 상품과 사용 맥락을 1초 안에 전달",
                "claim_ids": ["CLAIM-COVER"],
                "evidence_ids": ["FACT-A"],
                "asset_ids": ["ASSET-MODEL"],
                "claim_visual_role": "direct",
                "visual_thesis": "실제 사람 크기 맥락에서 얼굴과 목 커버 범위를 보여준다",
                "required_visual_cues": ["눈 아래 상단선", "목 하단 끝선", "입·코 타공 위치"],
                "model_policy": "synthetic_adult",
                "layout": {"mobile": "overlay", "wide": "overlay"},
                "asset_frames": [
                    {
                        "asset_id": "ASSET-MODEL",
                        "subject_bbox": {"x": 0.18, "y": 0.08, "width": 0.64, "height": 0.86},
                        "critical_regions": [
                            {"id": "face-cover", "x": 0.28, "y": 0.24, "width": 0.44, "height": 0.48}
                        ],
                        "subject_visibility_ratio_min": 0.95,
                        "critical_region_visibility_ratio_min": 1.0,
                    }
                ],
                "qa": {"claim_visual_relevance_min": 80, "review_method": "human_visual"},
                "imagegen_prompt": prompt(),
            },
            {
                "id": "M02",
                "order": 2,
                "role": "coverage_measurement",
                "commercial_job": "커버 범위를 감이 아닌 수치로 확인",
                "claim_ids": ["CLAIM-SIZE"],
                "evidence_ids": ["FACT-A", "FACT-B"],
                "asset_ids": ["ASSET-MEASURE"],
                "claim_visual_role": "direct",
                "visual_thesis": "제품 전체와 A·B 기준점이 한 프레임 안에 보인다",
                "required_visual_cues": ["제품 상단", "제품 하단", "A 기준점", "B 기준점"],
                "measurement_ids": ["A", "B"],
                "model_policy": "none",
                "layout": {"mobile": "copy_then_media", "wide": "media_right"},
                "asset_frames": [
                    {
                        "asset_id": "ASSET-MEASURE",
                        "subject_bbox": {"x": 0.08, "y": 0.05, "width": 0.84, "height": 0.9},
                        "critical_regions": [
                            {"id": "top-anchor", "x": 0.46, "y": 0.05, "width": 0.08, "height": 0.08},
                            {"id": "bottom-anchor", "x": 0.42, "y": 0.86, "width": 0.16, "height": 0.08},
                        ],
                        "subject_visibility_ratio_min": 0.95,
                        "critical_region_visibility_ratio_min": 1.0,
                    }
                ],
                "qa": {"claim_visual_relevance_min": 80, "review_method": "human_visual"},
                "imagegen_prompt": prompt(),
            },
        ],
    }


def good_metrics() -> dict[str, object]:
    modules = [
        {
            "id": "M01",
            "dom_order": 1,
            "claim_ids": ["CLAIM-COVER"],
            "copy_rect": {"left": 24, "top": 100, "right": 336, "bottom": 300},
            "media_rect": {"left": 0, "top": 0, "right": 360, "bottom": 780},
            "assets": [
                {
                    "id": "ASSET-MODEL",
                    "natural_width": 1000,
                    "natural_height": 1500,
                    "render_width": 360,
                    "render_height": 780,
                    "object_fit": "cover",
                    "source_visible_rect": {"x": 0.1538, "y": 0, "width": 0.6924, "height": 1},
                }
            ],
        },
        {
            "id": "M02",
            "dom_order": 2,
            "claim_ids": ["CLAIM-SIZE"],
            "copy_rect": {"left": 24, "top": 800, "right": 336, "bottom": 980},
            "media_rect": {"left": 24, "top": 1000, "right": 336, "bottom": 1450},
            "assets": [
                {
                    "id": "ASSET-MEASURE",
                    "natural_width": 1000,
                    "natural_height": 1500,
                    "render_width": 312,
                    "render_height": 450,
                    "object_fit": "contain",
                    "source_visible_rect": {"x": 0, "y": 0, "width": 1, "height": 1},
                }
            ],
        },
    ]
    wide_modules = json.loads(json.dumps(modules, ensure_ascii=False))
    wide_modules[1]["copy_rect"] = {"left": 40, "top": 800, "right": 360, "bottom": 1080}
    wide_modules[1]["media_rect"] = {"left": 420, "top": 800, "right": 760, "bottom": 1310}
    return {
        "schema_version": "1.0",
        "page": "detail-page.html",
        "viewports": [
            {"width": 360, "height": 900, "modules": modules},
            {"width": 800, "height": 1000, "modules": wide_modules},
        ],
    }


def test_visual_storyboard_reference_has_no_extra_blank_line_at_eof() -> None:
    reference = (
        ROOT
        / "coupang-detail-page-generator"
        / "references"
        / "visual-storyboard-and-ac.md"
    )

    assert not reference.read_text(encoding="utf-8-sig").endswith("\n\n")


def test_storyboard_contract_passes_with_numeric_ac_and_imagegen_brief(tmp_path: Path) -> None:
    storyboard = tmp_path / "storyboard.json"
    report = tmp_path / "report.json"
    write_json(storyboard, good_storyboard())

    result = run_python(STORYBOARD_VALIDATOR, "--storyboard", storyboard, "--report", report, "--strict")

    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["metrics"]["claim_evidence_binding_ratio"] == 1.0
    assert payload["metrics"]["primary_claim_direct_visual_ratio"] == 1.0


def test_storyboard_blocks_missing_prompt_measurement_and_direct_claim_link(tmp_path: Path) -> None:
    payload = good_storyboard()
    payload["modules"][0]["imagegen_prompt"].pop("claim_link")
    payload["modules"][1]["measurement_ids"] = ["A"]
    payload["modules"][0]["claim_visual_role"] = "context"
    storyboard = tmp_path / "bad-storyboard.json"
    write_json(storyboard, payload)

    result = run_python(STORYBOARD_VALIDATOR, "--storyboard", storyboard, "--strict")

    assert result.returncode == 1
    assert "PROMPT_CONTRACT" in result.stderr
    assert "MISSING_MEASUREMENT" in result.stderr
    assert "PRIMARY_CLAIM_DIRECT_VISUAL" in result.stderr


def test_visual_layout_passes_exact_order_claim_binding_and_crop_visibility(tmp_path: Path) -> None:
    storyboard = tmp_path / "storyboard.json"
    metrics = tmp_path / "metrics.json"
    report = tmp_path / "layout-report.json"
    write_json(storyboard, good_storyboard())
    write_json(metrics, good_metrics())

    result = run_python(
        LAYOUT_VALIDATOR,
        "--storyboard",
        storyboard,
        "--metrics",
        metrics,
        "--report",
        report,
        "--strict",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["metrics"]["module_order_match_ratio"] == 1.0
    assert payload["metrics"]["claim_asset_binding_ratio"] == 1.0


def test_visual_layout_blocks_swapped_modules_wrong_claim_and_critical_crop(tmp_path: Path) -> None:
    storyboard = tmp_path / "storyboard.json"
    payload = good_metrics()
    mobile = payload["viewports"][0]
    mobile["modules"][0]["dom_order"] = 2
    mobile["modules"][1]["dom_order"] = 1
    mobile["modules"][0]["claim_ids"] = ["CLAIM-WRONG"]
    mobile["modules"][0]["assets"][0]["source_visible_rect"] = {
        "x": 0,
        "y": 0,
        "width": 0.45,
        "height": 0.45,
    }
    metrics = tmp_path / "bad-metrics.json"
    write_json(storyboard, good_storyboard())
    write_json(metrics, payload)

    result = run_python(LAYOUT_VALIDATOR, "--storyboard", storyboard, "--metrics", metrics, "--strict")

    assert result.returncode == 1
    assert "MODULE_ORDER_MISMATCH" in result.stderr
    assert "CLAIM_ASSET_MISMATCH" in result.stderr
    assert "CRITICAL_REGION_CROPPED" in result.stderr


def test_visual_layout_collector_exposes_repeatable_cdp_contract() -> None:
    probe_source = PROBE.read_text(encoding="utf-8")
    result = subprocess.run(
        ["node", str(COLLECTOR), "--help"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )

    assert 'schema_version: "1.0"' in probe_source
    assert "source_visible_rect" in probe_source
    assert "data-asset-id" in probe_source
    assert "data-claim-ids" in probe_source
    assert result.returncode == 0, result.stderr
    assert "--storyboard" in result.stdout
    assert "--viewports" in result.stdout
    assert "--screenshots" in result.stdout
