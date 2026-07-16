#!/usr/bin/env python3
"""Compile a ten-page ImageGen queue into executable page prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

from validate_campaign_assets import FIDELITY_FIELDS, PERSON_PAGES, validate_campaign

LOGGER = logging.getLogger("build_image_prompts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile PG-01..PG-10 ImageGen prompts")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    queue_path = (args.queue or project / "output" / "imagegen-queue.json").expanduser().resolve()
    output_dir = (args.output_dir or project / "output" / "prompts").expanduser().resolve()
    errors, _, _ = validate_campaign(project, queue_only=True)
    if errors:
        for item in errors:
            LOGGER.error(item)
        return 1
    queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = list(output_dir.glob("PG-*.md"))
    if existing and not args.force:
        LOGGER.error("existing prompt jobs preserved; use --force to replace")
        return 2

    master = [
        "# ImageGen 10-page batch",
        "",
        "한 번의 사용자 요청 안에서 실행한다. PG-01과 사람 없는 작업을 먼저 처리하고, PG-01을 합성 모델 기준으로 나머지 인물 작업에 재입력한다.",
        "실제 사람 픽셀을 편집·보존·합성하지 않는다. 생성 이미지 안에는 텍스트·로고·배지·아이콘을 만들지 않는다.",
        "",
    ]
    pages = []
    for item in queue["jobs"]:
        job_id = item["id"]
        page = str(item["page"]).zfill(2)
        inputs = "\n".join(
            f"- {value['role']}: `{value['path']}` — {value.get('usage', '')}" for value in item.get("input_images", [])
        )
        text = f"""# {job_id} · page {page} · {item['role']}

- scene: `{item['scene']}`
- mode: `generate_from_references`
- depends_on: {', '.join(item.get('depends_on', [])) or 'none'}
- contains_person: {str(bool(item.get('contains_person'))).lower()}
- person_origin: `{item['person_origin']}`
- real_person_pixels_allowed: false
- output: `{item['output_path']}`

## Input images

{inputs}

## Prompt

{item['prompt']}

## Immediate acceptance QA

- synthetic_person_check: pass / fail / not_applicable
- source_person_pixels: none / found
- text_free: pass / fail
- art_direction_match: pass / fail
- commercial_structure: pass / fail
- product silhouette:
- product count:
- product color:
- product openings:
- product seams:
- product label:
- product material:
- decision: approved / rejected
"""
        (output_dir / f"{job_id}.md").write_text(text, encoding="utf-8")
        master.append(f"- [{job_id}]({job_id}.md): page {page} / {item['role']} / {item['scene']}")
        pages.append(
            {
                "job_id": job_id,
                "page": page,
                "attempt": 0,
                "status": "pending",
                "file": item["output_path"],
                "sha256": "",
                "contains_person": bool(item.get("contains_person")),
                "person_origin": item.get("person_origin"),
                "synthetic_person_check": "pending" if page in PERSON_PAGES else "not_applicable",
                "source_person_pixels": "pending",
                "text_free": "pending",
                "art_direction_match": "pending",
                "commercial_structure": "pending",
                "product_fidelity": {field: "pending" for field in sorted(FIDELITY_FIELDS)},
                "notes": "",
            }
        )
    (output_dir / "master.md").write_text("\n".join(master) + "\n", encoding="utf-8")
    manifest_path = project / "output" / "generated-pages" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists() or args.force:
        manifest = {
            "version": "4.0",
            "queue_sha256": digest(queue_path),
            "human_origin_policy": "synthetic_only",
            "real_person_pixels_allowed": False,
            "pages": pages,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("compiled exactly ten page prompts: %s", output_dir)
    LOGGER.info("generated page QA manifest: %s", manifest_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
