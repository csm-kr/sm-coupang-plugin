#!/usr/bin/env python3
"""Build exactly ten synthetic-person-safe ImageGen page jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

LOGGER = logging.getLogger("build_imagegen_queue")

PAGE_SPECS = [
    ("PG-01", "01", "hero", "synthetic_model_hero", True, "hero", "hook"),
    ("PG-02", "02", "product_overview", "product_flatlay", False, "product", "product_overview"),
    ("PG-03", "03", "problem_context", "product_contact_evidence", False, "problem", "contact"),
    ("PG-04", "04", "construction", "people_free_construction", False, "feature", "structure"),
    ("PG-05", "05", "key_detail", "product_deformation_sequence", False, "feature", "deformation"),
    ("PG-06", "06", "material_detail", "product_storage_portability", False, "feature", "portability"),
    ("PG-07", "07", "daily_use", "synthetic_hands_feet_use_sequence", True, "lifestyle", "use_sequence"),
    ("PG-08", "08", "lifestyle_mosaic", "people_free_use_context_mosaic", False, "lifestyle", "use_context"),
    ("PG-09", "09", "product_information", "product_information_still_life", False, "product", "specification"),
    ("PG-10", "10", "closing", "people_free_function_recap", False, "closing", "recap"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a ten-page ImageGen batch with synthetic people only")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--reference", type=Path, help="Optional user art-direction reference; uses the bundled commercial benchmark when omitted")
    parser.add_argument("--product-images", type=Path, nargs="+", required=True)
    parser.add_argument("--confirm-person-free", action="store_true", help="Confirm every product input was visually verified to contain no person pixels")
    parser.add_argument("--confirm-actual-product-source", action="store_true", help="Confirm version-5 product inputs are trusted raw_capture/manufacturer_source records")
    parser.add_argument("--confirm-concept-only", action="store_true", help="Proceed under an explicit concept-only opt-in; generated assets are not actual product evidence")
    parser.add_argument("--style-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def normalize(project: Path, value: Path) -> tuple[str, Path]:
    path = value.expanduser()
    resolved = path.resolve() if path.is_absolute() else (project / path).resolve()
    try:
        relative = resolved.relative_to(project).as_posix()
    except ValueError:
        relative = str(resolved)
    return relative, resolved


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def input_item(role: str, path: str, usage: str, **extra: str) -> dict[str, str]:
    return {"role": role, "path": path, "usage": usage, **extra}


def page_request(page: str) -> str:
    requests = {
        "01": "Conversion-focused hero with one newly synthesized adult Korean model or a dominant product-first crop, the product immediately recognizable, and a bold high-contrast headline zone occupying roughly the top fifth. Combine a relatable situation, clear product visibility, and a strong visual hook; avoid a quiet editorial look.",
        "02": "People-free solution overview showing the complete product and every provided component at large scale. Use one dominant product view plus two or three blank fact chips or callout modules. Preserve count, color, silhouette, openings, seams, and label placement.",
        "03": "People-free functional contact proof. Show the category-relevant verified contact or customer situation directly on the product surface: for rain goods use real-looking water beads, flowing water, or wet pavement touching the outer cover; for other categories use only a verified relevant contact. The product response must be visible without relying on icons. Never invent a performance grade, duration, certification, or competitor comparison.",
        "04": "People-free construction proof point 01. Show the complete product on a neutral shoe form or product stand plus two or three circular detail insets for verified fastening, adjustment, opening, or coverage structure. Keep the product large; no model face or repeated hero pose.",
        "05": "People-free functional proof point 02. Show one physical product through a clear three-state deformation or operation sequence such as bend, roll, unfold, open, or close, only when verified. The sequence must visibly explain utility rather than repeat crops.",
        "06": "People-free proof point 03 around verified storage, portability, care, material surface, or components. Use a dominant compact-storage comparison plus distinct support macros. Reserve compact aligned caption strips and avoid decorative lifestyle imagery.",
        "07": "Show a two- or three-step use sequence with newly synthesized hands and feet only, face fully out of frame. Do not repeat the PG-01 full-body pose. Use close camera angles on the product interaction, repeated blank step circles, and aligned caption zones; keep the product large in every step.",
        "08": "People-free friction-reducer mosaic with verified storage, options, and genuinely distinct use contexts represented through props and close product views. Use one dominant functional module and smaller support modules; no repeated model face, walk, or full-body photo.",
        "09": "People-free purchase-information panel with a large complete product, components, package if provided, and orderly blank modules for verified specifications, colors, size, care, and notices. Use a table/card hierarchy with strong row alignment; invent no text or values.",
        "10": "People-free product-first closing recap. Use one dominant complete product plus three visibly different functional evidence modules recovered from earlier pages, such as contact, fastening, deformation, portability, or specification. Make it distinct from page 01 and leave a bold compact final headline zone.",
    }
    return requests[page]


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    output_path = (args.output or project / "output" / "imagegen-queue.json").expanduser().resolve()
    if output_path.exists() and not args.force:
        LOGGER.error("existing queue preserved; use --force to replace: %s", output_path)
        return 2

    skill_dir = Path(__file__).resolve().parent.parent
    bundled_style_dir = skill_dir / "assets" / "commercial-reference"
    reference_value = args.reference or bundled_style_dir / "commercial-hero.png"
    reference_rel, reference_path = normalize(project, reference_value)
    if not reference_path.is_file():
        LOGGER.error("reference image missing: %s", reference_path)
        return 2

    if not args.confirm_person_free:
        LOGGER.error("--confirm-person-free is required after visual inspection of every product input")
        return 2

    if args.confirm_actual_product_source and args.confirm_concept_only:
        LOGGER.error("choose either --confirm-actual-product-source or --confirm-concept-only, not both")
        return 2

    workflow_v5 = (project / "output" / "project-manifest.yaml").is_file()
    project_manifest: dict = {}
    workflow_version = "legacy"
    target_canvas: dict = {}
    lineage: dict = {}
    lineage_by_path: dict[Path, dict] = {}
    identity_status = "legacy_untracked"
    if workflow_v5:
        if yaml is None:
            LOGGER.error("PyYAML is required for version-5 workflow gate checks")
            return 2
        try:
            project_manifest = yaml.safe_load((project / "output" / "project-manifest.yaml").read_text(encoding="utf-8-sig")) or {}
        except Exception as exc:
            LOGGER.error("invalid project-manifest.yaml: %s", exc)
            return 2
        workflow_version = str(project_manifest.get("workflow_version", "5.0"))
        target_canvas = project_manifest.get("project", {}).get("canvas", {})
        if workflow_version in {"5.1", "5.2"} and (
            target_canvas.get("width") != 800 or target_canvas.get("height") != 2400
        ):
            LOGGER.error("workflow 5.1+ requires a fixed 800x2400 canvas")
            return 2
        if workflow_version == "5.3" and (
            target_canvas.get("mode") != "responsive"
            or target_canvas.get("width") != 800
            or target_canvas.get("height") is not None
            or target_canvas.get("min_width") != 360
            or target_canvas.get("max_width") != 800
        ):
            LOGGER.error("workflow 5.3 requires a responsive 360..800px HTML canvas")
            return 2
        gates = project_manifest.get("gates", {}) if isinstance(project_manifest, dict) else {}
        prerequisites = ("evidence", "market", "brand", "planning", "ui_assets")
        pending = [gate for gate in prerequisites if gates.get(gate) != "pass"]
        if pending:
            LOGGER.error("version-5 queue is blocked until prerequisite gates pass: %s", ", ".join(pending))
            return 2
        lineage_path = project / "output" / "product-source-lineage.json"
        if not lineage_path.is_file():
            LOGGER.error("version-5 workflow requires product-source-lineage.json")
            return 2
        try:
            lineage = json.loads(lineage_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            LOGGER.error("invalid product-source-lineage.json: %s", exc)
            return 2
        identity_status = str(lineage.get("identity_status", ""))
        if identity_status == "verified" and not args.confirm_actual_product_source:
            LOGGER.error("verified identity requires --confirm-actual-product-source")
            return 2
        if identity_status == "concept_only" and not args.confirm_concept_only:
            LOGGER.error("concept-only identity requires --confirm-concept-only")
            return 2
        if identity_status not in {"verified", "concept_only"}:
            LOGGER.error("product identity must be verified or concept_only before queue creation")
            return 2
        for source in lineage.get("sources", []):
            if not isinstance(source, dict):
                continue
            value = str(source.get("local_path") or source.get("path_or_url") or "").strip()
            if not value or "://" in value:
                continue
            source_path = Path(value).expanduser()
            resolved_source = source_path.resolve() if source_path.is_absolute() else (project / source_path).resolve()
            lineage_by_path[resolved_source] = source

    brand_system: dict = {}
    brand_prompt = ""
    brand_path = project / "output" / "brand" / "brand-system.json"
    if workflow_v5:
        if not brand_path.is_file():
            LOGGER.error("version-5 workflow requires output/brand/brand-system.json")
            return 2
        try:
            brand_system = json.loads(brand_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            LOGGER.error("invalid brand-system.json: %s", exc)
            return 2
        visual = brand_system.get("visual", {})
        campaign_rules = brand_system.get("campaign_rules", {})
        if brand_system.get("status") not in {"working_draft", "established", "approved"}:
            LOGGER.error("brand-system status is invalid")
            return 2
        if not str(brand_system.get("promise", "")).strip():
            LOGGER.error("brand-system promise must be locked before queue creation")
            return 2
        if not isinstance(visual.get("core_colors"), dict) or len(visual.get("core_colors", {})) < 3:
            LOGGER.error("brand-system requires at least three role-based core colors")
            return 2
        for field in ("photography", "components", "memory_devices"):
            if not visual.get(field):
                LOGGER.error("brand-system visual.%s must be locked before queue creation", field)
                return 2
        for field in ("constants", "variables"):
            if not campaign_rules.get(field):
                LOGGER.error("brand-system campaign_rules.%s must be locked before queue creation", field)
                return 2
        if workflow_version in {"5.1", "5.2", "5.3"}:
            naming = brand_system.get("naming", {})
            expected_priority = ["practical_evidence", "professional_function", "emotional_lifestyle"]
            if not str(naming.get("selected_name", "")).strip():
                LOGGER.error("workflow 5.1+ requires a selected product brand-name proposal")
                return 2
            if brand_system.get("style_priority") != expected_priority:
                LOGGER.error("workflow 5.1+ brand style priority is invalid")
                return 2
        brand_prompt = (
            "\n\nBrand system lock: "
            + json.dumps(
                {
                    "status": brand_system.get("status"),
                    "promise": brand_system.get("promise"),
                    "personality": brand_system.get("personality"),
                    "voice_principles": brand_system.get("voice", {}).get("principles"),
                    "core_colors": visual.get("core_colors"),
                    "category_accent": visual.get("category_accent"),
                    "typography": visual.get("typography"),
                    "photography": visual.get("photography"),
                    "components": visual.get("components"),
                    "memory_devices": visual.get("memory_devices"),
                    "campaign_constants": campaign_rules.get("constants"),
                    "campaign_variables": campaign_rules.get("variables"),
                    "logo_policy": campaign_rules.get("logo_policy"),
                    "style_priority": brand_system.get("style_priority"),
                },
                ensure_ascii=False,
            )
            + "\nApply the brand constants consistently while varying page modules by commercial role. "
            "Do not invent or display a brand name, wordmark, logo, or slogan unless name_usage_allowed is true."
        )
    canvas_prompt = ""
    if workflow_v5 and target_canvas:
        if workflow_version == "5.3":
            canvas_prompt = (
                "\n\nHybrid HTML visual-material lock: generate a text-free external visual asset for a responsive 360..800px module. "
                "Keep the complete product and proof action crop-safe across mobile widths. Do not add copy, badges, tables, or typography."
            )
        else:
            canvas_prompt = (
                f"\n\nFinal canvas lock: compose every page for an exact {target_canvas.get('width')}x{target_canvas.get('height')}px "
                "portrait output. Keep all required product evidence and copy-safe zones inside that aspect ratio; do not design for a shorter editorial card."
            )

    product_inputs: list[dict[str, str]] = []
    product_input_by_source: dict[str, dict[str, str]] = {}
    seen: set[Path] = set()
    for index, value in enumerate(args.product_images, start=1):
        relative, resolved = normalize(project, value)
        if not resolved.is_file():
            LOGGER.error("product image missing: %s", resolved)
            return 2
        if resolved in seen:
            continue
        seen.add(resolved)
        lineage_record = lineage_by_path.get(resolved) if workflow_v5 else None
        if workflow_v5 and not lineage_record:
            LOGGER.error("product image is not registered in product-source-lineage.json: %s", resolved)
            return 2
        lineage_type = str(lineage_record.get("lineage_type", "legacy_product_only")) if lineage_record else "legacy_product_only"
        source_id = str(lineage_record.get("source_id", f"legacy-{index:02d}")) if lineage_record else f"legacy-{index:02d}"
        if workflow_v5 and identity_status == "verified":
            if lineage_type not in {"raw_capture", "manufacturer_source"} or lineage_record.get("trusted_for_identity") is not True:
                LOGGER.error("verified identity input must be a trusted raw_capture/manufacturer_source: %s", relative)
                return 2
        if workflow_v5 and lineage_record.get("contains_person") is not False:
            LOGGER.error("lineage must explicitly confirm contains_person=false: %s", relative)
            return 2
        usage = (
            "verified person-free actual product evidence; trusted for SKU identity; contains no face, skin, hand, arm, body, or person pixels"
            if identity_status == "verified"
            else (
                "person-free concept reference only; not actual product structure evidence; contains no person pixels"
                if identity_status == "concept_only"
                else "verified person-free product evidence only; contains no face, skin, hand, arm, body, or person pixels"
            )
        )
        product_input = input_item(
                f"product_evidence_{index:02d}",
                relative,
                usage,
                source_id=source_id,
                lineage_type=lineage_type,
            )
        product_inputs.append(product_input)
        product_input_by_source[source_id] = product_input
    if not product_inputs:
        LOGGER.error("at least one product image is required")
        return 2

    reference_routes: dict[str, dict] = {}
    canonical_source_ids: list[str] = []
    if workflow_version in {"5.2", "5.3"}:
        routing_path = project / "output" / "reference-routing.json"
        try:
            routing = json.loads(routing_path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            LOGGER.error("workflow 5.2 requires valid reference-routing.json: %s", exc)
            return 2
        if str(routing.get("identity_status", "")) != identity_status:
            LOGGER.error("reference-routing identity_status must match product-source-lineage.json")
            return 2
        canonical_source_ids = [str(value) for value in routing.get("canonical_sources", [])]
        minimum_canonical = 3 if identity_status == "verified" else 1
        if not minimum_canonical <= len(canonical_source_ids) <= 5 or len(set(canonical_source_ids)) != len(canonical_source_ids):
            LOGGER.error("workflow 5.2 requires %d..5 unique canonical source IDs", minimum_canonical)
            return 2
        missing_canonical = [value for value in canonical_source_ids if value not in product_input_by_source]
        if missing_canonical:
            LOGGER.error("canonical sources were not passed in --product-images: %s", ", ".join(missing_canonical))
            return 2
        reference_routes = routing.get("pages", {})
        if not isinstance(reference_routes, dict) or sorted(reference_routes) != [f"{value:02d}" for value in range(1, 11)]:
            LOGGER.error("reference-routing.pages must contain exactly 01..10")
            return 2
        for page, route in reference_routes.items():
            selected = [str(value) for value in route.get("source_ids", [])] if isinstance(route, dict) else []
            if not 1 <= len(selected) <= 5 or any(value not in canonical_source_ids for value in selected):
                LOGGER.error("reference route %s must select 1..5 canonical source IDs", page)
                return 2
            if not route.get("required_views") or not str(route.get("rationale", "")).strip() or route.get("missing_views"):
                LOGGER.error("reference route %s requires views, rationale, and no missing views", page)
                return 2

    invariant_path = project / "output" / "product-invariants.txt"
    if not invariant_path.is_file():
        LOGGER.error("product-invariants.txt missing: %s", invariant_path)
        return 2
    invariants = invariant_path.read_text(encoding="utf-8-sig").strip()
    if len([line for line in invariants.splitlines() if line.strip()]) < 5:
        LOGGER.error("product-invariants.txt needs at least five explicit non-empty lines")
        return 2

    style_dir = (args.style_dir or (project / "output" / "style-crops" if args.reference else bundled_style_dir)).expanduser().resolve()
    styles: dict[str, str] = {}
    for role in ("hero", "problem", "product", "feature", "lifestyle", "closing"):
        prefix = "style" if args.reference or args.style_dir else "commercial"
        relative, resolved = normalize(project, style_dir / f"{prefix}-{role}.png")
        if not resolved.is_file():
            LOGGER.error("style crop missing: %s", resolved)
            return 2
        styles[role] = relative

    universal = (
        "Create a fully original photorealistic Korean ecommerce page visual. "
        "All visible people, faces, skin, arms, hands, bodies, poses, and identities must be newly synthesized pixels. "
        "Do not edit, preserve, trace, composite, or reproduce any real person from any input. "
        "Do not resemble the person in the product evidence or the art-direction reference. "
        "Use the style crop only for composition, lighting, palette, spacing, scene density, and visual rhythm. "
        "Generate no Korean or English text, letters, numbers, logos, labels with readable text, badges, icons, prices, certifications, or watermarks. "
        "Use conversion-focused Korean mobile-commerce art direction: one dominant product or evidence visual, modular comparison/detail/step/spec areas where requested, strong white-versus-saturated-color section contrast, and intentional negative space for bold typography. Avoid weak editorial layouts, tiny floating products, and large unfinished blank bottoms."
    )
    if identity_status == "verified":
        universal += (
            " Treat only the registered raw_capture or manufacturer_source images as SKU identity evidence; "
            "keep silhouette, toe, opening, straps, fasteners, seams, sole, engravings, color, transparency, "
            "component count, and assembly identical across every scene."
        )
    elif identity_status == "concept_only":
        universal += (
            " This is concept-only art direction, not actual SKU evidence. Do not present imagined product structure, "
            "use steps, or details as verified facts, and reserve a clear typography area for the required Korean concept-image disclosure."
        )
    product_lock = (
        "\n\nProduct identity invariants (repeat exactly and obey):\n"
        + invariants
        + "\nDo not redesign, beautify, simplify, or add unverified product parts. "
          "If label text cannot be exact, make it unreadable and leave room for a product-only raw label composite."
    )

    jobs = []
    for job_id, page, role, scene, has_person, style_role, evidence_kind in PAGE_SPECS:
        depends_on = ["PG-01"] if has_person and job_id != "PG-01" else []
        selected_source_ids = (
            [str(value) for value in reference_routes[page]["source_ids"]]
            if workflow_version in {"5.2", "5.3"}
            else [str(value.get("source_id", "")) for value in product_inputs]
        )
        inputs = [dict(product_input_by_source[value]) for value in selected_source_ids]
        if depends_on:
            inputs.insert(
                0,
                input_item(
                    "synthetic_model_anchor",
                    "output/generated-pages/PG-01.png",
                    "synthetic identity continuity only",
                ),
            )
        inputs.append(
            input_item(
                f"style_{style_role}",
                styles[style_role],
                "art direction only; never copy text, product, brand, or person identity",
            )
        )
        identity = (
            " Create one entirely fictional adult Korean campaign model from text, with a natural short dark bob, neutral makeup, and understated cream-and-pale-blue wardrobe. This generated model becomes the only identity anchor for later pages."
            if job_id == "PG-01"
            else (
                " Match only the fictional model identity from PG-01: face, haircut, body proportions, wardrobe family, and color grade."
                if has_person
                else " Include no person, face, skin, hand, arm, or body."
            )
        )
        jobs.append(
            {
                "id": job_id,
                "page": page,
                "role": role,
                "scene": scene,
                "mode": "generate_from_references",
                "depends_on": depends_on,
                "contains_person": has_person,
                "face_visible_full_body": job_id == "PG-01",
                "evidence_kind": evidence_kind,
                "person_origin": "synthetic" if has_person else "none",
                "real_person_pixels_allowed": False,
                "source_person_usage": "excluded_from_all_inputs",
                "reference_source_ids": selected_source_ids,
                "required_product_views": reference_routes.get(page, {}).get("required_views", []),
                "input_images": inputs,
                "output_path": f"output/generated-pages/{job_id}.png",
                "prompt": universal + identity + " " + page_request(page) + product_lock + brand_prompt + canvas_prompt,
            }
        )

    queue = {
        "version": "4.0",
        "workflow_version": workflow_version,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output_count": 10,
        "batch_policy": "single_user_request_two_internal_parallel_stages_no_page_approval",
        "synthetic_model_anchor": "PG-01",
        "human_origin_policy": "synthetic_only",
        "real_person_pixels_allowed": False,
        "function_evidence_minimum": 5,
        "face_visible_full_body_limit": 2,
        "reference": reference_rel,
        "reference_policy": "art_direction_only_no_copy_no_claims_no_identity",
        "product_source_policy": (
            "trusted_person_free_actual_sources_only"
            if identity_status == "verified"
            else (
                "person_free_concept_sources_not_actual_evidence"
                if identity_status == "concept_only"
                else "verified_person_free_only; sources containing any person pixels are excluded from ImageGen and final composites"
            )
        ),
        "identity_status": identity_status,
        "actual_product_source_confirmed": bool(args.confirm_actual_product_source),
        "concept_only_confirmed": bool(args.confirm_concept_only),
        "product_lineage_path": "output/product-source-lineage.json" if workflow_v5 else "",
        "brand_system_path": "output/brand/brand-system.json" if workflow_v5 else "",
        "brand_system_sha256": digest(brand_path) if workflow_v5 else "",
        "brand_name_usage_allowed": bool(brand_system.get("name_usage_allowed")) if workflow_v5 else False,
        "brand_name_status": str(brand_system.get("naming", {}).get("status", "")) if workflow_v5 else "",
        "brand_name": str(brand_system.get("name", "")) if workflow_v5 else "",
        "target_canvas": target_canvas if workflow_v5 else {},
        "canonical_source_ids": canonical_source_ids,
        "reference_routing_path": "output/reference-routing.json" if workflow_version in {"5.2", "5.3"} else "",
        "product_invariants": invariants,
        "jobs": jobs,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_pages = []
    for job in jobs:
        fidelity_fields = ["silhouette", "count", "color", "openings", "seams", "label", "material"]
        if workflow_v5:
            fidelity_fields.extend(["toe", "straps", "fasteners", "cut_mold_lines", "sole", "engravings", "assembly"])
        manifest_pages.append(
            {
                "job_id": job["id"],
                "page": job["page"],
                "attempt": 0,
                "status": "pending",
                "file": job["output_path"],
                "sha256": "",
                "contains_person": job["contains_person"],
                "person_origin": job["person_origin"],
                "synthetic_person_check": "pending",
                "source_person_pixels": "pending",
                "text_free": "pending",
                "art_direction_match": "pending",
                "commercial_structure": "pending",
                "sku_identity": "pending" if workflow_v5 else "not_applicable",
                "source_lineage": "pending" if workflow_v5 else "not_applicable",
                "brand_consistency": "pending" if workflow_v5 else "not_applicable",
                "reference_source_ids": job.get("reference_source_ids", []),
                "targeted_edit_attempts": 0,
                "qa_gates": {
                    "file_layout": "pending",
                    "product_identity": "pending",
                    "text": "pending",
                    "information_advertising": "pending",
                },
                "product_fidelity": {field: "pending" for field in fidelity_fields},
                "notes": "",
            }
        )
    manifest = {
        "version": workflow_version if workflow_v5 else "4.0",
        "workflow_version": workflow_version,
        "queue_sha256": digest(output_path),
        "human_origin_policy": "synthetic_only",
        "real_person_pixels_allowed": False,
        "identity_status": identity_status,
        "pages": manifest_pages,
    }
    manifest_path = project / "output" / "generated-pages" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("ten-page ImageGen queue created: %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
