#!/usr/bin/env python3
"""Validate workflow gates for version 5 Coupang detail-page projects."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - dependency error is handled in main.
    yaml = None

LOGGER = logging.getLogger("validate_project_manifest")
GATES = ("evidence", "market", "brand", "planning", "ui_assets", "fidelity_pilot", "production", "final")
PAGE_IDS = [f"{index:02d}" for index in range(1, 11)]
ASSET_MODES = {
    "PRESERVE",
    "COMPOSITE",
    "EDIT_BACKGROUND_ONLY",
    "GENERATE_SUPPORT",
    "GENERATE_PRODUCT_ALLOWED",
    "REAL_PHOTO_REQUIRED",
    "GIF_REQUIRED",
}
WORKFLOW_VERSIONS = {"5.0", "5.1", "5.2", "5.3"}
V51_STYLE_PRIORITY = ["practical_evidence", "professional_function", "emotional_lifestyle"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a project manifest and the artifacts required at a workflow gate")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--gate", choices=GATES, default="final")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def load_yaml(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing project manifest: {path}")
        return {}
    if yaml is None:
        errors.append("PyYAML is required to validate project-manifest.yaml")
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"invalid YAML {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append("project manifest root must be a mapping")
        return {}
    return data


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing: {path}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"invalid JSON {path}: {exc}")
        return {}
    if not isinstance(data, dict):
        errors.append(f"JSON root must be an object: {path}")
        return {}
    return data


def nonempty(value: Any) -> bool:
    return bool(str(value).strip()) if value is not None else False


def nonempty_list(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, list) and len(value) >= minimum and all(nonempty(item) for item in value)


def markdown_has_data_row(path: Path, minimum_cells: int = 2) -> bool:
    if not path.is_file():
        return False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line.startswith("|") or re.fullmatch(r"\|?[\s:|\-]+\|?", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= minimum_cells and not any(token in cells[0].casefold() for token in ("fact id", "pain id", "컷 id", "gif id", "장")):
            if sum(bool(cell) for cell in cells) >= minimum_cells:
                return True
    return False


def require_file(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing: {path}")


def validate_base(manifest: dict[str, Any], errors: list[str]) -> None:
    version = str(manifest.get("workflow_version", ""))
    if version not in WORKFLOW_VERSIONS:
        errors.append("workflow_version must be 5.0, 5.1, 5.2, or 5.3")
    project = manifest.get("project", {})
    if not isinstance(project, dict):
        errors.append("project must be a mapping")
        return
    if project.get("platform") != "coupang-mobile-detail":
        errors.append("project.platform must be coupang-mobile-detail")
    if project.get("page_count") != 10:
        errors.append("project.page_count must be 10")
    canvas = project.get("canvas", {})
    if not isinstance(canvas, dict) or int(canvas.get("width", 0)) <= 0:
        errors.append("project.canvas.width must be a positive integer")
    if version in {"5.1", "5.2"} and isinstance(canvas, dict):
        expected = {
            "mode": "fixed",
            "width": 800,
            "height": 2400,
            "min_height": 2400,
            "max_height": 2400,
        }
        for field, value in expected.items():
            if canvas.get(field) != value:
                errors.append(f"workflow 5.1+ project.canvas.{field} must be {value!r}")
    if version == "5.3" and isinstance(canvas, dict):
        expected = {
            "mode": "responsive",
            "width": 800,
            "height": None,
            "min_width": 360,
            "max_width": 800,
        }
        for field, value in expected.items():
            if canvas.get(field) != value:
                errors.append(f"workflow 5.3 project.canvas.{field} must be {value!r}")
    if not isinstance(manifest.get("inputs"), dict):
        errors.append("inputs must be a mapping")
    if not isinstance(manifest.get("gates"), dict):
        errors.append("gates must be a mapping")
    if version == "5.2":
        qa = manifest.get("qa", {})
        if not isinstance(qa, dict):
            errors.append("workflow 5.2 qa must be a mapping")
        else:
            if qa.get("max_targeted_edits_per_page") != 2:
                errors.append("workflow 5.2 qa.max_targeted_edits_per_page must be 2")
            if qa.get("max_text_partial_edits_per_page") != 3:
                errors.append("workflow 5.2 qa.max_text_partial_edits_per_page must be 3")
            if qa.get("local_typography_fallback_allowed") is not False:
                errors.append("workflow 5.2 must forbid local typography fallback")
    if version == "5.3":
        planning = manifest.get("planning", {})
        expected_paths = {
            "product_plan_path": "output/planning/product-plan.json",
            "content_plan_path": "output/planning/content-plan.json",
            "product_approval_path": "output/approvals/product-plan-approval.json",
            "content_approval_path": "output/approvals/content-plan-approval.json",
            "approval_actor_type": "user",
        }
        if not isinstance(planning, dict):
            errors.append("workflow 5.3 planning must be a mapping")
        else:
            for field, expected in expected_paths.items():
                if planning.get(field) != expected:
                    errors.append(f"workflow 5.3 planning.{field} must be {expected}")
        design = manifest.get("design", {})
        if not isinstance(design, dict) or design.get("text_rendering") != "hybrid-html":
            errors.append("workflow 5.3 design.text_rendering must be hybrid-html")
        qa = manifest.get("qa", {})
        if not isinstance(qa, dict):
            errors.append("workflow 5.3 qa must be a mapping")
        else:
            if qa.get("material_qa_path") != "output/qa/material-qa.json":
                errors.append("workflow 5.3 qa.material_qa_path is invalid")
            if qa.get("integration_qa_path") != "output/qa/integration-qa.json":
                errors.append("workflow 5.3 qa.integration_qa_path is invalid")


def validate_evidence(output: Path, manifest: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    inputs = manifest.get("inputs", {})
    product = manifest.get("product", {})
    identity = manifest.get("product_identity", {})
    if not nonempty_list(inputs.get("product_truth_images")):
        errors.append("inputs.product_truth_images requires at least one path")
    product_sources = inputs.get("product_sources", [])
    if not isinstance(product_sources, list) or not product_sources:
        errors.append("inputs.product_sources requires at least one lineage record")
    for field in ("display_name", "category", "target_customer", "primary_problem"):
        if not nonempty(product.get(field)):
            errors.append(f"product.{field} is required by the evidence gate")
    ledger = output / "product-truth-ledger.md"
    require_file(ledger, errors)
    if ledger.is_file() and not markdown_has_data_row(ledger, 5):
        errors.append("product-truth-ledger.md has no completed fact row")
    facts = load_json(output / "product-facts.json", errors)
    verified = 0
    ad_allowed = {"CONFIRMED_USER", "CONFIRMED_SOURCE", "OBSERVED_IMAGE"}
    for value in facts.values():
        status = str(value.get("status", "")) if isinstance(value, dict) else ""
        if isinstance(value, dict) and (status in ad_allowed or status.startswith("verified_")) and nonempty(value.get("value")):
            verified += 1
    if verified < 3:
        errors.append("product-facts.json requires at least three verified facts")
    invariants = output / "product-invariants.txt"
    require_file(invariants, errors)
    if invariants.is_file():
        lines = [line for line in invariants.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        if len(lines) < 5:
            errors.append("product-invariants.txt requires at least five explicit rules")
        if all("원본" in line or "제품" in line for line in lines):
            warnings.append("product-invariants.txt may still be generic; add product-specific counts, positions, colors, and patterns")

    lineage = load_json(output / "product-source-lineage.json", errors)
    identity_status = str(lineage.get("identity_status", ""))
    concept_opt_in = lineage.get("concept_only_opt_in") is True and identity.get("concept_only_opt_in") is True
    if identity_status not in {"verified", "concept_only"}:
        errors.append("product-source-lineage.identity_status must be verified or concept_only")
    sources = lineage.get("sources", [])
    if not isinstance(sources, list):
        errors.append("product-source-lineage.sources must be an array")
        sources = []
    trusted_ids: set[str] = set()
    all_source_ids: set[str] = set()
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            errors.append(f"product source {index} must be an object")
            continue
        for field in ("source_id", "lineage_type", "path_or_url"):
            if not nonempty(source.get(field)):
                errors.append(f"product source {index} missing {field}")
        lineage_type = str(source.get("lineage_type", ""))
        all_source_ids.add(str(source.get("source_id", "")))
        if lineage_type not in {"raw_capture", "manufacturer_source", "generated_master", "generated_scene"}:
            errors.append(f"product source {index} has invalid lineage_type")
        if source.get("trusted_for_identity") is True:
            if lineage_type not in {"raw_capture", "manufacturer_source"}:
                errors.append(f"product source {index}: generated assets cannot be trusted for identity")
            else:
                trusted_ids.add(str(source.get("source_id", "")))
    if identity_status == "verified" and not trusted_ids:
        errors.append("verified product identity requires a trusted raw_capture or manufacturer_source")
    manifest_source_ids = {str(value) for value in product_sources}
    if not manifest_source_ids.issubset(all_source_ids):
        errors.append("inputs.product_sources must reference source_id values in product-source-lineage.json")
    if identity_status == "concept_only" and not concept_opt_in:
        errors.append("concept_only identity requires explicit concept_only_opt_in in manifest and lineage")
    if str(identity.get("status", "")) != identity_status:
        errors.append("manifest product_identity.status must match product-source-lineage.identity_status")
    verified_ids = {str(value) for value in identity.get("verified_source_ids", [])}
    if identity_status == "verified" and not verified_ids.issubset(trusted_ids):
        errors.append("product_identity.verified_source_ids must reference trusted actual sources")
    if identity_status == "verified" and identity.get("uncertain_details"):
        errors.append("verified product identity cannot retain uncertain_details")
    if str(manifest.get("workflow_version", "")) in {"5.2", "5.3"}:
        routing = load_json(output / "reference-routing.json", errors)
        canonical = routing.get("canonical_sources", [])
        minimum_canonical = 3 if identity_status == "verified" else 1
        if not isinstance(canonical, list) or not minimum_canonical <= len(canonical) <= 5 or not all(nonempty(value) for value in canonical):
            errors.append(f"workflow 5.2 reference-routing.canonical_sources requires {minimum_canonical}..5 source IDs")
            canonical = []
        canonical_ids = {str(value) for value in canonical}
        if identity_status == "verified" and not canonical_ids.issubset(trusted_ids):
            errors.append("canonical reference IDs must be trusted raw_capture/manufacturer_source records")
        if identity_status == "concept_only" and not canonical_ids.issubset(all_source_ids):
            errors.append("concept-only canonical reference IDs must exist in product-source-lineage.json")
        if routing.get("identity_status") != identity_status:
            errors.append("reference-routing.identity_status must match product identity")
        manifest_canonical = {str(value) for value in identity.get("canonical_reference_ids", [])}
        if manifest_canonical != canonical_ids:
            errors.append("manifest product_identity.canonical_reference_ids must match reference-routing.json")
        page_routes = routing.get("pages", {})
        if not isinstance(page_routes, dict) or sorted(page_routes) != PAGE_IDS:
            errors.append("reference-routing.pages must contain exactly 01..10")
        else:
            for page in PAGE_IDS:
                route = page_routes.get(page, {})
                selected_ids = route.get("source_ids", []) if isinstance(route, dict) else []
                if not isinstance(selected_ids, list) or not 1 <= len(selected_ids) <= 5:
                    errors.append(f"reference route {page} requires 1..5 source IDs")
                    continue
                if not {str(value) for value in selected_ids}.issubset(canonical_ids):
                    errors.append(f"reference route {page} may use only canonical source IDs")
                if not nonempty_list(route.get("required_views")) or not nonempty(route.get("rationale")):
                    errors.append(f"reference route {page} requires required_views and rationale")
                if route.get("missing_views"):
                    errors.append(f"reference route {page} still has missing_views")


def validate_market(output: Path, errors: list[str]) -> None:
    root = output / "browser-research"
    for name in ("source-product.json", "competitors.json", "appeal-map.json", "sources.md"):
        require_file(root / name, errors)
    pain = output / "competitor-pain-map.md"
    require_file(pain, errors)
    if pain.is_file() and not markdown_has_data_row(pain, 6):
        errors.append("competitor-pain-map.md has no completed pain row")
    principles = output / "planning-principles.md"
    require_file(principles, errors)
    if principles.is_file():
        text = principles.read_text(encoding="utf-8-sig")
        for heading in ("## 한 줄 기획 원리", "## 구매 판단 흐름", "## 승인 소구", "## 금지 전이", "## 정반합 결정"):
            if heading not in text:
                errors.append(f"planning-principles.md missing heading: {heading}")


def validate_brand(output: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    brand_dir = output / "brand"
    for name in ("brand-brief.md", "brand-guide.md", "brand-evidence-library.json"):
        require_file(brand_dir / name, errors)
    version = str(manifest.get("workflow_version", ""))
    if version in {"5.1", "5.2", "5.3"}:
        require_file(brand_dir / "brand-name-candidates.md", errors)
    system = load_json(brand_dir / "brand-system.json", errors)
    status = str(system.get("status", ""))
    if status not in {"working_draft", "established", "approved"}:
        errors.append("brand-system.status must be working_draft, established, or approved")
    for field in ("positioning", "promise"):
        if not nonempty(system.get(field)):
            errors.append(f"brand-system.{field} is required")
    for field in ("reasons_to_believe", "personality", "anti_personality"):
        if not nonempty_list(system.get(field), 3):
            errors.append(f"brand-system.{field} requires at least three entries")
    voice = system.get("voice", {})
    visual = system.get("visual", {})
    campaign = system.get("campaign_rules", {})
    for field in ("principles", "preferred_patterns", "forbidden_patterns"):
        if not nonempty_list(voice.get(field), 2):
            errors.append(f"brand-system.voice.{field} requires at least two entries")
    if not isinstance(visual.get("core_colors"), dict) or len(visual.get("core_colors", {})) < 3:
        errors.append("brand-system.visual.core_colors requires at least three role-based colors")
    for field in ("photography", "components", "memory_devices"):
        if not nonempty_list(visual.get(field), 1):
            errors.append(f"brand-system.visual.{field} is required")
    for field in ("constants", "variables"):
        if not nonempty_list(campaign.get(field), 2):
            errors.append(f"brand-system.campaign_rules.{field} requires at least two entries")
    if status == "working_draft":
        if system.get("name_usage_allowed") is not False or campaign.get("logo_policy") != "no_logo_until_approved":
            errors.append("working_draft brands must forbid name and logo usage")
    if system.get("name_usage_allowed") is True and not nonempty(system.get("name")):
        errors.append("brand-system.name is required when name_usage_allowed is true")
    manifest_brand = manifest.get("brand", {})
    if manifest_brand.get("name_usage_allowed") and not nonempty(manifest_brand.get("name")):
        errors.append("manifest allows brand-name usage but brand.name is empty")
    if version in {"5.1", "5.2", "5.3"}:
        naming = system.get("naming", {})
        if not isinstance(naming, dict):
            errors.append("brand-system.naming must be an object")
            naming = {}
        naming_status = str(naming.get("status", ""))
        selected_name = str(naming.get("selected_name", "")).strip()
        candidates = naming.get("candidates", [])
        if naming.get("required_per_product") is not True:
            errors.append("brand-system.naming.required_per_product must be true")
        if naming_status not in {"proposed", "approved", "established"}:
            errors.append("brand-system.naming.status must be proposed, approved, or established")
        if not selected_name:
            errors.append("every workflow 5.1+ product requires a selected brand-name proposal")
        if naming_status == "proposed" and not nonempty_list(candidates, 3):
            errors.append("proposed product branding requires at least three name candidates")
        if not nonempty(naming.get("rationale")):
            errors.append("brand-system.naming.rationale is required")
        if system.get("name") != selected_name:
            errors.append("brand-system.name must match naming.selected_name")
        if system.get("name_usage_allowed") is not naming.get("usage_allowed"):
            errors.append("brand-system name usage fields must agree")
        if naming_status == "proposed" and naming.get("usage_allowed") is not False:
            errors.append("proposed brand names cannot be rendered in final images")
        if system.get("style_priority") != V51_STYLE_PRIORITY:
            errors.append("brand-system.style_priority must be practical_evidence, professional_function, emotional_lifestyle")
        if not isinstance(manifest_brand, dict):
            errors.append("manifest.brand must be a mapping")
        else:
            if manifest_brand.get("name_status") != naming_status:
                errors.append("manifest brand.name_status must match brand-system naming.status")
            if str(manifest_brand.get("name", "")).strip() != selected_name:
                errors.append("manifest brand.name must match the selected product brand name")
            if manifest_brand.get("name_usage_allowed") is not naming.get("usage_allowed"):
                errors.append("manifest and brand-system name usage must agree")
            if manifest_brand.get("style_priority") != V51_STYLE_PRIORITY:
                errors.append("manifest brand.style_priority has the wrong order")

        candidates_path = brand_dir / "brand-name-candidates.md"
        if candidates_path.is_file():
            candidate_text = candidates_path.read_text(encoding="utf-8-sig")
            final_match = re.search(r"^-\s*최종 제안:\s*(.+?)\s*$", candidate_text, re.MULTILINE)
            if not final_match or final_match.group(1).strip() != selected_name:
                errors.append("brand-name-candidates.md final proposal must match brand-system.naming.selected_name")
            populated_rows = 0
            for raw in candidate_text.splitlines():
                if not raw.strip().startswith("|"):
                    continue
                cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
                if cells and cells[0] and cells[0] != "후보" and not re.fullmatch(r"[-:]+", cells[0]):
                    populated_rows += 1
            if naming_status == "proposed" and populated_rows < 3:
                errors.append("brand-name-candidates.md requires three completed candidate rows")


def validate_planning(output: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    for path in (output / "page-plan.md", output / "copy" / "overlay-copy.md"):
        require_file(path, errors)
    pages = manifest.get("pages", [])
    version = str(manifest.get("workflow_version", ""))
    canonical_ids = {str(value) for value in manifest.get("product_identity", {}).get("canonical_reference_ids", [])}
    if version == "5.3":
        try:
            from hybrid_contract import validate_planning as validate_hybrid_planning

            errors.extend(validate_hybrid_planning(output.parent, "content"))
        except Exception as exc:
            errors.append(f"workflow 5.3 planning validation failed to run: {exc}")
    if version == "5.2":
        approval_path = output / "strategy-approval.md"
        require_file(approval_path, errors)
        strategy = manifest.get("strategy", {})
        if not isinstance(strategy, dict) or strategy.get("approval_status") != "approved":
            errors.append("workflow 5.2 strategy.approval_status must be approved before generation")
        if strategy.get("approval_basis") not in {"user_approved", "recommended_proceed", "direct_full_generation"}:
            errors.append("workflow 5.2 strategy.approval_basis is invalid")
        if approval_path.is_file():
            text = approval_path.read_text(encoding="utf-8-sig")
            for heading in ("## 경쟁 리뷰 기반 구매 불안", "## 소구점 결정", "## 판매 정보와 보류 주장", "## 실촬영·구성 결정"):
                if heading not in text:
                    errors.append(f"strategy-approval.md missing heading: {heading}")
            if "- 승인 상태: `approved`" not in text:
                errors.append("strategy-approval.md approval status must be approved")
    if not isinstance(pages, list) or len(pages) != 10:
        errors.append("manifest.pages must contain exactly ten page records")
        return
    actual = [str(item.get("page", "")).zfill(2) for item in pages if isinstance(item, dict)]
    if actual != PAGE_IDS:
        errors.append("manifest.pages must be ordered 01..10")
    for index, item in enumerate(pages, start=1):
        if not isinstance(item, dict):
            errors.append(f"manifest page {index} must be a mapping")
            continue
        page = f"{index:02d}"
        for field in ("commercial_job", "purchase_reason", "proof_type", "evidence", "brand_role"):
            if not nonempty(item.get(field)):
                errors.append(f"page {page} missing {field}")
        if any(token in str(item.get("evidence", "")).casefold() for token in ("required", "pending", "필요")):
            errors.append(f"page {page} evidence is still a placeholder")
        if version == "5.2":
            for field in ("buyer_question", "scene", "required_product_view", "forbidden_elements", "qa_criteria"):
                if not nonempty(item.get(field)):
                    errors.append(f"page {page} missing {field}")
            if not nonempty_list(item.get("evidence_ledger_ids")):
                errors.append(f"page {page} requires evidence_ledger_ids")
            reference_ids = item.get("reference_source_ids", [])
            if not nonempty_list(reference_ids) or not {str(value) for value in reference_ids}.issubset(canonical_ids):
                errors.append(f"page {page} reference_source_ids must use canonical sources")
            if not isinstance(item.get("real_photo_required"), bool):
                errors.append(f"page {page} real_photo_required must be boolean")
    copy_path = output / "copy" / "overlay-copy.md"
    if copy_path.is_file() and version != "5.3":
        sections: dict[str, dict[str, str]] = {}
        current = ""
        for raw in copy_path.read_text(encoding="utf-8-sig").splitlines():
            heading = re.fullmatch(r"##\s+(\d{1,2})\s*", raw.strip())
            if heading:
                current = f"{int(heading.group(1)):02d}"
                sections[current] = {}
                continue
            field = re.fullmatch(r"-\s+([a-zA-Z0-9_]+):\s*(.*)", raw.strip())
            if current and field:
                sections[current][field.group(1)] = field.group(2).strip()
        if sorted(sections) != PAGE_IDS:
            errors.append("overlay-copy.md must contain sections 01..10")
        for page in PAGE_IDS:
            fields = sections.get(page, {})
            if fields.get("copy_status") != "approved":
                errors.append(f"page {page} copy_status must be approved")
            for field in ("commercial_job", "brand_role", "claim_id", "headline", "emphasis", "proof_type", "proof_frame", "evidence"):
                if not nonempty(fields.get(field)):
                    errors.append(f"page {page} copy missing {field}")


def validate_ui_assets(output: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    ui = output / "ui-guide.md"
    require_file(ui, errors)
    if ui.is_file():
        text = ui.read_text(encoding="utf-8-sig")
        for heading in ("## 브랜드 연결", "## UI 토큰", "## 타이포그래피", "## 정렬 축", "## 컴포넌트", "## 페이지 반복과 변주"):
            if heading not in text:
                errors.append(f"ui-guide.md missing heading: {heading}")
        token_values: dict[str, str] = {}
        for raw in text.splitlines():
            if not raw.strip().startswith("|"):
                continue
            cells = [cell.strip().strip("`") for cell in raw.strip().strip("|").split("|")]
            if len(cells) >= 2 and (cells[0].startswith("color.") or cells[0] in {"radius.card", "shadow.product"}):
                token_values[cells[0]] = cells[1]
        for token in ("color.bg", "color.text", "color.brand", "color.category", "radius.card", "shadow.product"):
            if not nonempty(token_values.get(token)):
                errors.append(f"ui-guide.md token needs a value: {token}")
    strategy = output / "asset-strategy.md"
    require_file(strategy, errors)
    if strategy.is_file():
        text = strategy.read_text(encoding="utf-8-sig")
        pages_with_mode = set()
        for raw in text.splitlines():
            for mode in ASSET_MODES:
                if mode in raw:
                    match = re.match(r"\|\s*(\d{1,2})\s*\|", raw.strip())
                    if match:
                        pages_with_mode.add(f"{int(match.group(1)):02d}")
        if pages_with_mode != set(PAGE_IDS):
            missing = sorted(set(PAGE_IDS) - pages_with_mode)
            errors.append("asset-strategy.md needs an asset mode for every page; missing: " + ", ".join(missing))
    pages = manifest.get("pages", [])
    if isinstance(pages, list):
        for index, item in enumerate(pages, start=1):
            if isinstance(item, dict) and item.get("asset_strategy") not in ASSET_MODES:
                errors.append(f"page {index:02d} manifest asset_strategy must be a valid mode")


def validate_production(output: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    if str(manifest.get("workflow_version", "")) == "5.3":
        try:
            from hybrid_contract import validate_materials

            material_errors, _, _, _ = validate_materials(output.parent)
            errors.extend(material_errors)
        except Exception as exc:
            errors.append(f"workflow 5.3 material QA validation failed to run: {exc}")
        for path in (output / "html" / "detail-page.html", output / "html" / "styles.css", output / "html" / "package-manifest.json"):
            require_file(path, errors)
        return
    for page in PAGE_IDS:
        require_file(output / "generated-pages" / f"PG-{page}.png", errors)
        require_file(output / "typography-pages" / f"TY-{page}.png", errors)
        require_file(output / "images" / f"{page}.png", errors)
    require_file(output / "generated-pages" / "manifest.json", errors)
    require_file(output / "typography-pages" / "manifest.json", errors)


def validate_fidelity_pilot(output: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    path = output / "fidelity-pilot.md"
    require_file(path, errors)
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8-sig")
    identity_status = str(manifest.get("product_identity", {}).get("status", ""))
    expected = "PASS" if identity_status == "verified" else "CONCEPT_ONLY" if identity_status == "concept_only" else ""
    if not expected or f"- 판정: `{expected}`" not in text:
        errors.append(f"fidelity-pilot.md verdict must be {expected or 'PASS/CONCEPT_ONLY'}")
    rows = [line for line in text.splitlines() if line.strip().startswith("|") and "PASS/FIX/BLOCKED" not in line and not set(line.replace("|", "").replace(":", "").strip()) <= {"-"}]
    if sum(1 for row in rows if "| PASS |" in row) < 9 and identity_status == "verified":
        errors.append("verified fidelity pilot requires PASS for all nine identity checks")


def has_plan_or_exclusion(path: Path, exclusion_label: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8-sig")
    return markdown_has_data_row(path, 4) or exclusion_label in text


def validate_final(output: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    photo = output / "photo-shot-list.md"
    gif = output / "gif-plan.md"
    require_file(photo, errors)
    require_file(gif, errors)
    if photo.is_file() and not has_plan_or_exclusion(photo, "실사진 제외 사유"):
        errors.append("photo-shot-list.md needs mapped shots or an explicit 실사진 제외 사유")
    if gif.is_file() and not has_plan_or_exclusion(gif, "GIF 제외 사유"):
        errors.append("gif-plan.md needs mapped GIFs or an explicit GIF 제외 사유")
    version = str(manifest.get("workflow_version", ""))
    if version == "5.3":
        try:
            from validate_hybrid_package import validate_package

            package_errors, package_warnings = validate_package(output.parent, strict=True)
            errors.extend(package_errors)
            errors.extend(f"strict hybrid QA warning: {item}" for item in package_warnings)
        except Exception as exc:
            errors.append(f"workflow 5.3 hybrid package validation failed to run: {exc}")
        gates = manifest.get("gates", {})
        expected = (
            "evidence",
            "market",
            "brand",
            "product_planning",
            "content_planning",
            "ui_assets",
            "fidelity_pilot",
            "material_qa",
            "assembly",
            "integration_qa",
            "final_qa",
        )
        for gate in expected:
            if gates.get(gate) != "pass":
                errors.append(f"manifest gate must be pass before completion: {gate}")
        return
    for name in ("qa-report.md", "contact-sheet.jpg"):
        require_file(output / name, errors)
    if version == "5.2":
        for name in ("image-inspection.json", "ocr-expectations.json", "ocr-report.json", "regeneration-log.json"):
            require_file(output / name, errors)
        regeneration = load_json(output / "regeneration-log.json", errors)
        if regeneration:
            if regeneration.get("max_targeted_edits_per_page") != 2:
                errors.append("regeneration-log max_targeted_edits_per_page must be 2")
            if regeneration.get("max_text_partial_edits_per_page") != 3:
                errors.append("regeneration-log max_text_partial_edits_per_page must be 3")
            if regeneration.get("local_typography_fallback_allowed") is not False:
                errors.append("regeneration-log must forbid local typography fallback")
            page_logs = regeneration.get("pages", {})
            if not isinstance(page_logs, dict) or sorted(page_logs) != PAGE_IDS:
                errors.append("regeneration-log.pages must contain exactly 01..10")
            else:
                for page in PAGE_IDS:
                    attempts = page_logs.get(page, [])
                    if not isinstance(attempts, list):
                        errors.append(f"regeneration-log page {page} must be an array")
                        continue
                    text_attempts = [item for item in attempts if isinstance(item, dict) and item.get("edit_type") == "text_partial_edit"]
                    other_attempts = [item for item in attempts if isinstance(item, dict) and item.get("edit_type") in {"product_targeted_edit", "layout_targeted_edit"}]
                    if len(text_attempts) > 3:
                        errors.append(f"regeneration-log page {page} exceeds three text partial edits")
                    if len(other_attempts) > 2:
                        errors.append(f"regeneration-log page {page} exceeds two product/layout targeted edits")
                    if any(isinstance(item, dict) and item.get("edit_type") == "local_typography_fallback" for item in attempts):
                        errors.append(f"regeneration-log page {page} uses forbidden local typography fallback")
                    for index, item in enumerate(attempts, start=1):
                        if not isinstance(item, dict):
                            errors.append(f"regeneration-log page {page} attempt {index} must be an object")
                            continue
                        if item.get("edit_type") not in {"text_partial_edit", "product_targeted_edit", "layout_targeted_edit"}:
                            errors.append(f"regeneration-log page {page} attempt {index} has invalid edit_type")
                        for field in ("target_area", "attempt_number", "result"):
                            if not nonempty(item.get(field)):
                                errors.append(f"regeneration-log page {page} attempt {index} missing {field}")
                    if len(text_attempts) == 3 and text_attempts[-1].get("result") != "pass":
                        errors.append(f"regeneration-log page {page} exhausted text edits and must remain BLOCKED_TEXT")
        ocr = load_json(output / "ocr-report.json", errors)
        if ocr and ocr.get("overall_status") == "fail":
            errors.append("ocr-report has unresolved text mismatches")
        qa_path = output / "qa-report.md"
        if qa_path.is_file():
            qa_text = qa_path.read_text(encoding="utf-8-sig")
            page_passes: set[str] = set()
            for raw in qa_text.splitlines():
                match = re.match(r"\|\s*(\d{1,2})\s*\|", raw.strip())
                if match and raw.count("PASS") >= 4:
                    page_passes.add(f"{int(match.group(1)):02d}")
            if page_passes != set(PAGE_IDS):
                errors.append("qa-report.md requires four PASS gate results for every page 01..10")
    gates = manifest.get("gates", {})
    expected = ("evidence", "market", "brand", "planning", "ui_assets", "fidelity_pilot", "production", "final_qa")
    for gate in expected:
        if gates.get(gate) != "pass":
            errors.append(f"manifest gate must be pass before completion: {gate}")
    decisions = manifest.get("decisions", [])
    if not isinstance(decisions, list) or len(decisions) < 4:
        errors.append("manifest.decisions requires at least four thesis/antithesis/synthesis records")
    else:
        for index, decision in enumerate(decisions, start=1):
            if not isinstance(decision, dict):
                errors.append(f"decision {index} must be a mapping")
                continue
            for field in ("stage", "thesis", "antithesis", "synthesis", "proof", "rollback"):
                if not nonempty(decision.get(field)):
                    errors.append(f"decision {index} missing {field}")
    lineage = load_json(output / "product-source-lineage.json", errors)
    generated = lineage.get("generated_assets", []) if lineage else []
    if not isinstance(generated, list) or len(generated) < 10:
        errors.append("product-source-lineage.generated_assets requires at least ten final page lineage records")
    else:
        asset_ids = set()
        concept_only = lineage.get("identity_status") == "concept_only"
        for index, asset in enumerate(generated, start=1):
            if not isinstance(asset, dict):
                errors.append(f"generated lineage asset {index} must be an object")
                continue
            asset_id = str(asset.get("asset_id", ""))
            asset_ids.add(asset_id)
            if not asset_id or not isinstance(asset.get("source_ids"), list):
                errors.append(f"generated lineage asset {index} requires asset_id and source_ids")
            expected_check = "concept_only" if concept_only else "pass"
            if asset.get("identity_check") != expected_check:
                errors.append(f"generated lineage asset {index} identity_check must be {expected_check}")
        if not set(PAGE_IDS).issubset({value[-2:] for value in asset_ids if value}):
            errors.append("generated lineage assets must cover final pages 01..10")
    if lineage.get("identity_status") == "concept_only":
        qa_path = output / "qa-report.md"
        if qa_path.is_file() and "연출용 콘셉트 이미지" not in qa_path.read_text(encoding="utf-8-sig"):
            errors.append("concept-only projects must label the QA report as 연출용 콘셉트 이미지")


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    output = project / "output"
    manifest_path = (args.manifest or output / "project-manifest.yaml").expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    manifest = load_yaml(manifest_path, errors)
    if manifest:
        validate_base(manifest, errors)

    ordered = list(GATES)
    upto = ordered.index(args.gate)
    selected = set(ordered[: upto + 1])
    if "evidence" in selected:
        validate_evidence(output, manifest, errors, warnings)
    if "market" in selected:
        validate_market(output, errors)
    if "brand" in selected:
        validate_brand(output, manifest, errors)
    if "planning" in selected:
        validate_planning(output, manifest, errors)
    if "ui_assets" in selected:
        validate_ui_assets(output, manifest, errors)
    if "fidelity_pilot" in selected:
        validate_fidelity_pilot(output, manifest, errors)
    if "production" in selected:
        validate_production(output, manifest, errors)
    if "final" in selected:
        validate_final(output, manifest, errors)

    for item in errors:
        LOGGER.error(item)
    for item in warnings:
        LOGGER.warning(item)
    if errors or (args.strict and warnings):
        LOGGER.error("project gate validation failed: gate=%s errors=%d warnings=%d", args.gate, len(errors), len(warnings))
        return 1
    LOGGER.info("project gate validation passed: gate=%s workflow_version=%s", args.gate, manifest.get("workflow_version", "unknown"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
