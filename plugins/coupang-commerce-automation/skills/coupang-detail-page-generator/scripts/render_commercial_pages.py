#!/usr/bin/env python3
"""Render ten detail pages from approved generated page visuals and local copy."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from validate_campaign_assets import validate_campaign

LOGGER = logging.getLogger("render_commercial_pages")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render output/images/01.png..10.png from synthetic-safe generated visuals")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--spec", type=Path, help="Defaults to <project>/output/layout-spec.json")
    parser.add_argument("--output-dir", type=Path, help="Defaults to <project>/output/images")
    parser.add_argument("--pages", nargs="+", default=["all"], help="01 03 or all")
    parser.add_argument("--allow-internal-preview", action="store_true", help="Render a non-final preview even when generated-page gates fail")
    return parser.parse_args()


def page_selection(values: list[str]) -> set[str]:
    if any(value.casefold() == "all" for value in values):
        return {f"{index:02d}" for index in range(1, 11)}
    selected: set[str] = set()
    for value in values:
        if not value.isdigit() or not 1 <= int(value) <= 10:
            raise ValueError(f"페이지는 01~10 또는 all이어야 합니다: {value}")
        selected.add(f"{int(value):02d}")
    return selected


def rgba(value: str, alpha: int | None = None) -> tuple[int, int, int, int]:
    from PIL import ImageColor

    color = ImageColor.getcolor(value, "RGBA")
    if alpha is None:
        return color
    return color[0], color[1], color[2], alpha


def resolve(project: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project / path
    return path.resolve()


def load_font(fonts: dict[str, Any], role: str, size: int):
    from PIL import ImageFont

    if role not in fonts:
        raise KeyError(f"font role 누락: {role}")
    definition = fonts[role]
    path = Path(definition["path"]).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"폰트 파일 누락: {path}")
    font = ImageFont.truetype(str(path), size=size)
    variation = definition.get("variation")
    if variation and hasattr(font, "set_variation_by_name"):
        try:
            font.set_variation_by_name(str(variation).encode("ascii"))
        except Exception:
            LOGGER.warning("가변 폰트 variation 적용 실패: %s / %s", path.name, variation)
    return font


def wrap_paragraph(draw, text: str, font, max_width: int) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = []
    base_offset = 0
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append(("", base_offset))
            base_offset += 1
            continue
        current = ""
        current_start = base_offset
        for index, char in enumerate(paragraph):
            candidate = current + char
            width = draw.textbbox((0, 0), candidate, font=font)[2]
            if current and width > max_width:
                lines.append((current.rstrip(), current_start))
                current = char
                current_start = base_offset + index
            else:
                current = candidate
        if current:
            lines.append((current.rstrip(), current_start))
        base_offset += len(paragraph) + 1
    return lines


def draw_text(canvas, draw, element: dict[str, Any], fonts: dict[str, Any]) -> None:
    x, y, width, height = map(int, element["box"])
    font = load_font(fonts, element.get("font", "body"), int(element["size"]))
    lines = wrap_paragraph(draw, str(element["text"]), font, width)
    line_height = int(element.get("line_height", 1.15) * int(element["size"]))
    total_height = line_height * len(lines)
    valign = element.get("valign", "top")
    if valign == "center":
        cursor_y = y + max(0, (height - total_height) // 2)
    elif valign == "bottom":
        cursor_y = y + max(0, height - total_height)
    else:
        cursor_y = y
    align = element.get("align", "left")
    fill = rgba(element.get("color", "#161616"))
    full_text = str(element["text"])
    highlight = str(element.get("highlight", ""))
    highlight_start = full_text.find(highlight) if highlight else -1
    highlight_end = highlight_start + len(highlight) if highlight_start >= 0 else -1
    highlight_fill = rgba(element.get("highlight_color", element.get("color", "#161616")))
    shadow = element.get("shadow")
    for line, line_start in lines:
        box = draw.textbbox((0, 0), line, font=font)
        text_width = box[2] - box[0]
        if align == "center":
            cursor_x = x + (width - text_width) / 2
        elif align == "right":
            cursor_x = x + width - text_width
        else:
            cursor_x = x
        if shadow:
            offset = shadow.get("offset", [4, 4])
            draw.text((cursor_x + offset[0], cursor_y + offset[1]), line, font=font, fill=rgba(shadow.get("color", "#A8C6E8")))
        line_end = line_start + len(line)
        overlap_start = max(line_start, highlight_start)
        overlap_end = min(line_end, highlight_end)
        if highlight_start >= 0 and overlap_start < overlap_end:
            local_start = overlap_start - line_start
            local_end = overlap_end - line_start
            runs = [
                (line[:local_start], fill),
                (line[local_start:local_end], highlight_fill),
                (line[local_end:], fill),
            ]
            run_x = cursor_x
            for run, run_fill in runs:
                if not run:
                    continue
                draw.text((run_x, cursor_y), run, font=font, fill=run_fill)
                run_box = draw.textbbox((0, 0), run, font=font)
                run_x += run_box[2] - run_box[0]
        else:
            draw.text((cursor_x, cursor_y), line, font=font, fill=fill)
        cursor_y += line_height


def rounded_mask(size: tuple[int, int], radius: int, circle: bool = False):
    from PIL import Image, ImageDraw

    mask = Image.new("L", size, 0)
    mask_draw = ImageDraw.Draw(mask)
    if circle:
        mask_draw.ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)
    else:
        mask_draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def draw_image(canvas, draw, element: dict[str, Any], project: Path) -> None:
    from PIL import Image, ImageChops, ImageOps

    x, y, width, height = map(int, element["box"])
    path = resolve(project, element["path"])
    if not path.is_file():
        raise FileNotFoundError(f"이미지 파일 누락: {path}")
    with Image.open(path) as opened:
        source = opened.convert("RGBA")
    crop = element.get("crop")
    if crop:
        source = source.crop(tuple(map(int, crop)))
    fit = element.get("fit", "cover")
    focal = tuple(element.get("focal", [0.5, 0.5]))
    if fit == "contain":
        contained = ImageOps.contain(source, (width, height), method=Image.Resampling.LANCZOS)
        tile = Image.new("RGBA", (width, height), rgba(element.get("fill", "#FFFFFF00")))
        tile.alpha_composite(contained, ((width - contained.width) // 2, (height - contained.height) // 2))
    else:
        tile = ImageOps.fit(source, (width, height), method=Image.Resampling.LANCZOS, centering=focal)
    radius = int(element.get("radius", 0))
    circle = element.get("mask") == "circle"
    mask = rounded_mask((width, height), radius, circle) if (radius or circle) else tile.getchannel("A")
    if radius or circle:
        mask = ImageChops.multiply(mask, tile.getchannel("A"))
    if radius or circle:
        clipped = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        clipped.paste(tile, (0, 0), mask)
        canvas.paste(clipped, (x, y), clipped)
    else:
        canvas.alpha_composite(tile, (x, y), (0, 0, width, height))
    border = element.get("border")
    if border:
        border_width = int(border.get("width", 2))
        color = rgba(border.get("color", "#FFFFFF"))
        if circle:
            draw.ellipse((x, y, x + width, y + height), outline=color, width=border_width)
        else:
            draw.rounded_rectangle((x, y, x + width, y + height), radius=radius, outline=color, width=border_width)


def draw_badge(draw, element: dict[str, Any], fonts: dict[str, Any]) -> None:
    x, y, width, height = map(int, element["box"])
    radius = int(element.get("radius", height // 2))
    fill = rgba(element.get("fill", "#FFFFFF"))
    outline = rgba(element.get("outline", "#161616"))
    outline_width = int(element.get("outline_width", 2))
    shape = element.get("shape", "rounded")
    if shape == "circle":
        draw.ellipse((x, y, x + width, y + height), fill=fill, outline=outline, width=outline_width)
    else:
        draw.rounded_rectangle((x, y, x + width, y + height), radius=radius, fill=fill, outline=outline, width=outline_width)
    font = load_font(fonts, element.get("font", "badge"), int(element["size"]))
    text = str(element["text"])
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    draw.text((x + (width - text_width) / 2, y + (height - text_height) / 2 - box[1]), text, font=font, fill=rgba(element.get("color", "#161616")))


def render_element(canvas, draw, element: dict[str, Any], project: Path, fonts: dict[str, Any]) -> None:
    kind = element["type"]
    if kind == "image":
        draw_image(canvas, draw, element, project)
    elif kind == "text":
        draw_text(canvas, draw, element, fonts)
    elif kind == "badge":
        draw_badge(draw, element, fonts)
    elif kind == "rect":
        x, y, width, height = map(int, element["box"])
        draw.rounded_rectangle((x, y, x + width, y + height), radius=int(element.get("radius", 0)), fill=rgba(element.get("fill", "#FFFFFF")), outline=rgba(element["outline"]) if element.get("outline") else None, width=int(element.get("outline_width", 1)))
    elif kind == "ellipse":
        x, y, width, height = map(int, element["box"])
        draw.ellipse((x, y, x + width, y + height), fill=rgba(element.get("fill", "#FFFFFF")), outline=rgba(element["outline"]) if element.get("outline") else None, width=int(element.get("outline_width", 1)))
    elif kind == "line":
        points = [tuple(map(int, point)) for point in element["points"]]
        draw.line(points, fill=rgba(element.get("color", "#161616")), width=int(element.get("width", 3)), joint="curve")
    else:
        raise ValueError(f"지원하지 않는 element type: {kind}")


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        LOGGER.error("Pillow가 필요합니다: python -m pip install Pillow")
        return 2
    project = args.project.expanduser().resolve()
    spec_path = (args.spec or project / "output" / "layout-spec.json").expanduser().resolve()
    output_dir = (args.output_dir or project / "output" / "images").expanduser().resolve()
    try:
        campaign_errors, campaign_warnings, _ = validate_campaign(project, queue_only=False)
        gate_errors = list(campaign_errors)
        gate_errors.extend(campaign_warnings)
        if gate_errors and not args.allow_internal_preview:
            raise ValueError("final rendering blocked: " + "; ".join(gate_errors))
        if gate_errors:
            LOGGER.warning("internal preview only; final validation will fail: %s", "; ".join(gate_errors))
        selected = page_selection(args.pages)
        spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        canvas_spec = spec["canvas"]
        width = int(canvas_spec.get("width", 780))
        min_height = int(canvas_spec.get("min_height", 1200))
        max_height = int(canvas_spec.get("max_height", 1800))
        fonts = spec["fonts"]
        pages = spec["pages"]
        expected = [f"{index:02d}" for index in range(1, 11)]
        actual = [str(page["page"]).zfill(2) for page in pages]
        if actual != expected:
            raise ValueError(f"페이지는 01~10 순서여야 합니다: {actual}")
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_pages: list[dict[str, Any]] = []
        for page in pages:
            page_id = str(page["page"]).zfill(2)
            height = int(page["height"])
            if not min_height <= height <= max_height:
                raise ValueError(f"{page_id}: 높이 {height}가 {min_height}~{max_height} 범위를 벗어남")
            elements = page.get("elements", [])
            if page_id in selected:
                canvas = Image.new("RGBA", (width, height), rgba(page.get("background", "#F6F1E8")))
                draw = ImageDraw.Draw(canvas, "RGBA")
                for element in elements:
                    render_element(canvas, draw, element, project, fonts)
                target = output_dir / f"{page_id}.png"
                canvas.convert("RGB").save(target, format="PNG", optimize=True)
                LOGGER.info("렌더링: %s (%dx%d)", target, width, height)
            bounds = []
            source_kind_counts = {kind: 0 for kind in ("generated_page", "raw_product_only", "decorative", "unknown")}
            asset_ids: set[str] = set()
            visual_area = 0
            typography_roles: set[str] = set()
            for element in elements:
                if element.get("counts_as_content", True) and "box" in element:
                    _, y, _, element_height = map(int, element["box"])
                    bounds.append((y, y + element_height))
                if element.get("type") == "image":
                    source_kind = element.get("source_kind") or ("raw" if str(element.get("path", "")).replace("\\", "/").startswith("raw/") else "unknown")
                    if source_kind not in source_kind_counts:
                        source_kind = "unknown"
                    source_kind_counts[source_kind] += 1
                    if element.get("asset_id"):
                        asset_ids.add(str(element["asset_id"]))
                if "box" in element and (element.get("type") == "image" or element.get("visual_weight", False)):
                    _, _, element_width, element_height = map(int, element["box"])
                    visual_area += element_width * element_height
                if element.get("type") in {"text", "badge"}:
                    typography_roles.add(element.get("font", "body"))
            if bounds:
                content_span = max(end for _, end in bounds) - min(start for start, _ in bounds)
                first_content_y = min(start for start, _ in bounds)
            else:
                content_span = 0
                first_content_y = height
            manifest_pages.append({
                "page": page_id,
                "file": f"output/images/{page_id}.png",
                "size": [width, height],
                "layout": page.get("layout"),
                "role": page.get("role"),
                "purchase_reason": page.get("purchase_reason"),
                "content_span_ratio": round(content_span / height, 4),
                "first_content_y": first_content_y,
                "raw_product_only_image_count": source_kind_counts["raw_product_only"],
                "generated_image_count": source_kind_counts["generated_page"],
                "source_kind_counts": source_kind_counts,
                "asset_ids": sorted(asset_ids),
                "visual_area_ratio": round(min(visual_area / (width * height), 1.0), 4),
                "typography_roles": sorted(typography_roles),
            })
        manifest = {"version": spec.get("version", "2.0"), "pages": manifest_pages}
        manifest_path = project / "output" / "render-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("렌더 매니페스트: %s", manifest_path)
    except Exception as exc:
        LOGGER.exception("상업 상세페이지 렌더링 실패: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
