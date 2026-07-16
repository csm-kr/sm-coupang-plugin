#!/usr/bin/env python3
"""Shared validation helpers for workflow 5.3 hybrid detail pages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PRODUCT_PLAN_PATH = "output/planning/product-plan.json"
CONTENT_PLAN_PATH = "output/planning/content-plan.json"
PRODUCT_APPROVAL_PATH = "output/approvals/product-plan-approval.json"
CONTENT_APPROVAL_PATH = "output/approvals/content-plan-approval.json"
ASSET_MANIFEST_PATH = "output/content-assets/manifest.json"
MATERIAL_QA_PATH = "output/qa/material-qa.json"
INTEGRATION_QA_PATH = "output/qa/integration-qa.json"

ALLOWED_CLAIM_STATUSES = {"CONFIRMED_USER", "CONFIRMED_SOURCE", "OBSERVED_IMAGE"}
MATERIAL_GATES = {
    "technical",
    "product_identity",
    "claim_evidence",
    "copy_accuracy",
    "visual_quality",
}
INTEGRATION_GATES = {
    "planning_alignment",
    "sequence_flow",
    "visual_consistency",
    "responsive_layout",
    "accessibility",
    "claims_policy",
    "channel_constraints",
}


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_json(path: Path, errors: list[str], label: str | None = None) -> dict[str, Any]:
    name = label or path.name
    if not path.is_file():
        errors.append(f"{name} missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"{name} parse failed: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{name} must be a JSON object")
        return {}
    return payload


def resolve_project_path(project: Path, value: str, errors: list[str], label: str) -> Path:
    project = project.resolve()
    candidate = (project / value).resolve()
    try:
        candidate.relative_to(project)
    except ValueError:
        errors.append(f"{label} escapes the project root: {value}")
    return candidate


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_text_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_nonempty_text(item) for item in value)


def validate_product_plan(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "1.0":
        errors.append("product-plan schema_version must be 1.0")
    if payload.get("artifact_type") != "product_plan":
        errors.append("product-plan artifact_type must be product_plan")
    if payload.get("status") != "ready_for_approval":
        errors.append("product-plan status must be ready_for_approval")
    for field in ("project_id", "source_candidate_id", "target_customer", "primary_problem", "positioning"):
        if not _nonempty_text(payload.get(field)):
            errors.append(f"product-plan {field} is required")
    offer = payload.get("offer")
    if not isinstance(offer, dict):
        errors.append("product-plan offer must be an object")
    else:
        if offer.get("currency") != "KRW":
            errors.append("product-plan offer.currency must be KRW")
        price = offer.get("recommended_price")
        if not isinstance(price, (int, float)) or price <= 0:
            errors.append("product-plan offer.recommended_price must be positive")
        bundles = offer.get("bundles")
        if not isinstance(bundles, list) or not bundles:
            errors.append("product-plan offer.bundles requires at least one bundle")
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("product-plan claims requires at least one confirmed claim")
    else:
        claim_ids: list[str] = []
        for index, claim in enumerate(claims, start=1):
            if not isinstance(claim, dict):
                errors.append(f"product-plan claim #{index} must be an object")
                continue
            claim_id = str(claim.get("id", "")).strip()
            claim_ids.append(claim_id)
            if not claim_id or not _nonempty_text(claim.get("text")):
                errors.append(f"product-plan claim #{index} requires id and text")
            if claim.get("status") not in ALLOWED_CLAIM_STATUSES:
                errors.append(f"product-plan claim {claim_id or index} has an unpublishable status")
            if not _nonempty_text_list(claim.get("evidence_ids")):
                errors.append(f"product-plan claim {claim_id or index} requires evidence_ids")
        if len(claim_ids) != len(set(claim_ids)):
            errors.append("product-plan claim IDs must be unique")
    if not isinstance(payload.get("constraints"), dict):
        errors.append("product-plan constraints must be an object")
    return errors


def validate_content_plan(project: Path, payload: dict[str, Any], product_plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "1.0":
        errors.append("content-plan schema_version must be 1.0")
    if payload.get("artifact_type") != "content_plan":
        errors.append("content-plan artifact_type must be content_plan")
    if payload.get("status") != "ready_for_approval":
        errors.append("content-plan status must be ready_for_approval")
    if not _nonempty_text(payload.get("project_id")):
        errors.append("content-plan project_id is required")
    if product_plan and payload.get("project_id") != product_plan.get("project_id"):
        errors.append("content-plan project_id must match product-plan")

    reference = payload.get("product_plan_ref")
    if not isinstance(reference, dict):
        errors.append("content-plan product_plan_ref must be an object")
    else:
        if reference.get("path") != PRODUCT_PLAN_PATH:
            errors.append(f"content-plan product_plan_ref.path must be {PRODUCT_PLAN_PATH}")
        product_path = project / PRODUCT_PLAN_PATH
        if product_path.is_file() and str(reference.get("sha256", "")).casefold() != sha256(product_path):
            errors.append("content-plan product_plan_ref is stale")

    rendering = payload.get("rendering")
    if not isinstance(rendering, dict):
        errors.append("content-plan rendering must be an object")
    else:
        expected = {
            "mode": "hybrid_html",
            "text_layer": "native_html",
            "visual_layer": "external_assets",
        }
        for field, value in expected.items():
            if rendering.get(field) != value:
                errors.append(f"content-plan rendering.{field} must be {value}")

    claims = product_plan.get("claims", []) if isinstance(product_plan, dict) else []
    claim_ids = {str(item.get("id", "")) for item in claims if isinstance(item, dict)}
    modules = payload.get("modules")
    if not isinstance(modules, list) or not modules:
        errors.append("content-plan modules requires at least one module")
        return errors
    module_ids: list[str] = []
    orders: list[int] = []
    for index, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
            errors.append(f"content-plan module #{index} must be an object")
            continue
        module_id = str(module.get("id", "")).strip()
        module_ids.append(module_id)
        if not module_id:
            errors.append(f"content-plan module #{index} requires id")
        order = module.get("order")
        if not isinstance(order, int) or order < 1:
            errors.append(f"content-plan module {module_id or index} requires a positive integer order")
        else:
            orders.append(order)
        for field in ("role", "headline", "body"):
            if not _nonempty_text(module.get(field)):
                errors.append(f"content-plan module {module_id or index} requires {field}")
        for field in ("evidence_ids", "claim_ids", "asset_ids", "editable_fields", "qa_criteria"):
            if not _nonempty_text_list(module.get(field)):
                errors.append(f"content-plan module {module_id or index} requires {field}")
        editable = set(module.get("editable_fields", [])) if isinstance(module.get("editable_fields"), list) else set()
        if not {"headline", "body"}.issubset(editable):
            errors.append(f"content-plan module {module_id or index} must keep headline and body editable")
        unknown_claims = set(module.get("claim_ids", [])) - claim_ids if isinstance(module.get("claim_ids"), list) else set()
        if unknown_claims:
            errors.append(f"content-plan module {module_id or index} references unknown claims: {', '.join(sorted(unknown_claims))}")
    if len(module_ids) != len(set(module_ids)):
        errors.append("content-plan module IDs must be unique")
    if sorted(orders) != list(range(1, len(modules) + 1)):
        errors.append("content-plan module order must be contiguous from 1")
    return errors


def validate_approval(project: Path, approval_relative: str, target_relative: str, label: str) -> list[str]:
    errors: list[str] = []
    approval = load_json(project / approval_relative, errors, label)
    target_path = project / target_relative
    if not approval:
        return errors
    if approval.get("schema_version") != "1.0":
        errors.append(f"{label} schema_version must be 1.0")
    if approval.get("artifact_type") != "approval":
        errors.append(f"{label} artifact_type must be approval")
    if approval.get("decision") != "approved":
        errors.append(f"{label} decision must be approved")
    if approval.get("actor_type") != "user":
        errors.append(f"{label} actor_type must be user")
    if not _nonempty_text(approval.get("actor_id")):
        errors.append(f"{label} actor_id is required")
    if not _nonempty_text(approval.get("approved_at")):
        errors.append(f"{label} approved_at is required")
    if approval.get("target_path") != target_relative:
        errors.append(f"{label} target_path must be {target_relative}")
    if target_path.is_file() and str(approval.get("target_sha256", "")).casefold() != sha256(target_path):
        errors.append(f"{label} is stale: the approved plan changed")
    return errors


def validate_planning(project: Path, gate: str = "content") -> list[str]:
    project = project.resolve()
    errors: list[str] = []
    product = load_json(project / PRODUCT_PLAN_PATH, errors, "product-plan")
    errors.extend(validate_product_plan(product))
    if errors or gate == "product-draft":
        return errors
    errors.extend(validate_approval(project, PRODUCT_APPROVAL_PATH, PRODUCT_PLAN_PATH, "product-plan approval"))
    if gate == "product":
        return errors

    content = load_json(project / CONTENT_PLAN_PATH, errors, "content-plan")
    errors.extend(validate_content_plan(project, content, product))
    if errors or gate == "content-draft":
        return errors
    errors.extend(validate_approval(project, CONTENT_APPROVAL_PATH, CONTENT_PLAN_PATH, "content-plan approval"))
    return errors


def validate_materials(project: Path) -> tuple[list[str], dict[str, Any], dict[str, Any], dict[str, Any]]:
    project = project.resolve()
    errors = validate_planning(project, "content")
    content = load_json(project / CONTENT_PLAN_PATH, errors, "content-plan")
    asset_manifest = load_json(project / ASSET_MANIFEST_PATH, errors, "content asset manifest")
    material_qa = load_json(project / MATERIAL_QA_PATH, errors, "material QA")
    if errors:
        return errors, content, asset_manifest, material_qa

    assets = asset_manifest.get("assets")
    if asset_manifest.get("schema_version") != "1.0" or not isinstance(assets, list) or not assets:
        errors.append("content asset manifest requires schema_version 1.0 and at least one asset")
        return errors, content, asset_manifest, material_qa
    asset_ids: list[str] = []
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            errors.append(f"content asset #{index} must be an object")
            continue
        asset_id = str(asset.get("id", "")).strip()
        asset_ids.append(asset_id)
        if not asset_id:
            errors.append(f"content asset #{index} requires id")
        if asset.get("type") not in {"image", "gif", "video"}:
            errors.append(f"content asset {asset_id or index} has an invalid type")
        value = str(asset.get("path", ""))
        if not value.replace("\\", "/").startswith("output/content-assets/"):
            errors.append(f"content asset {asset_id or index} must live under output/content-assets")
        path = resolve_project_path(project, value, errors, f"content asset {asset_id or index}")
        if not path.is_file():
            errors.append(f"content asset {asset_id or index} file missing: {value}")
        elif str(asset.get("sha256", "")).casefold() != sha256(path):
            errors.append(f"content asset {asset_id or index} SHA-256 is stale")
        for field in ("alt", "evidence_ids", "claim_ids", "lineage_ids"):
            value_field = asset.get(field)
            if field == "alt":
                if not _nonempty_text(value_field):
                    errors.append(f"content asset {asset_id or index} requires alt")
            elif not _nonempty_text_list(value_field):
                errors.append(f"content asset {asset_id or index} requires {field}")
    if len(asset_ids) != len(set(asset_ids)):
        errors.append("content asset IDs must be unique")

    modules = content.get("modules", [])
    module_map = {str(item.get("id", "")): item for item in modules if isinstance(item, dict)}
    known_assets = set(asset_ids)
    for module_id, module in module_map.items():
        unknown_assets = set(module.get("asset_ids", [])) - known_assets
        if unknown_assets:
            errors.append(f"content module {module_id} references unknown assets: {', '.join(sorted(unknown_assets))}")

    records = material_qa.get("materials")
    if material_qa.get("schema_version") != "1.0" or not isinstance(records, list):
        errors.append("material QA requires schema_version 1.0 and a materials array")
        return errors, content, asset_manifest, material_qa
    qa_map = {str(item.get("module_id", "")): item for item in records if isinstance(item, dict)}
    if set(qa_map) != set(module_map):
        errors.append("material QA must contain exactly one record for every content module")
    for module_id, module in module_map.items():
        record = qa_map.get(module_id, {})
        expected_assets = set(module.get("asset_ids", []))
        if set(record.get("asset_ids", [])) != expected_assets:
            errors.append(f"material QA {module_id} asset_ids must match the content module")
        gates = record.get("gates")
        if not isinstance(gates, dict) or not MATERIAL_GATES.issubset(gates):
            errors.append(f"material QA {module_id} is missing required gates")
        else:
            failed = sorted(gate for gate in MATERIAL_GATES if gates.get(gate) != "pass")
            if failed:
                errors.append(f"material QA {module_id} failed gates: {', '.join(failed)}")
        if record.get("automated_status") != "pass":
            errors.append(f"material QA {module_id} automated_status must pass")
        if record.get("visual_review_status") != "pass":
            errors.append(f"material QA {module_id} visual_review_status must pass")
        if record.get("status") != "pass":
            errors.append(f"material QA {module_id} status must pass")
    return errors, content, asset_manifest, material_qa
