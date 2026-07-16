#!/usr/bin/env python3
"""Validate the ten-page conditioned typography pass and published images."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

LOGGER = logging.getLogger("validate_typography_pass")
EXPECTED_PAGES = [f"{index:02d}" for index in range(1, 11)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate TY-01..TY-10 conditioned typography outputs")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", default="output")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_typography(
    project: Path,
    strict: bool = False,
    output_root: str = "output",
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> tuple[list[str], list[str], dict[str, int]]:
    output = project / output_root
    queue_path = output / "typography-queue.json"
    manifest_path = output / "typography-pages" / "manifest.json"
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"approved_pages": 0, "conditioned_pages": 0, "local_fallback_pages": 0}
    if not queue_path.is_file() or not manifest_path.is_file():
        return ["typography queue or manifest missing"], warnings, metrics
    try:
        queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return [f"typography JSON parse failed: {exc}"], warnings, metrics
    jobs = queue.get("jobs", [])
    pages = manifest.get("pages", [])
    if [str(item.get("page", "")).zfill(2) for item in jobs] != EXPECTED_PAGES:
        errors.append("typography queue must contain pages 01..10 in order")
    if [str(item.get("page", "")).zfill(2) for item in pages] != EXPECTED_PAGES:
        errors.append("typography manifest must contain pages 01..10 in order")
    if manifest.get("queue_sha256") != digest(queue_path):
        errors.append("typography manifest queue hash mismatch")
    workflow_version = str(queue.get("workflow_version", "legacy"))
    workflow_v5 = workflow_version in {"5.0", "5.1", "5.2"}
    identity_status = str(queue.get("identity_status", "legacy_untracked"))
    if workflow_version == "5.2":
        if queue.get("text_partial_edit_limit") != 3 or manifest.get("text_partial_edit_limit") != 3:
            errors.append("workflow 5.2 requires a text partial edit limit of exactly 3")
        if queue.get("local_typography_fallback_allowed") is not False or manifest.get("local_typography_fallback_allowed") is not False:
            errors.append("workflow 5.2 must forbid local typography fallback")
        if int(manifest.get("local_fallback_pages", 0)) != 0:
            errors.append("workflow 5.2 local_fallback_pages must be zero")
    if workflow_v5:
        brand_path = output / "brand" / "brand-system.json"
        if not brand_path.is_file():
            errors.append("version-5 typography requires brand-system.json")
        elif queue.get("brand_system_sha256") != digest(brand_path):
            errors.append("typography queue brand_system_sha256 is missing or stale")
    minimum_source_width = 780
    if workflow_version in {"5.1", "5.2"}:
        manifest_path_yaml = output / "project-manifest.yaml"
        if yaml is None:
            errors.append("PyYAML is required to validate workflow 5.1+ canvas")
        elif not manifest_path_yaml.is_file():
            errors.append("workflow 5.1+ typography requires project-manifest.yaml")
        else:
            try:
                project_manifest = yaml.safe_load(manifest_path_yaml.read_text(encoding="utf-8-sig")) or {}
                canvas = project_manifest.get("project", {}).get("canvas", {})
                manifest_width = int(canvas.get("width", 0))
                manifest_height = int(canvas.get("height", 0))
                if manifest_width != 800 or manifest_height != 2400:
                    errors.append("workflow 5.1+ published canvas must be exactly 800x2400")
                if queue.get("target_canvas") != canvas:
                    errors.append("typography queue target_canvas differs from project manifest")
                expected_width = expected_width or manifest_width
                expected_height = expected_height or manifest_height
                minimum_source_width = manifest_width
            except Exception as exc:
                errors.append(f"workflow 5.1+ canvas parse failed: {exc}")
    queue_by_page = {str(item.get("page", "")).zfill(2): item for item in jobs}
    hashes: dict[str, list[str]] = {}
    try:
        from PIL import Image
    except ImportError:
        Image = None
        errors.append("Pillow missing")
    for item in pages:
        page = str(item.get("page", "")).zfill(2)
        expected = queue_by_page.get(page, {})
        if item.get("status") != "approved":
            errors.append(f"{page}: typography status is not approved")
        else:
            metrics["approved_pages"] += 1
        mode = item.get("render_mode")
        if mode == "imagegen_conditioned":
            metrics["conditioned_pages"] += 1
        elif mode == "local_fallback":
            metrics["local_fallback_pages"] += 1
            if workflow_version == "5.2":
                errors.append(f"{page}: local typography fallback is forbidden")
            else:
                warnings.append(f"{page}: local typography fallback used")
        else:
            errors.append(f"{page}: invalid render_mode {mode}")
        for field in (
            "text_accuracy",
            "base_preservation",
            "product_fidelity",
            "commercial_hierarchy",
            "commercial_flow_support",
            "alignment_consistency",
            "headline_compactness",
        ):
            if item.get(field) != "pass":
                errors.append(f"{page}: {field} must pass")
        if workflow_v5:
            for field in ("brand_consistency", "product_source_lineage"):
                if item.get(field) != "pass":
                    errors.append(f"{page}: {field} must pass")
        if workflow_version == "5.2":
            text_attempts = item.get("text_partial_edit_attempts")
            if not isinstance(text_attempts, int) or not 0 <= text_attempts <= 3:
                errors.append(f"{page}: text_partial_edit_attempts must be 0..3")
            if item.get("local_typography_fallback_used") is not False:
                errors.append(f"{page}: local_typography_fallback_used must be false")
        if item.get("source_person_pixels") != "none":
            errors.append(f"{page}: source person pixels must be none")
        if item.get("exact_text") != expected.get("exact_text"):
            errors.append(f"{page}: exact text differs from typography queue")
        if identity_status == "concept_only":
            exact_values = expected.get("exact_text", [])
            if not any(
                isinstance(value, dict)
                and value.get("role") == "disclosure"
                and value.get("text") == "연출용 콘셉트 이미지"
                for value in exact_values
            ):
                errors.append(f"{page}: concept-only disclosure is missing")
        if item.get("base_sha256") != expected.get("base_sha256"):
            errors.append(f"{page}: base image hash differs from typography queue")
        file_value = str(item.get("file", ""))
        path = project / file_value
        if not path.is_file():
            errors.append(f"{page}: typography image missing")
            continue
        actual_hash = digest(path)
        if item.get("sha256") != actual_hash:
            errors.append(f"{page}: typography image hash mismatch")
        hashes.setdefault(actual_hash, []).append(page)
        if Image:
            try:
                with Image.open(path) as image:
                    width, height = image.size
                if width < minimum_source_width or height <= width:
                    errors.append(f"{page}: invalid portrait size {width}x{height}")
            except Exception as exc:
                errors.append(f"{page}: image read failed: {exc}")
        if strict:
            published = output / "images" / f"{page}.png"
            if not published.is_file():
                errors.append(f"{page}: published image missing")
            elif Image:
                with Image.open(published) as image:
                    width_ok = image.width == (expected_width or 780)
                    height_ok = (
                        image.height == expected_height
                        if expected_height is not None
                        else image.height > image.width
                    )
                    if not width_ok or not height_ok:
                        errors.append(f"{page}: invalid published size {image.width}x{image.height}")
    for duplicate_pages in hashes.values():
        if len(duplicate_pages) > 1:
            errors.append("duplicate typography pixels: " + ", ".join(duplicate_pages))
    return errors, warnings, metrics


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    errors, warnings, metrics = validate_typography(
        args.project.expanduser().resolve(),
        args.strict,
        args.output_root,
        args.width,
        args.height,
    )
    for item in errors:
        LOGGER.error(item)
    for item in warnings:
        LOGGER.warning(item)
    if errors or (args.strict and warnings):
        LOGGER.error("typography validation failed: errors=%d warnings=%d", len(errors), len(warnings))
        return 1
    LOGGER.info("typography validation passed: %s", metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
