#!/usr/bin/env python3
"""Assemble editable native HTML copy with separately generated visual assets."""

from __future__ import annotations

import argparse
import html
import json
import logging
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from hybrid_contract import ASSET_MANIFEST_PATH, CONTENT_PLAN_PATH, MATERIAL_QA_PATH, sha256, validate_materials


LOGGER = logging.getLogger("build_hybrid_detail_page")

CSS = """@charset \"utf-8\";
:root {
  color-scheme: light;
  --page-width: 800px;
  --ink: #10233f;
  --muted: #52647a;
  --surface: #ffffff;
  --canvas: #eef3f8;
  --accent: #1976d2;
  --radius: 24px;
  --space: clamp(20px, 5vw, 48px);
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; overflow-x: hidden; background: var(--canvas); color: var(--ink); }
body { font-family: \"Pretendard\", \"Noto Sans KR\", system-ui, -apple-system, sans-serif; line-height: 1.55; }
.detail-page { width: min(100%, var(--page-width)); margin: 0 auto; background: var(--surface); }
.content-module { display: grid; gap: var(--space); padding: clamp(48px, 10vw, 96px) clamp(24px, 8vw, 64px); border-bottom: 1px solid #dfe7ef; }
.content-module:nth-child(even) { background: #f7fafc; }
.module-copy { display: grid; gap: 16px; }
.module-role { margin: 0; color: var(--accent); font-size: 0.82rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
.module-headline { margin: 0; font-size: clamp(2rem, 7vw, 4.75rem); line-height: 1.06; letter-spacing: -0.045em; overflow-wrap: anywhere; }
.module-body { margin: 0; color: var(--muted); font-size: clamp(1rem, 3.6vw, 1.7rem); overflow-wrap: anywhere; }
.module-media { display: grid; gap: 16px; margin: 0; }
.module-media img, .module-media video { display: block; width: 100%; height: auto; border-radius: var(--radius); background: #e5ebf1; }
.module-media video { max-height: 75vh; }
@media (min-width: 680px) {
  .content-module[data-layout=\"split\"] { grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); align-items: center; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; }
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an editable HTML + external visual asset detail page")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    return parser.parse_args()


def relative_asset_url(value: str) -> str:
    normalized = PurePosixPath(value.replace("\\", "/"))
    parts = normalized.parts
    if len(parts) < 3 or parts[:2] != ("output", "content-assets"):
        raise ValueError(f"asset path must be under output/content-assets: {value}")
    relative = PurePosixPath("..", "content-assets", *parts[2:]).as_posix()
    return quote(relative, safe="/._-")


def claim_ids_attribute(values: object) -> str:
    claim_ids = values if isinstance(values, list) else []
    return html.escape(" ".join(str(value) for value in claim_ids), quote=True)


def media_markup(asset: dict[str, object], claim_ids: object) -> str:
    source = relative_asset_url(str(asset["path"]))
    alt = html.escape(str(asset["alt"]), quote=True)
    asset_id = html.escape(str(asset["id"]), quote=True)
    claims = claim_ids_attribute(claim_ids)
    kind = str(asset["type"])
    if kind == "video":
        return (
            f'<video data-asset-id="{asset_id}" data-claim-ids="{claims}" controls playsinline preload="metadata" '
            f'aria-label="{alt}"><source src="{source}"></video>'
        )
    return (
        f'<img data-asset-id="{asset_id}" data-claim-ids="{claims}" src="{source}" '
        f'alt="{alt}" loading="lazy" decoding="async">'
    )


def build_html(content: dict[str, object], assets: dict[str, object]) -> str:
    asset_map = {
        str(item["id"]): item
        for item in assets.get("assets", [])
        if isinstance(item, dict) and item.get("id")
    }
    sections: list[str] = []
    modules = sorted(content.get("modules", []), key=lambda item: int(item.get("order", 0)))
    for module in modules:
        module_id = html.escape(str(module["id"]), quote=True)
        role = html.escape(str(module["role"]))
        headline = html.escape(str(module["headline"]))
        body = html.escape(str(module["body"]))
        claim_ids = module.get("claim_ids", [])
        claims = claim_ids_attribute(claim_ids)
        media = "\n".join(
            media_markup(asset_map[str(asset_id)], claim_ids) for asset_id in module.get("asset_ids", [])
        )
        layout = "split" if len(module.get("asset_ids", [])) == 1 else "stack"
        sections.append(
            f'''    <section class="content-module" data-module-id="{module_id}" data-claim-ids="{claims}" data-layout="{layout}">
      <div class="module-copy">
        <p class="module-role">{role}</p>
        <!-- headline/body는 승인된 content-plan에서 온 편집 가능한 네이티브 HTML 텍스트입니다. -->
        <h2 class="module-headline" data-editable-field="headline">{headline}</h2>
        <p class="module-body" data-editable-field="body">{body}</p>
      </div>
      <figure class="module-media">
        {media}
      </figure>
    </section>'''
        )
    project_id = html.escape(str(content.get("project_id", "")), quote=True)
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{project_id} 상세페이지</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="detail-page" data-project-id="{project_id}">
{chr(10).join(sections)}
  </main>
</body>
</html>
'''


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    errors, content, asset_manifest, _ = validate_materials(project)
    for error in errors:
        LOGGER.error(error)
    if errors:
        LOGGER.error("hybrid assembly blocked by planning or material QA: errors=%d", len(errors))
        return 1

    output = project / "output"
    html_dir = output / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    html_path = html_dir / "detail-page.html"
    css_path = html_dir / "styles.css"
    html_path.write_text(build_html(content, asset_manifest), encoding="utf-8")
    css_path.write_text(CSS, encoding="utf-8")

    modules = sorted(content.get("modules", []), key=lambda item: int(item.get("order", 0)))
    package = {
        "schema_version": "1.0",
        "workflow_version": "5.3",
        "rendering_mode": "hybrid_html",
        "html": {"path": "output/html/detail-page.html", "sha256": sha256(html_path)},
        "stylesheet": {"path": "output/html/styles.css", "sha256": sha256(css_path)},
        "content_plan_sha256": sha256(project / CONTENT_PLAN_PATH),
        "asset_manifest_sha256": sha256(project / ASSET_MANIFEST_PATH),
        "material_qa_sha256": sha256(project / MATERIAL_QA_PATH),
        "modules": [
            {
                "id": str(module["id"]),
                "order": int(module["order"]),
                "asset_ids": [str(value) for value in module.get("asset_ids", [])],
                "editable_fields": [str(value) for value in module.get("editable_fields", [])],
            }
            for module in modules
        ],
    }
    package_path = html_dir / "package-manifest.json"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("hybrid detail page assembled: %s", html_path)
    LOGGER.info("integration QA is still required: output/qa/integration-qa.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
