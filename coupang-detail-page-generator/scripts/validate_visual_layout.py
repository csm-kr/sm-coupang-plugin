#!/usr/bin/env python3
"""Validate DOM order, claim bindings, layout direction, and image crop visibility."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def configure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="실제 브라우저 좌표로 모듈 순서·이미지 크롭·주장 연결을 검증합니다.")
    parser.add_argument("--storyboard", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--required-viewports", nargs="+", type=int, default=[360, 800])
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def area(box: dict[str, Any]) -> float:
    return max(0.0, float(box.get("width", 0))) * max(0.0, float(box.get("height", 0)))


def visibility_ratio(target: dict[str, Any], visible: dict[str, Any]) -> float:
    target_right = float(target["x"]) + float(target["width"])
    target_bottom = float(target["y"]) + float(target["height"])
    visible_right = float(visible["x"]) + float(visible["width"])
    visible_bottom = float(visible["y"]) + float(visible["height"])
    width = max(0.0, min(target_right, visible_right) - max(float(target["x"]), float(visible["x"])))
    height = max(0.0, min(target_bottom, visible_bottom) - max(float(target["y"]), float(visible["y"])))
    target_area = area(target)
    return width * height / target_area if target_area else 0.0


def overlaps(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return not (
        float(first.get("right", 0)) <= float(second.get("left", 0))
        or float(second.get("right", 0)) <= float(first.get("left", 0))
        or float(first.get("bottom", 0)) <= float(second.get("top", 0))
        or float(second.get("bottom", 0)) <= float(first.get("top", 0))
    )


def layout_matches(rule: str, copy_rect: dict[str, Any], media_rect: dict[str, Any]) -> bool:
    tolerance = 8
    if rule == "overlay":
        return overlaps(copy_rect, media_rect)
    if rule == "copy_then_media" or rule == "media_below":
        return float(media_rect.get("top", 0)) + tolerance >= float(copy_rect.get("bottom", 0))
    if rule == "media_right":
        return float(media_rect.get("left", 0)) + tolerance >= float(copy_rect.get("right", 0))
    if rule == "media_left":
        return float(media_rect.get("right", 0)) <= float(copy_rect.get("left", 0)) + tolerance
    if rule == "media_above":
        return float(media_rect.get("bottom", 0)) <= float(copy_rect.get("top", 0)) + tolerance
    if rule in {"stack", "full"}:
        return True
    return False


def validate(
    storyboard: dict[str, Any], metrics: dict[str, Any], required_viewports: list[int]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def error(code: str, message: str, viewport: int | None = None, module_id: str | None = None) -> None:
        item: dict[str, Any] = {"code": code, "message": message}
        if viewport is not None:
            item["viewport"] = viewport
        if module_id:
            item["module_id"] = module_id
        errors.append(item)

    if metrics.get("schema_version") != "1.0":
        error("SCHEMA", "visual layout metrics schema_version은 1.0이어야 합니다.")
    planned_modules = sorted(storyboard.get("modules", []), key=lambda item: int(item.get("order", 0)))
    expected_ids = [str(item.get("id", "")) for item in planned_modules]
    planned_map = {str(item.get("id", "")): item for item in planned_modules}
    viewports = metrics.get("viewports") if isinstance(metrics.get("viewports"), list) else []
    viewport_map = {int(item.get("width", 0)): item for item in viewports if isinstance(item, dict)}
    for width in required_viewports:
        if width not in viewport_map:
            error("MISSING_VIEWPORT", f"필수 viewport {width}px 결과가 없습니다.", width)

    module_checks = 0
    module_matches = 0
    binding_checks = 0
    binding_matches = 0
    crop_checks = 0
    crop_matches = 0
    for width, viewport in viewport_map.items():
        if width not in required_viewports:
            continue
        actual_modules = viewport.get("modules") if isinstance(viewport.get("modules"), list) else []
        sorted_actual = sorted(actual_modules, key=lambda item: int(item.get("dom_order", 0)))
        actual_ids = [str(item.get("id", "")) for item in sorted_actual]
        module_checks += len(expected_ids)
        module_matches += sum(1 for expected, actual in zip(expected_ids, actual_ids) if expected == actual)
        if actual_ids != expected_ids:
            error(
                "MODULE_ORDER_MISMATCH",
                f"예정 순서 {expected_ids}와 DOM 순서 {actual_ids}가 다릅니다.",
                width,
            )
        actual_map = {str(item.get("id", "")): item for item in actual_modules if isinstance(item, dict)}
        for module_id in expected_ids:
            planned = planned_map[module_id]
            actual = actual_map.get(module_id)
            if not actual:
                error("MISSING_MODULE", "브라우저 결과에 모듈이 없습니다.", width, module_id)
                continue
            expected_claims = {str(value) for value in planned.get("claim_ids", [])}
            actual_claims = {str(value) for value in actual.get("claim_ids", [])}
            expected_assets = {str(value) for value in planned.get("asset_ids", [])}
            actual_assets = {
                str(item.get("id", "")) for item in actual.get("assets", []) if isinstance(item, dict)
            }
            binding_checks += 1
            if expected_claims == actual_claims and expected_assets == actual_assets:
                binding_matches += 1
            else:
                error(
                    "CLAIM_ASSET_MISMATCH",
                    f"claim/assets 예정값 {sorted(expected_claims)}/{sorted(expected_assets)}와 "
                    f"렌더값 {sorted(actual_claims)}/{sorted(actual_assets)}가 다릅니다.",
                    width,
                    module_id,
                )

            layout = planned.get("layout", {}) if isinstance(planned.get("layout"), dict) else {}
            rule = str(layout.get("mobile" if width <= 620 else "wide", ""))
            copy_rect = actual.get("copy_rect")
            media_rect = actual.get("media_rect")
            if rule and isinstance(copy_rect, dict) and isinstance(media_rect, dict):
                if not layout_matches(rule, copy_rect, media_rect):
                    error("LAYOUT_ORDER_MISMATCH", f"렌더 위치가 {rule} 규칙과 다릅니다.", width, module_id)

            asset_map = {
                str(item.get("id", "")): item for item in actual.get("assets", []) if isinstance(item, dict)
            }
            for frame in planned.get("asset_frames", []):
                if not isinstance(frame, dict):
                    continue
                asset_id = str(frame.get("asset_id", ""))
                rendered = asset_map.get(asset_id)
                if not rendered:
                    continue
                visible = rendered.get("source_visible_rect")
                if not isinstance(visible, dict):
                    error("MISSING_VISIBLE_RECT", "source_visible_rect가 없습니다.", width, module_id)
                    continue
                crop_checks += 1
                subject_ratio = visibility_ratio(frame["subject_bbox"], visible)
                subject_min = float(frame.get("subject_visibility_ratio_min", 0.95))
                crop_pass = True
                if subject_ratio + 1e-6 < subject_min:
                    crop_pass = False
                    error(
                        "SUBJECT_CROPPED",
                        f"{asset_id} 피사체 가시율 {subject_ratio:.3f} < {subject_min:.3f}",
                        width,
                        module_id,
                    )
                critical_min = float(frame.get("critical_region_visibility_ratio_min", 1))
                for region in frame.get("critical_regions", []):
                    region_ratio = visibility_ratio(region, visible)
                    if region_ratio + 1e-6 < critical_min:
                        crop_pass = False
                        error(
                            "CRITICAL_REGION_CROPPED",
                            f"{asset_id}/{region.get('id')} 가시율 {region_ratio:.3f} < {critical_min:.3f}",
                            width,
                            module_id,
                        )
                if crop_pass:
                    crop_matches += 1

    ac = storyboard.get("acceptance_criteria", {}) if isinstance(storyboard.get("acceptance_criteria"), dict) else {}
    summary = {
        "viewports": len([width for width in required_viewports if width in viewport_map]),
        "module_order_match_ratio": round(module_matches / module_checks, 4) if module_checks else 0,
        "claim_asset_binding_ratio": round(binding_matches / binding_checks, 4) if binding_checks else 0,
        "critical_crop_pass_ratio": round(crop_matches / crop_checks, 4) if crop_checks else 0,
        "crop_checks": crop_checks,
    }
    if summary["module_order_match_ratio"] < float(ac.get("module_order_match_ratio_min", 1)):
        error("MODULE_ORDER_RATIO", "모듈 순서 일치율이 AC 미만입니다.")
    if summary["claim_asset_binding_ratio"] < float(ac.get("claim_evidence_binding_ratio_min", 1)):
        error("CLAIM_ASSET_BINDING_RATIO", "주장-자산 연결 일치율이 AC 미만입니다.")
    if crop_checks and summary["critical_crop_pass_ratio"] < 1:
        error("CROP_PASS_RATIO", "피사체·핵심 부위 크롭 통과율이 100% 미만입니다.")
    return errors, warnings, summary


def main() -> int:
    configure_utf8()
    args = parse_args()
    try:
        storyboard = load(args.storyboard.expanduser().resolve())
        metrics = load(args.metrics.expanduser().resolve())
    except Exception as exc:
        sys.stderr.write(f"[SCHEMA] {exc}\n")
        return 2
    errors, warnings, summary = validate(storyboard, metrics, args.required_viewports)
    status = "fail" if errors or (args.strict and warnings) else "pass"
    report = {
        "schema_version": "1.0",
        "status": status,
        "storyboard": str(args.storyboard),
        "source_metrics": str(args.metrics),
        "metrics": summary,
        "errors": errors,
        "warnings": warnings,
    }
    if args.report:
        path = args.report.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in errors:
        context = "".join(
            part for part in (
                f" [{item['viewport']}px]" if item.get("viewport") else "",
                f" [{item['module_id']}]" if item.get("module_id") else "",
            )
        )
        sys.stderr.write(f"[{item['code']}]{context} {item['message']}\n")
    if status == "pass":
        sys.stdout.write(
            "visual-layout: pass | "
            f"order={summary['module_order_match_ratio']:.2f} "
            f"binding={summary['claim_asset_binding_ratio']:.2f} "
            f"crop={summary['critical_crop_pass_ratio']:.2f}\n"
        )
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
