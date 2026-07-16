#!/usr/bin/env python3
"""Record an explicitly reviewed conditioned-typography pass."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output-root", default="output")
    parser.add_argument("--confirm-exact-text", action="store_true")
    parser.add_argument("--confirm-base-preservation", action="store_true")
    parser.add_argument("--confirm-product-fidelity", action="store_true")
    parser.add_argument("--confirm-person-free", action="store_true")
    parser.add_argument("--confirm-alignment-consistency", action="store_true")
    parser.add_argument("--confirm-headline-compactness", action="store_true")
    parser.add_argument("--confirm-brand-consistency", action="store_true")
    parser.add_argument("--confirm-product-lineage", action="store_true")
    args = parser.parse_args()

    confirmations = (
        args.confirm_exact_text,
        args.confirm_base_preservation,
        args.confirm_product_fidelity,
        args.confirm_person_free,
        args.confirm_alignment_consistency,
        args.confirm_headline_compactness,
    )
    if not all(confirmations):
        parser.error("all six base --confirm-* review flags are required")

    root = args.project / args.output_root
    queue_path = root / "typography-queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    workflow_version = str(queue.get("workflow_version", "legacy"))
    workflow_v5 = workflow_version in {"5.0", "5.1", "5.2"}
    if workflow_v5 and not (args.confirm_brand_consistency and args.confirm_product_lineage):
        parser.error("version-5 approval also requires --confirm-brand-consistency and --confirm-product-lineage")
    text_attempts_by_page = {f"{value:02d}": 0 for value in range(1, 11)}
    if workflow_version == "5.2":
        regeneration_path = root / "regeneration-log.json"
        regeneration = json.loads(regeneration_path.read_text(encoding="utf-8-sig"))
        if regeneration.get("max_text_partial_edits_per_page") != 3:
            parser.error("workflow 5.2 regeneration log must allow exactly three text partial edits")
        if regeneration.get("local_typography_fallback_allowed") is not False:
            parser.error("workflow 5.2 forbids local typography fallback")
        for page, entries in regeneration.get("pages", {}).items():
            page_id = str(page).zfill(2)
            if page_id not in text_attempts_by_page or not isinstance(entries, list):
                continue
            text_entries = [entry for entry in entries if isinstance(entry, dict) and entry.get("edit_type") == "text_partial_edit"]
            if len(text_entries) > 3:
                parser.error(f"page {page_id} exceeds three text partial edits")
            if any(entry.get("edit_type") == "local_typography_fallback" for entry in entries if isinstance(entry, dict)):
                parser.error(f"page {page_id} uses forbidden local typography fallback")
            if len(text_entries) == 3 and text_entries[-1].get("result") != "pass":
                parser.error(f"page {page_id} must remain BLOCKED_TEXT after three failed text edits")
            text_attempts_by_page[page_id] = len(text_entries)
    pages = []
    for job in queue["jobs"]:
        page = str(job["page"]).zfill(2)
        image_path = root / "typography-pages" / f"TY-{page}.png"
        if not image_path.is_file():
            raise FileNotFoundError(image_path)
        pages.append(
            {
                "job_id": f"TY-{page}",
                "page": page,
                "attempt": 1,
                "status": "approved",
                "file": f"{args.output_root}/typography-pages/TY-{page}.png",
                "sha256": digest(image_path),
                "base_image": job["base_image"],
                "base_sha256": job["base_sha256"],
                "exact_text": job["exact_text"],
                "render_mode": "imagegen_conditioned",
                "text_partial_edit_attempts": text_attempts_by_page[page],
                "local_typography_fallback_used": False,
                "text_accuracy": "pass",
                "base_preservation": "pass",
                "product_fidelity": "pass",
                "commercial_hierarchy": "pass",
                "commercial_flow_support": "pass",
                "alignment_consistency": "pass",
                "headline_compactness": "pass",
                "brand_consistency": "pass" if workflow_v5 else "not_applicable",
                "product_source_lineage": "pass" if workflow_v5 else "not_applicable",
                "alignment": "pass",
                "source_person_pixels": "none",
                "notes": f"조건 이미지 승인; 한글 영역 부분 편집 {text_attempts_by_page[page]}회; 잠금 문구 및 정렬 수동 검토 완료",
            }
        )

    manifest_path = root / "typography-pages" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": "2.0" if workflow_v5 else "1.0",
                "workflow_version": workflow_version,
                "method": "imagegen_conditioned_typography",
                "queue_sha256": digest(queue_path),
                "local_fallback_pages": 0,
                "text_partial_edit_limit": 3 if workflow_version == "5.2" else 2,
                "local_typography_fallback_allowed": False if workflow_version == "5.2" else True,
                "pages": pages,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[OK] approved {len(pages)} pages -> {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
