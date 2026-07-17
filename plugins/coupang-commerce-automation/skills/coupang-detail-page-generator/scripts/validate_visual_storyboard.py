#!/usr/bin/env python3
"""Validate a claim-led visual storyboard before any bitmap generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_AC = {
    "claim_evidence_binding_ratio_min",
    "primary_claim_direct_visual_ratio_min",
    "claim_visual_relevance_min",
    "subject_visibility_ratio_min",
    "critical_region_visibility_ratio_min",
    "module_order_match_ratio_min",
    "model_scene_count_min",
    "model_scene_count_max",
}
REQUIRED_MODULE_TEXT = {"id", "role", "commercial_job", "visual_thesis"}
REQUIRED_MODULE_LISTS = {"claim_ids", "evidence_ids", "asset_ids", "required_visual_cues", "asset_frames"}
REQUIRED_PROMPT = {
    "use_case",
    "asset_type",
    "primary_request",
    "subject",
    "composition",
    "claim_link",
    "measurement_guidance",
    "constraints",
    "avoid",
}
VISUAL_ROLES = {"direct", "supporting", "context"}
MODEL_POLICIES = {"none", "synthetic_adult"}


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="수치형 AC가 포함된 주장 중심 비주얼 스토리보드를 검증합니다.")
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("storyboard root must be an object")
    return payload


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def number(value: Any, low: float, high: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= float(value) <= high


def valid_box(box: Any) -> bool:
    if not isinstance(box, dict):
        return False
    values = [box.get(key) for key in ("x", "y", "width", "height")]
    if not all(number(value, 0, 1) for value in values):
        return False
    x, y, width, height = (float(value) for value in values)
    return width > 0 and height > 0 and x + width <= 1.000001 and y + height <= 1.000001


def validate(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def error(code: str, message: str, module_id: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if module_id:
            item["module_id"] = module_id
        errors.append(item)

    if payload.get("schema_version") != "1.0" or payload.get("artifact_type") != "visual_storyboard":
        error("SCHEMA", "schema_version 1.0과 artifact_type visual_storyboard가 필요합니다.")
    if payload.get("asset_scope") not in {"concept_only", "production"}:
        error("ASSET_SCOPE", "asset_scope는 concept_only 또는 production이어야 합니다.")

    ac = payload.get("acceptance_criteria")
    if not isinstance(ac, dict):
        error("AC_CONTRACT", "acceptance_criteria 객체가 필요합니다.")
        ac = {}
    missing_ac = sorted(REQUIRED_AC - set(ac))
    if missing_ac:
        error("AC_CONTRACT", f"필수 AC 누락: {', '.join(missing_ac)}")
    for field in (
        "claim_evidence_binding_ratio_min",
        "primary_claim_direct_visual_ratio_min",
        "subject_visibility_ratio_min",
        "critical_region_visibility_ratio_min",
        "module_order_match_ratio_min",
    ):
        if field in ac and not number(ac[field], 0, 1):
            error("AC_CONTRACT", f"{field}는 0~1 숫자여야 합니다.")
    if "claim_visual_relevance_min" in ac and not number(ac["claim_visual_relevance_min"], 0, 100):
        error("AC_CONTRACT", "claim_visual_relevance_min은 0~100 숫자여야 합니다.")

    required_measurements = {str(value) for value in payload.get("required_measurement_ids", [])}
    anchors = payload.get("measurement_anchors", [])
    anchor_ids: set[str] = set()
    if required_measurements and not isinstance(anchors, list):
        error("MEASUREMENT_CONTRACT", "measurement_anchors 배열이 필요합니다.")
        anchors = []
    for index, anchor in enumerate(anchors, start=1):
        if not isinstance(anchor, dict):
            error("MEASUREMENT_CONTRACT", f"measurement anchor #{index}가 객체가 아닙니다.")
            continue
        anchor_id = str(anchor.get("id", "")).strip()
        anchor_ids.add(anchor_id)
        for field in ("id", "label", "unit", "start", "end", "verification"):
            if not nonempty_text(anchor.get(field)):
                error("MEASUREMENT_CONTRACT", f"measurement {anchor_id or index}의 {field}가 필요합니다.")
        if not isinstance(anchor.get("value"), (int, float)):
            error("MEASUREMENT_CONTRACT", f"measurement {anchor_id or index}의 value는 숫자여야 합니다.")
    missing_anchor_ids = sorted(required_measurements - anchor_ids)
    if missing_anchor_ids:
        error("MISSING_MEASUREMENT", f"필수 치수 기준점 누락: {', '.join(missing_anchor_ids)}")

    modules = payload.get("modules")
    if not isinstance(modules, list) or not modules:
        error("MODULE_CONTRACT", "modules 배열이 필요합니다.")
        modules = []
    if isinstance(payload.get("module_count"), int) and payload.get("module_count") != len(modules):
        error("MODULE_COUNT", "module_count와 실제 modules 수가 다릅니다.")

    module_ids: list[str] = []
    orders: list[int] = []
    covered_measurements: set[str] = set()
    model_scenes = 0
    bound_modules = 0
    direct_claim_ids: set[str] = set()
    for index, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
            error("MODULE_CONTRACT", f"module #{index}가 객체가 아닙니다.")
            continue
        module_id = str(module.get("id", "")).strip() or f"#{index}"
        module_ids.append(module_id)
        order = module.get("order")
        if not isinstance(order, int) or order < 1:
            error("MODULE_ORDER", "order는 1 이상의 정수여야 합니다.", module_id)
        else:
            orders.append(order)
        for field in REQUIRED_MODULE_TEXT:
            if not nonempty_text(module.get(field)):
                error("MODULE_CONTRACT", f"{field}가 필요합니다.", module_id)
        for field in REQUIRED_MODULE_LISTS:
            if not nonempty_list(module.get(field)):
                error("MODULE_CONTRACT", f"{field}는 비어 있지 않은 배열이어야 합니다.", module_id)
        role = module.get("claim_visual_role")
        if role not in VISUAL_ROLES:
            error("CLAIM_VISUAL_ROLE", "claim_visual_role은 direct/supporting/context 중 하나여야 합니다.", module_id)
        if role == "direct":
            direct_claim_ids.update(str(value) for value in module.get("claim_ids", []))
        if nonempty_list(module.get("claim_ids")) and nonempty_list(module.get("evidence_ids")):
            bound_modules += 1
        model_policy = module.get("model_policy")
        if model_policy not in MODEL_POLICIES:
            error("MODEL_POLICY", "model_policy는 none 또는 synthetic_adult여야 합니다.", module_id)
        elif model_policy == "synthetic_adult":
            model_scenes += 1
        if payload.get("asset_scope") == "concept_only" and model_policy not in MODEL_POLICIES:
            error("CONCEPT_MODEL_POLICY", "concept_only 인물은 synthetic_adult만 허용합니다.", module_id)

        measurement_ids = {str(value) for value in module.get("measurement_ids", [])}
        covered_measurements.update(measurement_ids)
        prompt = module.get("imagegen_prompt")
        if prompt is not None:
            if not isinstance(prompt, dict):
                error("PROMPT_CONTRACT", "imagegen_prompt는 객체여야 합니다.", module_id)
            else:
                missing = sorted(REQUIRED_PROMPT - set(prompt))
                if missing:
                    error("PROMPT_CONTRACT", f"ImageGen 프롬프트 필드 누락: {', '.join(missing)}", module_id)
                for field in REQUIRED_PROMPT - {"constraints", "avoid"}:
                    if field in prompt and not nonempty_text(prompt.get(field)):
                        error("PROMPT_CONTRACT", f"ImageGen {field}가 비었습니다.", module_id)
                for field in ("constraints", "avoid"):
                    if field in prompt and not nonempty_list(prompt.get(field)):
                        error("PROMPT_CONTRACT", f"ImageGen {field}는 비어 있지 않은 배열이어야 합니다.", module_id)

        frames = module.get("asset_frames", [])
        for frame_index, frame in enumerate(frames, start=1):
            if not isinstance(frame, dict):
                error("FRAME_CONTRACT", f"asset frame #{frame_index}가 객체가 아닙니다.", module_id)
                continue
            if str(frame.get("asset_id", "")) not in {str(value) for value in module.get("asset_ids", [])}:
                error("FRAME_CONTRACT", "asset_frame의 asset_id가 module asset_ids에 없습니다.", module_id)
            if not valid_box(frame.get("subject_bbox")):
                error("FRAME_CONTRACT", "subject_bbox는 0~1 정규화 좌표여야 합니다.", module_id)
            critical = frame.get("critical_regions")
            if not isinstance(critical, list) or not critical:
                error("FRAME_CONTRACT", "critical_regions가 필요합니다.", module_id)
            else:
                for region in critical:
                    if not isinstance(region, dict) or not nonempty_text(region.get("id")) or not valid_box(region):
                        error("FRAME_CONTRACT", "critical region은 id와 유효한 정규화 좌표가 필요합니다.", module_id)
            for field in ("subject_visibility_ratio_min", "critical_region_visibility_ratio_min"):
                if not number(frame.get(field), 0, 1):
                    error("FRAME_CONTRACT", f"{field}는 0~1 숫자여야 합니다.", module_id)

        qa = module.get("qa")
        if not isinstance(qa, dict) or not number(qa.get("claim_visual_relevance_min"), 0, 100):
            error("QA_CONTRACT", "qa.claim_visual_relevance_min이 필요합니다.", module_id)
        elif qa.get("review_method") != "human_visual":
            error("QA_CONTRACT", "주장-이미지 연관성은 human_visual 검수를 포함해야 합니다.", module_id)

    if len(module_ids) != len(set(module_ids)):
        error("MODULE_ID_DUPLICATE", "module id는 중복될 수 없습니다.")
    if sorted(orders) != list(range(1, len(modules) + 1)):
        error("MODULE_ORDER", "module order는 1부터 연속이어야 합니다.")
    missing_measurements = sorted(required_measurements - covered_measurements)
    if missing_measurements:
        error("MISSING_MEASUREMENT", f"스토리보드 모듈에 연결되지 않은 치수: {', '.join(missing_measurements)}")

    primary_claims = {str(value) for value in payload.get("primary_claim_ids", [])}
    missing_direct = sorted(primary_claims - direct_claim_ids)
    if missing_direct:
        error("PRIMARY_CLAIM_DIRECT_VISUAL", f"직접 시각 증거가 없는 핵심 주장: {', '.join(missing_direct)}")

    total_modules = len(modules)
    metrics = {
        "modules": total_modules,
        "model_scenes": model_scenes,
        "claim_evidence_binding_ratio": round(bound_modules / total_modules, 4) if total_modules else 0,
        "primary_claim_direct_visual_ratio": round(
            len(primary_claims & direct_claim_ids) / len(primary_claims), 4
        ) if primary_claims else 1.0,
        "measurement_anchor_coverage_ratio": round(
            len(required_measurements & covered_measurements) / len(required_measurements), 4
        ) if required_measurements else 1.0,
    }
    if metrics["claim_evidence_binding_ratio"] < float(ac.get("claim_evidence_binding_ratio_min", 1)):
        error("CLAIM_EVIDENCE_BINDING", "주장-근거 연결 비율이 AC 미만입니다.")
    if metrics["primary_claim_direct_visual_ratio"] < float(ac.get("primary_claim_direct_visual_ratio_min", 1)):
        error("PRIMARY_CLAIM_DIRECT_VISUAL", "핵심 주장 직접 시각화 비율이 AC 미만입니다.")
    minimum_models = int(ac.get("model_scene_count_min", 0)) if isinstance(ac.get("model_scene_count_min"), int) else 0
    maximum_models = int(ac.get("model_scene_count_max", 2)) if isinstance(ac.get("model_scene_count_max"), int) else 2
    if not minimum_models <= model_scenes <= maximum_models:
        error("MODEL_SCENE_COUNT", f"모델 장면 수 {model_scenes}가 허용 범위 {minimum_models}~{maximum_models} 밖입니다.")
    return errors, warnings, metrics


def main() -> int:
    configure_utf8()
    args = parse_args()
    try:
        payload = load_json(args.storyboard.expanduser().resolve())
    except Exception as exc:
        sys.stderr.write(f"[SCHEMA] {exc}\n")
        return 2
    errors, warnings, metrics = validate(payload)
    report = {
        "schema_version": "1.0",
        "storyboard": str(args.storyboard),
        "status": "fail" if errors or (args.strict and warnings) else "pass",
        "metrics": metrics,
        "errors": errors,
        "warnings": warnings,
    }
    if args.report:
        path = args.report.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in errors:
        suffix = f" [{item['module_id']}]" if item.get("module_id") else ""
        sys.stderr.write(f"[{item['code']}]{suffix} {item['message']}\n")
    for item in warnings:
        sys.stderr.write(f"[WARNING:{item['code']}] {item['message']}\n")
    if report["status"] == "pass":
        sys.stdout.write(
            "visual-storyboard: pass | "
            f"modules={metrics['modules']} binding={metrics['claim_evidence_binding_ratio']:.2f} "
            f"direct={metrics['primary_claim_direct_visual_ratio']:.2f}\n"
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
