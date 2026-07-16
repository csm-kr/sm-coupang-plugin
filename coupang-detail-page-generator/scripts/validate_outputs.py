#!/usr/bin/env python3
"""Validate exactly ten rendered pages and synthetic-person provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

from validate_campaign_assets import EXPECTED_IDS, EXPECTED_PAGES, PERSON_PAGES, validate_campaign

LOGGER = logging.getLogger("validate_outputs")
REQUIRED = [
    "rapid-improvement-brief.md",
    "product-invariants.txt",
    "style-crops/manifest.json",
    "page-plan.md",
    "copy/overlay-copy.md",
    "imagegen-queue.json",
    "generated-pages/manifest.json",
    "layout-spec.json",
    "render-manifest.json",
    "qa-report.md",
]
V5_REQUIRED = [
    "project-manifest.yaml",
    "product-truth-ledger.md",
    "product-source-lineage.json",
    "competitor-pain-map.md",
    "brand/brand-brief.md",
    "brand/brand-system.json",
    "brand/brand-guide.md",
    "brand/brand-evidence-library.json",
    "ui-guide.md",
    "asset-strategy.md",
    "fidelity-pilot.md",
    "photo-shot-list.md",
    "gif-plan.md",
]
V51_REQUIRED = [
    "README.md",
    "brand/brand-name-candidates.md",
]
V52_REQUIRED = [
    "strategy-approval.md",
    "reference-routing.json",
    "image-inspection.json",
    "ocr-expectations.json",
    "ocr-report.json",
    "regeneration-log.json",
]
EXPECTED_ROLES = [
    "hero",
    "product_overview",
    "problem_context",
    "construction",
    "key_detail",
    "material_detail",
    "daily_use",
    "lifestyle_mosaic",
    "product_information",
    "closing",
]
FORBIDDEN_SOURCE_KINDS = {"raw", "preserve_edit", "campaign_generate", "support_generate"}
EXPECTED_COMMERCIAL_JOBS = [
    "hook",
    "solution_overview",
    "problem_or_criterion",
    "proof_1",
    "proof_2",
    "proof_3",
    "use_or_demonstration",
    "friction_reducer",
    "purchase_information",
    "recap",
]
V5_ASSET_MODES = {
    "PRESERVE",
    "COMPOSITE",
    "EDIT_BACKGROUND_ONLY",
    "GENERATE_SUPPORT",
    "GENERATE_PRODUCT_ALLOWED",
    "REAL_PHOTO_REQUIRED",
    "GIF_REQUIRED",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ten final detail-page images")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--page", help="01..10")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--min-height", type=int)
    parser.add_argument("--max-height", type=int)
    parser.add_argument("--no-qa-update", action="store_true")
    return parser.parse_args()


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_overlay_copy(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current = ""
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        heading = re.fullmatch(r"##\s+(\d{1,2})\s*", raw.strip())
        if heading:
            current = f"{int(heading.group(1)):02d}"
            sections[current] = {}
            continue
        field = re.fullmatch(r"-\s+([a-zA-Z0-9_]+):\s*(.*)", raw.strip())
        if current and field:
            sections[current][field.group(1)] = field.group(2).strip()
    return sections


def commercial_score(path: Path) -> int | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig")
    labels = (
        "첫 화면 훅과 상품 인지",
        "페이지별 구매 이유 차별성",
        "주장과 시각 증거의 연결",
        "타이포 위계와 대비",
        "전환 흐름과 구매정보 마감",
    )
    scores: list[int] = []
    for label in labels:
        match = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*([0-2])\s*\|", text, re.MULTILINE)
        if not match:
            return None
        scores.append(int(match.group(1)))
    if 0 in scores:
        return -(100 + sum(scores))
    return sum(scores)


def brand_score(path: Path) -> int | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig")
    labels = (
        "포지셔닝과 고객 불안 연결",
        "브랜드 약속과 제품 증거 연결",
        "브랜드 목소리 일관성",
        "색·폰트·사진·컴포넌트 시스템",
        "카테고리 친숙성과 기억 장치",
    )
    scores: list[int] = []
    for label in labels:
        match = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*([0-2])\s*\|", text, re.MULTILINE)
        if not match:
            return None
        scores.append(int(match.group(1)))
    if 0 in scores:
        return -(100 + sum(scores))
    return sum(scores)


def update_qa(path: Path, errors: list[str], warnings: list[str], pages: list[str], metrics: dict[str, Any]) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8-sig")
    start, end = "<!-- machine-validation:start -->", "<!-- machine-validation:end -->"
    lines = [
        start,
        "## Machine validation",
        "",
        f"- 검사 시각(UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- 검사 페이지: {', '.join(pages)}",
        f"- 승인 생성 페이지: {metrics.get('approved_pages', 0)}",
        f"- 합성 인물 페이지: {metrics.get('synthetic_person_pages', 0)}",
        f"- 실제 인물 픽셀 위반: {metrics.get('real_person_pixel_violations', 0)}",
        f"- 상업성 점수: {metrics.get('commercial_score', '미입력')}",
        f"- 브랜드 점수: {metrics.get('brand_score', '해당 없음')}",
        f"- 제품 동일성: {metrics.get('identity_status', '레거시 미추적')}",
        f"- 오류: {len(errors)}",
        f"- 경고: {len(warnings)}",
        "",
        "### 오류",
        "",
    ]
    lines.extend(f"- {item}" for item in errors or ["없음"])
    lines.extend(["", "### 경고", ""])
    lines.extend(f"- {item}" for item in warnings or ["없음"])
    lines.extend(["", end])
    block = "\n".join(lines)
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    text = pattern.sub(block, text) if pattern.search(text) else text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    if args.page and (not args.page.isdigit() or not 1 <= int(args.page) <= 10):
        LOGGER.error("--page must be 01..10")
        return 2
    pages = [f"{int(args.page):02d}"] if args.page else EXPECTED_PAGES
    project = args.project.expanduser().resolve()
    output = project / "output"
    workflow_v5 = (output / "project-manifest.yaml").is_file()
    errors: list[str] = []
    warnings: list[str] = []
    workflow_version = "legacy"
    expected_width = args.width or 780
    expected_height = args.height
    minimum_height = args.min_height or 1100
    maximum_height = args.max_height or 1800
    if workflow_v5:
        if yaml is None:
            errors.append("PyYAML is required to validate version-5 output dimensions")
        else:
            try:
                project_manifest = yaml.safe_load((output / "project-manifest.yaml").read_text(encoding="utf-8-sig")) or {}
                workflow_version = str(project_manifest.get("workflow_version", "5.0"))
                canvas = project_manifest.get("project", {}).get("canvas", {})
                expected_width = args.width or int(canvas.get("width", 780))
                expected_height = args.height if args.height is not None else (
                    int(canvas["height"]) if canvas.get("height") is not None else None
                )
                minimum_height = args.min_height or int(canvas.get("min_height", 1100))
                maximum_height = args.max_height or int(canvas.get("max_height", 1800))
            except Exception as exc:
                errors.append(f"project canvas parse failed: {exc}")
    if workflow_version == "5.3":
        if args.page:
            errors.append("workflow 5.3 validates the assembled HTML package as a whole; --page is not supported")
        try:
            from validate_hybrid_package import validate_package

            hybrid_errors, hybrid_warnings = validate_package(project, strict=args.strict)
            errors.extend(hybrid_errors)
            warnings.extend(hybrid_warnings)
        except Exception as exc:
            errors.append(f"workflow 5.3 hybrid validation failed to run: {exc}")
        for item in errors:
            LOGGER.error(item)
        for item in warnings:
            LOGGER.warning(item)
        if errors or (args.strict and warnings):
            LOGGER.error("hybrid output validation failed: errors=%d warnings=%d", len(errors), len(warnings))
            return 1
        LOGGER.info("hybrid output validation passed")
        return 0
    typography_mode = (output / "typography-pages" / "manifest.json").is_file()
    required = [item for item in REQUIRED if not typography_mode or item not in {"layout-spec.json", "render-manifest.json"}]
    if workflow_v5:
        required.extend(V5_REQUIRED)
    if workflow_version in {"5.1", "5.2"}:
        required.extend(V51_REQUIRED)
    if workflow_version == "5.2":
        required.extend(V52_REQUIRED)
    if typography_mode:
        required.extend(["typography-queue.json", "typography-pages/manifest.json"])
    for relative in required:
        if not (output / relative).is_file():
            errors.append(f"required file missing: {relative}")

    overlay_path = output / "copy" / "overlay-copy.md"
    if overlay_path.is_file():
        try:
            sections = parse_overlay_copy(overlay_path)
            if sorted(sections) != EXPECTED_PAGES:
                errors.append("overlay copy must contain exactly sections 01..10")
            jobs = []
            alignments = []
            for page in EXPECTED_PAGES:
                fields = sections.get(page, {})
                headline = fields.get("headline", "")
                emphasis = fields.get("emphasis", "")
                job = fields.get("commercial_job", "")
                alignment = fields.get("headline_alignment", "")
                jobs.append(job)
                alignments.append(alignment)
                if fields.get("copy_status", "approved").startswith("draft"):
                    warnings.append(f"{page}: copy_status is still draft_requires_fact_rewrite")
                if not headline or not fields.get("subcopy"):
                    errors.append(f"{page}: headline and subcopy are required")
                if not emphasis or headline.count(emphasis) != 1:
                    errors.append(f"{page}: emphasis must appear exactly once in headline")
                if alignment not in {"left", "center"}:
                    errors.append(f"{page}: headline_alignment must be left or center")
                if not fields.get("proof_type") or not fields.get("evidence"):
                    errors.append(f"{page}: proof_type and evidence are required")
                if workflow_v5:
                    for field in ("brand_role", "claim_id", "proof_frame"):
                        if not fields.get(field):
                            errors.append(f"{page}: version-5 copy requires {field}")
                    if fields.get("asset_mode") not in V5_ASSET_MODES:
                        errors.append(f"{page}: version-5 asset_mode must be a valid asset strategy mode")
            if jobs != EXPECTED_COMMERCIAL_JOBS:
                errors.append("overlay copy commercial_job sequence does not match the conversion flow")
            if len(set(alignments)) < 2:
                errors.append("headline alignment must vary between center and left across ten pages")
        except Exception as exc:
            errors.append(f"overlay-copy parse failed: {exc}")

    if typography_mode:
        try:
            from validate_typography_pass import validate_typography

            typography_errors, typography_warnings, _ = validate_typography(
                project,
                strict=args.strict,
                expected_width=expected_width,
                expected_height=expected_height,
            )
            errors.extend(f"typography pages: {item}" for item in typography_errors)
            warnings.extend(f"typography pages: {item}" for item in typography_warnings)
        except Exception as exc:
            errors.append(f"typography validation failed to run: {exc}")

    campaign_errors, campaign_warnings, campaign_metrics = validate_campaign(project, queue_only=False)
    errors.extend(f"generated pages: {item}" for item in campaign_errors)
    warnings.extend(f"generated pages: {item}" for item in campaign_warnings)

    try:
        from PIL import Image
    except ImportError:
        Image = None
        errors.append("Pillow missing")
    hashes: dict[str, list[str]] = {}
    for page in pages:
        path = output / "images" / f"{page}.png"
        if not path.is_file():
            errors.append(f"{page}: final image missing")
            continue
        if Image:
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    width, height = image.size
                size_ok = width == expected_width and (
                    height == expected_height
                    if expected_height is not None
                    else minimum_height <= height <= maximum_height
                )
                if not size_ok:
                    errors.append(f"{page}: invalid size {width}x{height}")
            except Exception as exc:
                errors.append(f"{page}: image read failed: {exc}")
        hashes.setdefault(digest(path), []).append(page)
    for values in hashes.values():
        if len(values) > 1:
            errors.append("duplicate final page pixels: " + ", ".join(values))

    spec_path = output / "layout-spec.json"
    if spec_path.is_file() and not typography_mode:
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
            spec_pages = spec.get("pages", [])
            actual_pages = [str(item.get("page", "")).zfill(2) for item in spec_pages]
            roles = [str(item.get("role", "")) for item in spec_pages]
            if actual_pages != EXPECTED_PAGES:
                errors.append("layout pages must be 01..10 in order")
            if roles != EXPECTED_ROLES:
                errors.append("layout roles do not match the ten-page structure")
            for index, item in enumerate(spec_pages, start=1):
                page = f"{index:02d}"
                expected_asset = f"PG-{page}"
                generated = []
                for element in item.get("elements", []):
                    if element.get("type") != "image":
                        continue
                    kind = str(element.get("source_kind", "unknown"))
                    if kind in FORBIDDEN_SOURCE_KINDS:
                        errors.append(f"{page}: forbidden legacy source_kind {kind}")
                    if kind == "generated_page":
                        generated.append(str(element.get("asset_id", "")))
                    if kind == "raw_product_only" and not str(element.get("path", "")).replace("\\", "/").startswith("raw/"):
                        errors.append(f"{page}: raw_product_only path must come from raw/")
                if expected_asset not in generated:
                    errors.append(f"{page}: matching generated page asset {expected_asset} is missing")
        except Exception as exc:
            errors.append(f"layout-spec parse failed: {exc}")

    render_path = output / "render-manifest.json"
    if render_path.is_file() and not typography_mode:
        try:
            manifest = json.loads(render_path.read_text(encoding="utf-8-sig"))
            entries = {str(item.get("page", "")).zfill(2): item for item in manifest.get("pages", [])}
            for page in pages:
                item = entries.get(page)
                if not item:
                    errors.append(f"{page}: render manifest entry missing")
                    continue
                if float(item.get("content_span_ratio", 0)) < 0.70:
                    errors.append(f"{page}: content span below 70%")
                if int(item.get("first_content_y", 9999)) > 140:
                    errors.append(f"{page}: first content starts after 140px")
                ratio = float(item.get("visual_area_ratio", 0))
                if not 0.55 <= ratio <= 0.85:
                    errors.append(f"{page}: visual area ratio {ratio:.0%} outside 55..85%")
        except Exception as exc:
            errors.append(f"render manifest parse failed: {exc}")

    if args.strict and not args.page and not (output / "contact-sheet.jpg").is_file():
        errors.append("contact-sheet.jpg missing")
    if campaign_metrics.get("approved_pages") != 10:
        errors.append("exactly ten generated pages must be approved")
    if campaign_metrics.get("synthetic_person_pages") != len(PERSON_PAGES):
        errors.append(f"all {len(PERSON_PAGES)} synthetic-person pages must pass synthetic-person QA")
    if campaign_metrics.get("real_person_pixel_violations") != 0:
        errors.append("real person pixel violations must be zero")

    score = commercial_score(output / "qa-report.md")
    if score is None:
        warnings.append("commercial scorecard is incomplete; enter five scores from 0 to 2")
        campaign_metrics["commercial_score"] = "미입력"
    elif score < 0:
        errors.append("commercial scorecard contains a zero-point category")
        campaign_metrics["commercial_score"] = abs(score) - 100
    elif score < 8:
        errors.append(f"commercial score {score}/10 is below the 8/10 pass threshold")
        campaign_metrics["commercial_score"] = score
    else:
        campaign_metrics["commercial_score"] = score

    if workflow_v5:
        bscore = brand_score(output / "qa-report.md")
        if bscore is None:
            errors.append("brand scorecard is incomplete; enter five scores from 0 to 2")
            campaign_metrics["brand_score"] = "미입력"
        elif bscore < 0:
            errors.append("brand scorecard contains a zero-point category")
            campaign_metrics["brand_score"] = abs(bscore) - 100
        elif bscore < 8:
            errors.append(f"brand score {bscore}/10 is below the 8/10 pass threshold")
            campaign_metrics["brand_score"] = bscore
        else:
            campaign_metrics["brand_score"] = bscore
        lineage_path = output / "product-source-lineage.json"
        if lineage_path.is_file():
            try:
                lineage = json.loads(lineage_path.read_text(encoding="utf-8-sig"))
                campaign_metrics["identity_status"] = lineage.get("identity_status", "미확인")
            except Exception as exc:
                errors.append(f"product-source-lineage parse failed: {exc}")
    else:
        campaign_metrics["brand_score"] = "레거시"

    if not args.no_qa_update:
        try:
            update_qa(output / "qa-report.md", errors, warnings, pages, campaign_metrics)
        except Exception as exc:
            warnings.append(f"QA machine block update failed: {exc}")
    for item in errors:
        LOGGER.error(item)
    for item in warnings:
        LOGGER.warning(item)
    if errors or (args.strict and warnings):
        LOGGER.error("output validation failed: errors=%d warnings=%d", len(errors), len(warnings))
        return 1
    LOGGER.info("output validation passed: pages=%s", ", ".join(pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
