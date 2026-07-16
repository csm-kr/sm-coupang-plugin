#!/usr/bin/env python3
"""Build ten image-conditioned typography edit jobs from approved overlay copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

LOGGER = logging.getLogger("build_typography_prompts")
EXPECTED_PAGES = [f"{index:02d}" for index in range(1, 11)]
TEXT_KEYS = ("eyebrow", "headline", "subcopy", "badge", "disclosure")
SUPPORT_PREFIXES = ("card_", "step_", "spec_", "caption_", "chip_", "compare_")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build TY-01..TY-10 conditioned typography prompts")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--copy", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_copy(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
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


def exact_text(fields: dict[str, str]) -> list[dict[str, str]]:
    values: list[dict[str, str]] = []
    for key in TEXT_KEYS:
        value = fields.get(key, "").strip()
        if value:
            values.append({"role": key, "text": value})
    for key in sorted(fields):
        if key.startswith(SUPPORT_PREFIXES) and fields[key].strip():
            values.append({"role": key, "text": fields[key].strip()})
    return values


def prompt_for(
    page: str,
    values: list[dict[str, str]],
    fields: dict[str, str],
    brand_lock: str = "",
    concept_only: bool = False,
    target_width: int = 780,
    target_height: int | None = None,
) -> str:
    literal = "\n".join(f'- {item["role"]}: "{item["text"]}"' for item in values)
    commercial_job = fields.get("commercial_job", "proof")
    alignment = fields.get("headline_alignment", "center")
    emphasis = fields.get("emphasis", "")
    proof_type = fields.get("proof_type", "product_evidence")
    concept_note = (
        "Render the exact disclosure '연출용 콘셉트 이미지' as a clear but subordinate Korean label inside the safe area. It must remain legible and must not be mistaken for a verified product proof badge."
        if concept_only
        else ""
    )
    card_note = (
        "Place every card_*, step_*, spec_*, caption_*, chip_*, and compare_* string inside its corresponding existing blank module. Use identical margins, label sizes, and baseline logic for repeated modules. For specification or key-value rows, lock a fixed label column, a fixed separator column, and a fixed value column; every value must begin on the same x-axis and wrapped continuation lines must use that same hanging indent."
        if any(item["role"].startswith(SUPPORT_PREFIXES) for item in values)
        else ""
    )
    size_targets = (
        "74~94px for a hero hook, 60~78px for other headlines, 26~34px for body text, and 19~25px for labels/captions"
        if target_width == 800
        else "72~92px for a hero hook, 58~76px for other headlines, 25~32px for body text, and 18~24px for labels/captions"
    )
    canvas_lock = (
        f"The final published canvas is exactly {target_width}x{target_height}px. Compose for this full portrait height and keep every text block inside it."
        if target_height is not None
        else f"The final published width is {target_width}px."
    )
    return f"""Use case: ads-marketing
