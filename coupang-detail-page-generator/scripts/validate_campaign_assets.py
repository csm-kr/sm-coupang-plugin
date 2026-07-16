#!/usr/bin/env python3
"""Validate a ten-page ImageGen batch and its synthetic-person provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("validate_campaign_assets")
EXPECTED_IDS = [f"PG-{index:02d}" for index in range(1, 11)]
EXPECTED_PAGES = [f"{index:02d}" for index in range(1, 11)]
PERSON_PAGES = {"01", "07"}
FUNCTION_EVIDENCE_KINDS = {"contact", "structure", "deformation", "portability", "use_sequence", "use_context", "specification"}
FIDELITY_FIELDS = {"silhouette", "count", "color", "openings", "seams", "label", "material"}
FIDELITY_FIELDS_V5 = FIDELITY_FIELDS | {"toe", "straps", "fasteners", "cut_mold_lines", "sole", "engravings", "assembly"}
FORBIDDEN_INPUT_ROLES = {"identity_seed", "edit_target", "real_wearer", "wearing_target", "real_model"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ten generated pages and synthetic-person safety")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--queue-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve(project: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (project / path).resolve()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"top-level JSON must be an object: {path}")
    return data


def validate_campaign(project: Path, queue_only: bool = False) -> tuple[list[str], list[str], dict[str, Any]]:
    project = project.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {
        "approved_pages": 0,
        "unique_pages": 0,
        "synthetic_person_pages": 0,
        "real_person_pixel_violations": 0,
    }
    queue_path = project / "output" / "imagegen-queue.json"
    if not queue_path.is_file():
        return ["imagegen-queue.json missing"], warnings, metrics
    try:
        queue = load_json(queue_path)
    except Exception as exc:
        return [f"imagegen-queue.json parse failed: {exc}"], warnings, metrics

    if str(queue.get("version")) != "4.0":
        errors.append("queue version must be 4.0")
    if queue.get("output_count") != 10:
        errors.append("output_count must be exactly 10")
    if queue.get("human_origin_policy") != "synthetic_only":
        errors.append("human_origin_policy must be synthetic_only")
    if queue.get("real_person_pixels_allowed") is not False:
        errors.append("real_person_pixels_allowed must be false")
    if int(queue.get("function_evidence_minimum", 0)) < 5:
        errors.append("function_evidence_minimum must be at least 5")
    if int(queue.get("face_visible_full_body_limit", 99)) > 2:
        errors.append("face_visible_full_body_limit must be 2 or less")
    if queue.get("synthetic_model_anchor") != "PG-01":
        errors.append("PG-01 must be the synthetic model anchor")
    workflow_version = str(queue.get("workflow_version", "legacy"))
    workflow_v5 = workflow_version in {"5.0", "5.1", "5.2", "5.3"}
    identity_status = str(queue.get("identity_status", "legacy_untracked"))
    if workflow_v5:
        if identity_status == "verified":
            if queue.get("product_source_policy") != "trusted_person_free_actual_sources_only":
                errors.append("version-5 verified queues must use trusted actual product sources only")
            if queue.get("actual_product_source_confirmed") is not True or queue.get("concept_only_confirmed") is not False:
                errors.append("version-5 verified queues require actual-product confirmation only")
        elif identity_status == "concept_only":
            if queue.get("product_source_policy") != "person_free_concept_sources_not_actual_evidence":
                errors.append("concept-only queues must declare that inputs are not actual product evidence")
            if queue.get("concept_only_confirmed") is not True or queue.get("actual_product_source_confirmed") is not False:
                errors.append("concept-only queues require explicit concept confirmation only")
        else:
            errors.append("version-5 queue identity_status must be verified or concept_only")
        if queue.get("product_lineage_path") != "output/product-source-lineage.json":
            errors.append("version-5 queue must reference product-source-lineage.json")
        brand_value = str(queue.get("brand_system_path", ""))
        brand_path = resolve(project, brand_value) if brand_value else project / "__missing_brand_system__"
        if brand_value != "output/brand/brand-system.json" or not brand_path.is_file():
            errors.append("version-5 queue must reference an existing output/brand/brand-system.json")
        elif str(queue.get("brand_system_sha256", "")).casefold() != digest(brand_path):
            errors.append("version-5 queue brand_system_sha256 is missing or stale")
        if workflow_version in {"5.1", "5.2"}:
            canvas = queue.get("target_canvas", {})
            if not isinstance(canvas, dict) or canvas.get("width") != 800 or canvas.get("height") != 2400:
                errors.append("workflow 5.1+ queue target_canvas must be exactly 800x2400")
            if not str(queue.get("brand_name", "")).strip():
                errors.append("workflow 5.1+ queue requires the selected product brand-name proposal")
            if queue.get("brand_name_status") not in {"proposed", "approved", "established"}:
                errors.append("workflow 5.1+ queue brand_name_status is invalid")
        if workflow_version == "5.3":
            canvas = queue.get("target_canvas", {})
            expected_canvas = {
                "mode": "responsive",
                "width": 800,
                "height": None,
                "min_width": 360,
                "max_width": 800,
            }
            if not isinstance(canvas, dict) or any(canvas.get(field) != value for field, value in expected_canvas.items()):
                errors.append("workflow 5.3 queue target_canvas must be responsive 360..800px")
            if not str(queue.get("brand_name", "")).strip():
                errors.append("workflow 5.3 queue requires the selected product brand-name proposal")
            if queue.get("brand_name_status") not in {"proposed", "approved", "established"}:
                errors.append("workflow 5.3 queue brand_name_status is invalid")
        if workflow_version in {"5.2", "5.3"}:
            canonical_ids = queue.get("canonical_source_ids", [])
            minimum_canonical = 3 if identity_status == "verified" else 1
            if not isinstance(canonical_ids, list) or not minimum_canonical <= len(canonical_ids) <= 5 or len(set(canonical_ids)) != len(canonical_ids):
                errors.append(f"workflow 5.2 queue requires {minimum_canonical}..5 unique canonical source IDs")
            if queue.get("reference_routing_path") != "output/reference-routing.json":
                errors.append("workflow 5.2 queue must reference output/reference-routing.json")
    elif queue.get("product_source_policy") != "verified_person_free_only; sources containing any person pixels are excluded from ImageGen and final composites":
        errors.append("legacy product_source_policy must require verified person-free inputs only")

    jobs = queue.get("jobs")
    if not isinstance(jobs, list):
        return errors + ["jobs must be an array"], warnings, metrics
    ids = [str(item.get("id", "")) for item in jobs if isinstance(item, dict)]
    pages = [str(item.get("page", "")).zfill(2) for item in jobs if isinstance(item, dict)]
    if ids != EXPECTED_IDS:
        errors.append("queue IDs must be PG-01..PG-10 in order")
    if pages != EXPECTED_PAGES:
        errors.append("queue pages must be 01..10 in order")
    if len(jobs) != 10:
        errors.append("queue must contain exactly ten jobs")
    if len(set(ids)) != len(ids):
        errors.append("queue job IDs are duplicated")

    invariants = str(queue.get("product_invariants", "")).strip()
    if len([line for line in invariants.splitlines() if line.strip()]) < 5:
        errors.append("product_invariants must contain at least five explicit lines")
    output_paths: list[str] = []
    job_map: dict[str, dict[str, Any]] = {}
    function_evidence_count = 0
    full_body_count = 0
    for index, item in enumerate(jobs, start=1):
        if not isinstance(item, dict):
            errors.append(f"queue job #{index} is not an object")
            continue
        job_id = str(item.get("id", f"#{index}"))
        page = str(item.get("page", "")).zfill(2)
        job_map[job_id] = item
        if item.get("mode") != "generate_from_references":
            errors.append(f"{job_id}: preserve/edit modes are forbidden")
        if item.get("real_person_pixels_allowed") is not False:
            errors.append(f"{job_id}: real person pixels must be forbidden")
        if item.get("source_person_usage") != "excluded_from_all_inputs":
            errors.append(f"{job_id}: sources containing people must be excluded from all inputs")
        expected_person = page in PERSON_PAGES
        if bool(item.get("contains_person")) != expected_person:
            errors.append(f"{job_id}: contains_person does not match the page role")
        if str(item.get("evidence_kind", "")) in FUNCTION_EVIDENCE_KINDS:
            function_evidence_count += 1
        if bool(item.get("face_visible_full_body")):
            full_body_count += 1
        if item.get("person_origin") != ("synthetic" if expected_person else "none"):
            errors.append(f"{job_id}: invalid person_origin")
        dependencies = item.get("depends_on", [])
        if expected_person and job_id != "PG-01" and dependencies != ["PG-01"]:
            errors.append(f"{job_id}: synthetic person page must depend only on PG-01")
        if (not expected_person or job_id == "PG-01") and dependencies:
            errors.append(f"{job_id}: unexpected dependency")

        prompt = str(item.get("prompt", ""))
        lowered = prompt.casefold()
        for token in (
            "newly synthesized pixels",
            "do not edit, preserve, trace, composite, or reproduce any real person",
            "generate no korean or english text",
            "watermarks",
        ):
            if token not in lowered:
                errors.append(f"{job_id}: required safety prompt is missing: {token}")
        if workflow_v5:
            if "brand system lock" not in lowered:
                errors.append(f"{job_id}: brand system lock is missing")
            if queue.get("brand_name_usage_allowed") is not True and "do not invent or display a brand name" not in lowered:
                errors.append(f"{job_id}: unapproved brand-name/logo guard is missing")
        if invariants and invariants not in prompt:
            errors.append(f"{job_id}: exact product invariant block is not repeated")

        inputs = item.get("input_images")
        if not isinstance(inputs, list):
            errors.append(f"{job_id}: input_images must be an array")
            inputs = []
        roles = [str(value.get("role", "")) for value in inputs if isinstance(value, dict)]
        forbidden = sorted(FORBIDDEN_INPUT_ROLES & set(roles))
        if forbidden:
            errors.append(f"{job_id}: forbidden real-person input roles: {', '.join(forbidden)}")
        if expected_person and job_id != "PG-01" and "synthetic_model_anchor" not in roles:
            errors.append(f"{job_id}: PG-01 synthetic anchor input missing")
        if not expected_person and "synthetic_model_anchor" in roles:
            errors.append(f"{job_id}: people-free page must not use a model anchor")
        style_roles = [role for role in roles if role.startswith("style_")]
        if len(style_roles) != 1:
            errors.append(f"{job_id}: exactly one style crop is required")
        if not any(role.startswith("product_evidence_") for role in roles):
            errors.append(f"{job_id}: at least one product evidence image is required")
        if workflow_version in {"5.2", "5.3"}:
            selected_ids = item.get("reference_source_ids", [])
            canonical_ids = queue.get("canonical_source_ids", [])
            product_source_ids = [str(value.get("source_id", "")) for value in inputs if isinstance(value, dict) and str(value.get("role", "")).startswith("product_evidence_")]
            if not isinstance(selected_ids, list) or not 1 <= len(selected_ids) <= 5:
                errors.append(f"{job_id}: reference_source_ids requires 1..5 values")
            elif any(str(value) not in canonical_ids for value in selected_ids):
                errors.append(f"{job_id}: reference_source_ids must use canonical sources")
            if [str(value) for value in selected_ids] != product_source_ids:
                errors.append(f"{job_id}: product inputs must exactly match the page reference route")
            if not item.get("required_product_views"):
                errors.append(f"{job_id}: required_product_views is missing")
        for value in inputs:
            if not isinstance(value, dict) or not value.get("path"):
                errors.append(f"{job_id}: invalid input image entry")
                continue
            role = str(value.get("role", ""))
            if role == "synthetic_model_anchor":
                continue
            path = resolve(project, str(value["path"]))
            if not path.is_file():
                errors.append(f"{job_id}: input image missing: {value['path']}")
            if role.startswith("product_evidence_"):
                usage = str(value.get("usage", ""))
                if "person-free" not in usage:
                    errors.append(f"{job_id}: person-free source guard is missing")
                if workflow_v5:
                    lineage_type = str(value.get("lineage_type", ""))
                    if not str(value.get("source_id", "")).strip():
                        errors.append(f"{job_id}: product evidence source_id is missing")
                    if identity_status == "verified" and lineage_type not in {"raw_capture", "manufacturer_source"}:
                        errors.append(f"{job_id}: generated product sources cannot establish verified identity")
                    if identity_status == "concept_only" and "not actual product structure evidence" not in usage:
                        errors.append(f"{job_id}: concept-only usage disclosure is missing")
        output_path = str(item.get("output_path", ""))
        output_paths.append(output_path)
        if output_path != f"output/generated-pages/{job_id}.png":
            errors.append(f"{job_id}: output_path must map directly to its page job")
    if len(output_paths) != len(set(output_paths)):
        errors.append("queue output paths are duplicated")
    if function_evidence_count < int(queue.get("function_evidence_minimum", 5)):
        errors.append("queue has fewer than five function-evidence pages")
    if full_body_count > int(queue.get("face_visible_full_body_limit", 2)):
        errors.append("queue exceeds the face-visible full-body model page limit")

    if queue_only:
        return errors, warnings, metrics

    manifest_path = project / "output" / "generated-pages" / "manifest.json"
    if not manifest_path.is_file():
        return errors + ["generated-pages/manifest.json missing"], warnings, metrics
    try:
        manifest = load_json(manifest_path)
    except Exception as exc:
        return errors + [f"generated page manifest parse failed: {exc}"], warnings, metrics
    if str(manifest.get("queue_sha256", "")).casefold() != digest(queue_path):
        errors.append("generated page manifest queue_sha256 is missing or stale")
    if manifest.get("human_origin_policy") != "synthetic_only":
        errors.append("generated page manifest human_origin_policy must be synthetic_only")
    if manifest.get("real_person_pixels_allowed") is not False:
        errors.append("generated page manifest must forbid real person pixels")
    assets = manifest.get("pages")
    if not isinstance(assets, list):
        return errors + ["generated page manifest pages must be an array"], warnings, metrics
    manifest_ids = [str(item.get("job_id", "")) for item in assets if isinstance(item, dict)]
    if manifest_ids != EXPECTED_IDS:
        errors.append("manifest must contain PG-01..PG-10 in queue order")

    file_hashes: dict[str, list[str]] = {}
    approved = 0
    synthetic_count = 0
    violations = 0
    for item in assets:
        if not isinstance(item, dict):
            errors.append("manifest contains a non-object page")
            continue
        job_id = str(item.get("job_id", ""))
        expected = job_map.get(job_id)
        if not expected:
            errors.append(f"unknown manifest job: {job_id}")
            continue
        status = str(item.get("status", ""))
        if status not in {"approved", "rejected", "pending"}:
            errors.append(f"{job_id}: invalid status")
        if status != "approved":
            errors.append(f"{job_id}: page is not approved")
            continue
        approved += 1
        if int(item.get("attempt", 0)) < 1:
            errors.append(f"{job_id}: attempt must be at least 1")
        if workflow_version in {"5.2", "5.3"} and int(item.get("targeted_edit_attempts", 0)) > 2:
            errors.append(f"{job_id}: targeted edit attempts exceed the limit of 2")
        if item.get("text_free") != "pass":
            errors.append(f"{job_id}: generated text/logo check failed or missing")
        if item.get("art_direction_match") != "pass":
            errors.append(f"{job_id}: art-direction check failed or missing")
        if item.get("commercial_structure") != "pass":
            errors.append(f"{job_id}: commercial page-role structure failed or missing")
        if workflow_v5:
            expected_identity_check = "concept_only" if identity_status == "concept_only" else "pass"
            if item.get("sku_identity") != expected_identity_check:
                errors.append(f"{job_id}: sku_identity must be {expected_identity_check}")
            if item.get("source_lineage") != "pass":
                errors.append(f"{job_id}: source_lineage must pass")
            if item.get("brand_consistency") != "pass":
                errors.append(f"{job_id}: brand_consistency must pass")
        if item.get("source_person_pixels") != "none":
            errors.append(f"{job_id}: real source-person pixels are present or unchecked")
            violations += 1
        page = str(expected.get("page", "")).zfill(2)
        if page in PERSON_PAGES:
            if item.get("synthetic_person_check") != "pass":
                errors.append(f"{job_id}: synthetic-person check failed or missing")
            else:
                synthetic_count += 1
        elif item.get("synthetic_person_check") not in {"not_applicable", "pass"}:
            errors.append(f"{job_id}: people-free page person check is invalid")
        fidelity = item.get("product_fidelity")
        required_fidelity = FIDELITY_FIELDS_V5 if workflow_v5 else FIDELITY_FIELDS
        if not isinstance(fidelity, dict) or not required_fidelity.issubset(fidelity):
            errors.append(f"{job_id}: product fidelity record is incomplete")
        else:
            for field in sorted(required_fidelity - {"label"}):
                if fidelity.get(field) != "pass":
                    errors.append(f"{job_id}: product fidelity failed or unchecked: {field}")
            if fidelity.get("label") not in {"pass", "not_visible", "product_only_raw_composite"}:
                errors.append(f"{job_id}: label fidelity is invalid")
        file_value = str(item.get("file", ""))
        path = resolve(project, file_value)
        if path != resolve(project, str(expected.get("output_path", ""))):
            errors.append(f"{job_id}: manifest file differs from queue output_path")
        if not path.is_file():
            errors.append(f"{job_id}: generated page file missing: {file_value}")
            continue
        actual_hash = digest(path)
        if str(item.get("sha256", "")).casefold() != actual_hash:
            errors.append(f"{job_id}: SHA-256 missing or mismatched")
        file_hashes.setdefault(actual_hash, []).append(job_id)
    for values in file_hashes.values():
        if len(values) > 1:
            errors.append("duplicate generated page pixels: " + ", ".join(values))
    metrics = {
        "approved_pages": approved,
        "unique_pages": len(file_hashes),
        "synthetic_person_pages": synthetic_count,
        "real_person_pixel_violations": violations,
    }
    return errors, warnings, metrics


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    errors, warnings, metrics = validate_campaign(args.project, args.queue_only)
    for item in errors:
        LOGGER.error(item)
    for item in warnings:
        LOGGER.warning(item)
    if errors or (args.strict and warnings):
        LOGGER.error("page batch validation failed: errors=%d warnings=%d", len(errors), len(warnings))
        return 1
    LOGGER.info("page batch validation passed: %s", json.dumps(metrics, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
