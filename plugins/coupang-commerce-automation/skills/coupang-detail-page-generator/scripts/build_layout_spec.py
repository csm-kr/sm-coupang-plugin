#!/usr/bin/env python3
"""Build a varied ten-page local-typography layout from approved PG visuals."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

LOGGER = logging.getLogger("build_layout_spec")
ROLES = [
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
LAYOUTS = [
    "hero_full",
    "studio_flatlay",
    "two_card_context",
    "full_plus_inset",
    "macro_focus",
    "macro_grid",
    "lifestyle_full",
    "four_panel_mosaic",
    "spec_cards",
    "closing_split",
]
HEIGHTS = [1650, 1550, 1600, 1600, 1550, 1550, 1600, 1700, 1600, 1650]
IMAGE_BOXES = [
    [0, 0, 780, 1250],
    [40, 340, 700, 1040],
    [0, 0, 780, 1360],
    [260, 0, 520, 1500],
    [0, 280, 780, 1180],
    [40, 350, 700, 1050],
    [0, 0, 780, 1350],
    [30, 320, 720, 1260],
    [40, 330, 700, 1050],
    [0, 0, 780, 1280],
]
TEXT_PLACEMENTS = ["bottom", "top", "top_card", "left", "top", "top", "top_card", "top", "top", "bottom"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build layout-spec.json for PG-01..PG-10")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--copy", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def parse_copy(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    current = ""
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        heading = re.match(r"^##\s+(\d{1,2})\s*$", line.strip())
        if heading:
            current = f"{int(heading.group(1)):02d}"
            result[current] = {}
            continue
        if current:
            field = re.match(r"^-\s*([a-z_]+)\s*:\s*(.*)$", line.strip(), re.IGNORECASE)
            if field:
                result[current][field.group(1).casefold()] = field.group(2).strip()
    return result


def text_elements(page: str, values: dict[str, str], placement: str, height: int) -> list[dict]:
    headline = values.get("headline", f"페이지 {page}")
    subcopy = values.get("subcopy", "")
    badge = values.get("badge", "")
    emphasis = values.get("emphasis", "")
    alignment = values.get("headline_alignment", "center")
    dark_panel = page in {"03", "10"}
    panel_fill = "#145DA0F2" if dark_panel else "#FDFBF7F5"
    panel_outline = "#145DA0" if dark_panel else "#C9E0F5"
    headline_color = "#FFFFFF" if dark_panel else "#102F55"
    body_color = "#EEF6FF" if dark_panel else "#303946"
    highlight_color = "#FFD34E" if dark_panel else "#2678C9"
    elements: list[dict] = []
    if placement == "bottom":
        card = [28, height - 535, 724, 480]
        badge_box = [68, height - 485, 200, 48]
        headline_box = [68, height - 405, 644, 190]
        body_box = [68, height - 190, 644, 90]
    elif placement == "left":
        card = [24, 90, 446, 560]
        badge_box = [58, 140, 180, 46]
        headline_box = [58, 220, 378, 230]
        body_box = [58, 485, 378, 120]
    elif placement == "top_card":
        card = [28, 32, 724, 410]
        badge_box = [68, 76, 190, 46]
        headline_box = [68, 148, 644, 160]
        body_box = [68, 330, 644, 74]
    else:
        card = [28, 28, 724, 360]
        badge_box = [68, 68, 190, 46]
        headline_box = [68, 138, 644, 150]
        body_box = [68, 305, 644, 65]
    elements.append(
        {
            "type": "rect",
            "box": card,
            "fill": panel_fill,
            "radius": 30,
            "outline": panel_outline,
            "outline_width": 2,
        }
    )
    if badge:
        elements.append(
            {
                "type": "badge",
                "box": badge_box,
                "text": badge,
                "font": "badge",
                "size": 22,
                "fill": "#FFFFFF" if dark_panel else "#DCECFB",
                "outline": "#FFFFFF" if dark_panel else "#DCECFB",
                "color": "#145DA0" if dark_panel else "#245F98",
                "radius": 22,
            }
        )
    elements.append(
        {
            "type": "text",
            "box": headline_box,
            "text": headline,
            "font": "hook" if page == "01" else "title",
            "size": 82 if page == "01" else (62 if placement == "left" else 68),
            "line_height": 1.02,
            "color": headline_color,
            "highlight": emphasis,
            "highlight_color": highlight_color,
            "align": alignment,
        }
    )
    if subcopy:
        elements.append(
            {
                "type": "text",
                "box": body_box,
                "text": subcopy,
                "font": "body",
                "size": 28 if placement != "left" else 26,
                "line_height": 1.35,
                "color": body_color,
                "align": alignment,
            }
        )
    return elements


def scale_elements(elements: list[dict], scale_x: float, scale_y: float) -> list[dict]:
    for element in elements:
        if isinstance(element.get("box"), list) and len(element["box"]) == 4:
            x, y, width, height = element["box"]
            element["box"] = [
                round(x * scale_x),
                round(y * scale_y),
                round(width * scale_x),
                round(height * scale_y),
            ]
        for field in ("size", "radius", "outline_width"):
            if isinstance(element.get(field), (int, float)):
                element[field] = max(1, round(element[field] * scale_x))
    return elements


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    copy_path = (args.copy or project / "output" / "copy" / "overlay-copy.md").expanduser().resolve()
    output_path = (args.output or project / "output" / "layout-spec.json").expanduser().resolve()
    if output_path.exists() and not args.force:
        LOGGER.error("existing layout preserved; use --force to replace")
        return 2
    if not copy_path.is_file():
        LOGGER.error("overlay copy missing: %s", copy_path)
        return 2
    copy = parse_copy(copy_path)
    if sorted(copy) != [f"{index:02d}" for index in range(1, 11)]:
        LOGGER.error("overlay copy must contain sections 01..10")
        return 2
    workflow_version = "legacy"
    canvas = {"width": 780, "min_height": 1350, "max_height": 1800}
    manifest_path = project / "output" / "project-manifest.yaml"
    if manifest_path.is_file():
        if yaml is None:
            LOGGER.error("PyYAML is required to read the project canvas")
            return 2
        try:
            project_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig")) or {}
            workflow_version = str(project_manifest.get("workflow_version", "5.0"))
            canvas = project_manifest.get("project", {}).get("canvas", canvas)
        except Exception as exc:
            LOGGER.error("project manifest parse failed: %s", exc)
            return 2
    target_width = int(canvas.get("width", 780))
    fixed_height = int(canvas["height"]) if canvas.get("height") is not None else None
    if workflow_version == "5.2":
        LOGGER.error("workflow 5.2 forbids local typography fallback; use ImageGen targeted text edits up to three times")
        return 2
    if workflow_version in {"5.1", "5.2"} and (target_width != 800 or fixed_height != 2400):
        LOGGER.error("workflow 5.1+ local fallback requires an 800x2400 canvas")
        return 2
    pages = []
    for index in range(10):
        page = f"{index + 1:02d}"
        asset_id = f"PG-{page}"
        image = {
            "type": "image",
            "path": f"output/generated-pages/{asset_id}.png",
            "asset_id": asset_id,
            "source_kind": "generated_page",
            "box": IMAGE_BOXES[index],
            "fit": "cover",
            "focal": [0.5, 0.45],
            "radius": 0 if index in {0, 2, 6, 9} else 28,
        }
        base_height = HEIGHTS[index]
        page_height = fixed_height or base_height
        elements = [image]
        elements.extend(text_elements(page, copy[page], TEXT_PLACEMENTS[index], base_height))
        elements = scale_elements(elements, target_width / 780, page_height / base_height)
        pages.append(
            {
                "page": page,
                "role": ROLES[index],
                "height": page_height,
                "background": "#FAF8F2",
                "layout": LAYOUTS[index],
                "purchase_reason": copy[page].get("headline", ""),
                "asset_ids": [asset_id],
                "elements": elements,
            }
        )
    spec = {
        "version": workflow_version if workflow_version in {"5.1", "5.2"} else "4.1",
        "canvas": canvas,
        "fonts": {
            "hook": {"path": "C:/Windows/Fonts/NotoSansKR-VF.ttf", "variation": "Black"},
            "title": {"path": "C:/Windows/Fonts/NotoSansKR-VF.ttf", "variation": "Black"},
            "body": {"path": "C:/Windows/Fonts/NotoSansKR-VF.ttf", "variation": "Regular"},
            "badge": {"path": "C:/Windows/Fonts/arialbd.ttf"},
        },
        "pages": pages,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("varied ten-page layout created: %s", output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