Asset type: Korean Coupang mobile detail-page panel {page}
Input images: Image 1 is the only edit target and visual condition.
Commercial role: {commercial_job}; evidence module: {proof_type}; locked headline alignment: {alignment}.
Primary request: Add only the approved typography below to Image 1. First inspect the actual negative space, product evidence, and subject hierarchy, then create a conversion-focused Korean ecommerce composition. Strengthen the page role with scale, line breaks, alignment, color contrast, and repeated card/step logic. Do not redesign or restyle the photograph.
Brand system: {brand_lock or 'Use the approved project UI guide and preserve its brand constants.'}
Text (verbatim; render each supplied string exactly once):
{literal}
Emphasis: Within the headline, render only the exact substring "{emphasis}" in one high-contrast accent color. Do not render it as a separate or duplicate text element.
Typography: conversion-focused Korean ecommerce art direction; ExtraBold/Black Korean headline, tight 0.96~1.08 line spacing, one or two balanced lines preferred and three lines maximum, clearly smaller clean Korean subcopy, compact Bold labels, and strong step numbers where supplied. Use a wide, stable Korean sans rather than condensed or vertically stretched glyphs. Keep the headline as a wide commercial block: do not make a short second line larger than the first, and keep its total height proportionate to its width. At final {target_width}px width, target {size_targets}. Prefer deep navy or charcoal on white and white on saturated color panels. Avoid pale editorial typography and weak contrast.
Page-specific note: {card_note or 'Keep text in genuine negative space and away from the main subject.'} {concept_note}
Constraints: {canvas_lock} Follow the locked headline alignment; use one optical center axis for centered blocks and a consistent left/card axis for comparison, step, or information blocks. Change only by adding typography and minimal flat support shapes such as a contrast band, card, line, comparison marker, or step circle. Preserve every face, hair, expression, body, hand, finger, product, seam, thumb opening, label, panel, inset, crop, background, lighting, color grade, and composition exactly as Image 1. Keep all text fully inside the canvas with generous mobile-safe margins. If this is a correction attempt, edit only the specified text region. Allow at most three targeted ImageGen text-edit attempts. Never use local typography fallback, external font layout, or text-overlay compositing.
Avoid: centering every module by habit; thin or light headline fonts; loose headline leading; covering a face, hand, product, inset, or information card; changing any supplied wording; misspelled or broken Hangul; duplicate or extra characters; unsupplied prices, discounts, reviews, certifications, claims, logos, or watermarks.
"""


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    output = project / "output"
    copy_path = (args.copy or output / "copy" / "overlay-copy.md").expanduser().resolve()
    generated_manifest = output / "generated-pages" / "manifest.json"
    if not copy_path.is_file() or not generated_manifest.is_file():
        LOGGER.error("overlay copy or generated-pages manifest missing")
        return 1
    sections = parse_copy(copy_path)
    if sorted(sections) != EXPECTED_PAGES:
        LOGGER.error("overlay copy must contain exactly sections 01..10")
        return 1

    workflow_v5 = (output / "project-manifest.yaml").is_file()
    workflow_version = "legacy"
    target_width = 780
    target_height: int | None = None
    target_canvas: dict = {}
    brand_path = output / "brand" / "brand-system.json"
    lineage_path = output / "product-source-lineage.json"
    brand_system: dict = {}
    identity_status = "legacy_untracked"
    if workflow_v5:
        if yaml is None:
            LOGGER.error("PyYAML is required for version-5 typography")
            return 1
        if not brand_path.is_file() or not lineage_path.is_file():
            LOGGER.error("version-5 typography requires brand-system.json and product-source-lineage.json")
            return 1
        try:
            project_manifest = yaml.safe_load((output / "project-manifest.yaml").read_text(encoding="utf-8-sig")) or {}
            brand_system = json.loads(brand_path.read_text(encoding="utf-8-sig"))
            lineage = json.loads(lineage_path.read_text(encoding="utf-8-sig"))
            identity_status = str(lineage.get("identity_status", ""))
            workflow_version = str(project_manifest.get("workflow_version", "5.0"))
            target_canvas = project_manifest.get("project", {}).get("canvas", {})
            target_width = int(target_canvas.get("width", 780))
            target_height = int(target_canvas["height"]) if target_canvas.get("height") is not None else None
        except Exception as exc:
            LOGGER.error("version-5 brand/lineage parse failed: %s", exc)
            return 1
        if workflow_version in {"5.1", "5.2"}:
            naming = brand_system.get("naming", {})
            if not str(naming.get("selected_name", "")).strip():
                LOGGER.error("workflow 5.1+ typography requires a selected product brand-name proposal")
                return 1
            if target_width != 800 or target_height != 2400:
                LOGGER.error("workflow 5.1+ typography requires an 800x2400 target canvas")
                return 1
    brand_lock = json.dumps(
        {
            "voice": brand_system.get("voice", {}).get("principles", []),
            "core_colors": brand_system.get("visual", {}).get("core_colors", {}),
            "typography": brand_system.get("visual", {}).get("typography", {}),
            "components": brand_system.get("visual", {}).get("components", []),
            "memory_devices": brand_system.get("visual", {}).get("memory_devices", []),
            "logo_policy": brand_system.get("campaign_rules", {}).get("logo_policy", ""),
            "style_priority": brand_system.get("style_priority", []),
            "brand_name_status": brand_system.get("naming", {}).get("status", ""),
            "brand_name_usage_allowed": brand_system.get("name_usage_allowed", False),
        },
        ensure_ascii=False,
    ) if workflow_v5 else ""

    prompt_dir = output / "typography-prompts"
    page_dir = output / "typography-pages"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    page_dir.mkdir(parents=True, exist_ok=True)
    existing = list(prompt_dir.glob("TY-*.md"))
    if existing and not args.force:
        LOGGER.error("existing typography prompts preserved; use --force to replace")
        return 2

    jobs = []
    manifest_pages = []
    master = [
        "# Conditioned typography pass",
        "",
        "각 PG 무문자 베이스를 유일한 편집 대상으로 다시 입력한다. 승인 카피는 바꾸지 않고 이미지 맥락에 맞는 조판만 생성한다.",
        "",
    ]
    for page in EXPECTED_PAGES:
        job_id = f"TY-{page}"
        base = output / "generated-pages" / f"PG-{page}.png"
        if not base.is_file():
            LOGGER.error("base image missing: %s", base)
            return 1
        values = exact_text(sections[page])
        if identity_status == "concept_only" and not any(item["role"] == "disclosure" for item in values):
            values.append({"role": "disclosure", "text": "연출용 콘셉트 이미지"})
        if len(values) < 2:
            LOGGER.error("%s requires at least headline and subcopy/badge", page)
            return 1
        fields = sections[page]
        if fields.get("copy_status", "approved").startswith("draft"):
            LOGGER.error("%s copy is still a draft; rewrite from verified product facts and set copy_status: approved", page)
            return 1
        headline = fields.get("headline", "")
        emphasis = fields.get("emphasis", "")
        if not emphasis or headline.count(emphasis) != 1:
            LOGGER.error("%s emphasis must appear exactly once inside the headline", page)
            return 1
        if fields.get("headline_alignment", "") not in {"left", "center"}:
            LOGGER.error("%s headline_alignment must be left or center", page)
            return 1
        prompt = prompt_for(
            page,
            values,
            fields,
            brand_lock=brand_lock,
            concept_only=identity_status == "concept_only",
            target_width=target_width,
            target_height=target_height,
        )
        base_rel = f"output/generated-pages/PG-{page}.png"
        out_rel = f"output/typography-pages/{job_id}.png"
        job = {
            "id": job_id,
            "page": page,
            "mode": "imagegen_conditioned_edit",
            "base_image": base_rel,
            "base_sha256": digest(base),
            "output_path": out_rel,
            "exact_text": values,
            "commercial_job": fields.get("commercial_job", ""),
            "headline_alignment": fields.get("headline_alignment", ""),
            "emphasis": emphasis,
            "text_partial_edit_limit": 3,
            "local_typography_fallback_allowed": False,
            "prompt": prompt,
        }
        jobs.append(job)
        manifest_pages.append(
            {
                "job_id": job_id,
                "page": page,
                "attempt": 0,
                "status": "pending",
                "file": out_rel,
                "sha256": "",
                "base_image": base_rel,
                "base_sha256": digest(base),
                "exact_text": values,
                "render_mode": "imagegen_conditioned",
                "text_partial_edit_attempts": 0,
                "local_typography_fallback_used": False,
                "text_accuracy": "pending",
                "base_preservation": "pending",
                "product_fidelity": "pending",
                "commercial_hierarchy": "pending",
                "commercial_flow_support": "pending",
                "alignment_consistency": "pending",
                "headline_compactness": "pending",
                "source_person_pixels": "none",
                "notes": "",
            }
        )
        markdown = f"""# {job_id} · page {page}

- mode: `imagegen_conditioned_edit`
- edit_target: `{base_rel}`
- output: `{out_rel}`

## Exact text

""" + "\n".join(f'- {item["role"]}: `{item["text"]}`' for item in values) + f"""

## Prompt

{prompt}
## Acceptance

- text_accuracy: pass / fail
- base_preservation: pass / fail
- product_fidelity: pass / fail
- commercial_hierarchy: pass / fail
- commercial_flow_support: pass / fail
- alignment_consistency: pass / fail
- headline_compactness: pass / fail
- text_partial_edit_attempts: 0 / 1 / 2 / 3
- local_typography_fallback_used: false
- source_person_pixels: none / found
- decision: approved / rejected
"""
        (prompt_dir / f"{job_id}.md").write_text(markdown, encoding="utf-8")
        master.append(f"- [{job_id}]({job_id}.md): `{base_rel}` → `{out_rel}`")

    queue = {
        "version": "1.0",
        "workflow_version": workflow_version,
        "method": "imagegen_conditioned_typography",
        "source_copy_sha256": digest(copy_path),
        "source_generated_manifest_sha256": digest(generated_manifest),
        "brand_system_sha256": digest(brand_path) if workflow_v5 else "",
        "identity_status": identity_status,
        "target_canvas": target_canvas if workflow_v5 else {},
        "brand_name": str(brand_system.get("name", "")) if workflow_v5 else "",
        "brand_name_status": str(brand_system.get("naming", {}).get("status", "")) if workflow_v5 else "",
        "brand_name_usage_allowed": bool(brand_system.get("name_usage_allowed")) if workflow_v5 else False,
        "text_partial_edit_limit": 3 if workflow_version == "5.2" else 2,
        "local_typography_fallback_allowed": False if workflow_version == "5.2" else True,
        "jobs": jobs,
    }
    queue_path = output / "typography-queue.json"
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (prompt_dir / "master.md").write_text("\n".join(master) + "\n", encoding="utf-8")
    typography_manifest = {
        "version": "1.0",
        "method": "imagegen_conditioned_typography",
        "text_partial_edit_limit": 3 if workflow_version == "5.2" else 2,
        "local_typography_fallback_allowed": False if workflow_version == "5.2" else True,
        "queue_sha256": digest(queue_path),
        "pages": manifest_pages,
    }
    (page_dir / "manifest.json").write_text(
        json.dumps(typography_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    LOGGER.info("built exactly ten conditioned typography prompts: %s", prompt_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
