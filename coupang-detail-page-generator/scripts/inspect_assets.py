#!/usr/bin/env python3
"""Recursively inventory raw/ and reference/ without inventing product facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

LOGGER = logging.getLogger("inspect_assets")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic", ".heif"}
TEXT_EXTS = {".txt", ".md", ".json", ".csv", ".tsv", ".yaml", ".yml"}
DOCUMENT_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
FONT_EXTS = {".ttf", ".otf", ".woff", ".woff2"}
SUPPORTED_EXTS = IMAGE_EXTS | TEXT_EXTS | DOCUMENT_EXTS | FONT_EXTS

RAW_RULES = [
    ("product_front", ("front", "정면", "앞면")),
    ("product_back", ("back", "후면", "뒷면")),
    ("product_side", ("side", "측면")),
    ("product_top", ("top", "상단", "윗면")),
    ("product_bottom", ("bottom", "하단", "밑면")),
    ("product_detail", ("detail", "closeup", "macro", "디테일", "상세", "접사")),
    ("product_in_use", ("use", "wear", "lifestyle", "사용", "착용", "연출")),
    ("product_components", ("component", "contents", "구성품", "구성")),
    ("product_package", ("package", "packaging", "box", "패키지", "포장")),
    ("brand_logo", ("logo", "brand", "로고", "브랜드")),
    ("size_chart", ("size", "dimension", "사이즈", "치수")),
    ("manual", ("manual", "instruction", "guide", "설명서", "사용법")),
    ("certificate", ("certificate", "cert", "인증서", "인증")),
    ("test_report", ("test", "report", "시험", "성적서")),
    ("product_information", ("info", "spec", "description", "상품정보", "제품정보", "스펙")),
    ("product_main", ("main", "hero", "대표", "메인")),
]

REFERENCE_RULES = [
    ("competitor", ("competitor", "coupang", "경쟁", "쿠팡")),
    ("layout", ("layout", "레이아웃")),
    ("color_palette", ("color", "palette", "색감", "컬러")),
    ("lighting", ("light", "lighting", "조명")),
    ("photography", ("photo", "shot", "구도", "촬영")),
    ("typography_hierarchy", ("type", "font", "typography", "타이포", "폰트")),
    ("card_design", ("card", "카드")),
    ("detail_closeup", ("detail", "closeup", "디테일", "접사")),
    ("lifestyle_scene", ("lifestyle", "scene", "사용장면", "라이프")),
    ("page_flow", ("flow", "sequence", "흐름", "순서")),
]


@dataclass
class Asset:
    name: str
    location: str
    category: str
    production_role: str
    information: str
    quality: str
    usage: str
    digest: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect raw/ and reference/ assets and write output/asset-inventory.md")
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="Project root containing raw/ and reference/")
    parser.add_argument("--output", type=Path, help="Inventory output path; defaults to <project>/output/asset-inventory.md")
    parser.add_argument("--low-res-short-edge", type=int, default=780, help="Warn when an image short edge is below this value")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_raw(path: Path) -> str:
    normalized = path.stem.casefold().replace("-", "_").replace(" ", "_")
    for category, tokens in RAW_RULES:
        if any(token.casefold() in normalized for token in tokens):
            return category
    if path.suffix.casefold() in IMAGE_EXTS:
        return "unknown"
    if path.suffix.casefold() in TEXT_EXTS | DOCUMENT_EXTS:
        return "product_information"
    return "unknown"


def classify_reference(path: Path) -> str:
    normalized = path.stem.casefold().replace("-", "_").replace(" ", "_")
    matches = [category for category, tokens in REFERENCE_RULES if any(token.casefold() in normalized for token in tokens)]
    return ", ".join(matches) if matches else "design_reference_unknown"


def inspect_image(path: Path, low_res_short_edge: int) -> tuple[str, str]:
    try:
        from PIL import Image
    except ImportError:
        return "이미지 파일; Pillow 미설치로 해상도 미확인", "제한 검사"

    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode
        ratio = width / height if height else 0
        info = f"{width}×{height}px, 비율 {ratio:.3f}, 모드 {mode}; 시각 의미는 후속 확인 필요"
        quality = "정상"
        if min(width, height) < low_res_short_edge:
            quality = f"저해상도 경고(짧은 변 {min(width, height)}px)"
        return info, quality
    except Exception as exc:  # Pillow raises format-specific exceptions.
        return f"이미지 읽기 실패: {exc}", "손상 또는 미지원 이미지"


def inspect_text(path: Path) -> tuple[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="cp949")
        except Exception as exc:
            return f"텍스트 디코딩 실패: {exc}", "읽기 실패"
    except Exception as exc:
        return f"텍스트 읽기 실패: {exc}", "읽기 실패"

    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "빈 파일")
    first_line = re.sub(r"\s+", " ", first_line)[:100]
    if path.suffix.casefold() == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            return f"JSON 구문 오류({exc.lineno}:{exc.colno}); 첫 줄: {first_line}", "손상된 JSON"
    return f"텍스트 {len(text):,}자; 첫 내용: {first_line}", "정상"


def inspect_document(path: Path) -> tuple[str, str]:
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        try:
            with path.open("rb") as handle:
                signature = handle.read(5)
            if signature != b"%PDF-":
                return "PDF 시그니처 불일치", "손상 가능"
            try:
                from pypdf import PdfReader

                pages = len(PdfReader(str(path)).pages)
                return f"PDF {pages}페이지; 내용은 PDF 도구로 후속 확인 필요", "정상"
            except ImportError:
                return "PDF 시그니처 정상; pypdf 미설치로 페이지 수 미확인", "제한 검사"
            except Exception as exc:
                return f"PDF 파싱 경고: {exc}", "손상 가능"
        except Exception as exc:
            return f"PDF 읽기 실패: {exc}", "읽기 실패"
    return f"{suffix[1:].upper()} 문서; 전용 문서 도구로 후속 확인 필요", "제한 검사"


def inspect_one(path: Path, root_name: str, project: Path, low_res_short_edge: int) -> Asset:
    suffix = path.suffix.casefold()
    relative = path.relative_to(project).as_posix()
    category = classify_raw(path) if root_name == "raw" else classify_reference(path)
    try:
        digest = sha256(path)
    except Exception as exc:
        LOGGER.error("해시 계산 실패: %s: %s", path, exc)
        digest = ""

    if suffix in IMAGE_EXTS:
        information, quality = inspect_image(path, low_res_short_edge)
    elif suffix in TEXT_EXTS:
        information, quality = inspect_text(path)
    elif suffix in DOCUMENT_EXTS:
        information, quality = inspect_document(path)
    elif suffix in FONT_EXTS:
        information, quality = "폰트 파일; 라이선스와 한국어 글리프 지원 후속 확인 필요", "제한 검사"
    else:
        information = f"지원하지 않는 형식: {suffix or '(확장자 없음)'}"
        quality = "지원 안 됨"

    if quality in {"읽기 실패", "손상 가능", "손상된 JSON", "손상 또는 미지원 이미지"}:
        usage = "사용 안 함; 원본 확인 필요"
    elif suffix not in SUPPORTED_EXTS:
        usage = "지원 안 됨; 수동 확인 필요"
    elif root_name == "reference":
        usage = "디자인 방향만 사용; 상품 사실 사용 금지"
    elif category == "unknown":
        usage = "검토 필요; 관련성과 분류를 시각 확인"
    else:
        usage = "후속 의미 분석 필요"

    if "generated" in path.stem.casefold() or "draft" in path.stem.casefold() or "시안" in path.stem:
        production_role = "GENERATED_DRAFT"
    elif root_name == "reference" and "competitor" in category:
        production_role = "COMPETITOR_REFERENCE"
    elif root_name == "reference":
        production_role = "STYLE_REFERENCE"
    elif category in {"size_chart", "certificate", "test_report"}:
        production_role = "MEASUREMENT_EVIDENCE"
    elif suffix in IMAGE_EXTS:
        production_role = "PRODUCT_SOURCE (시각·계보 확인 전 후보)"
    else:
        production_role = "SUPPLIER_REFERENCE"

    return Asset(path.name, relative, category, production_role, information, quality, usage, digest)


def escape_markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def build_inventory(project: Path, low_res_short_edge: int) -> tuple[list[Asset], list[str]]:
    assets: list[Asset] = []
    notes: list[str] = []
    for root_name in ("raw", "reference"):
        root = project / root_name
        if not root.exists():
            root.mkdir(parents=True, exist_ok=True)
            notes.append(f"`{root_name}/`가 없어 빈 폴더를 생성했습니다.")
        if not root.is_dir():
            raise NotADirectoryError(f"{root} is not a directory")
        files = sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix().casefold())
        if not files:
            notes.append(f"`{root_name}/`에 파일이 없습니다.")
        for path in files:
            LOGGER.info("검사: %s", path)
            assets.append(inspect_one(path, root_name, project, low_res_short_edge))

    by_digest: dict[str, list[Asset]] = {}
    for asset in assets:
        if asset.digest:
            by_digest.setdefault(asset.digest, []).append(asset)
    for group in by_digest.values():
        if len(group) > 1:
            locations = ", ".join(item.location for item in group)
            for item in group:
                item.quality = f"{item.quality}; 완전 중복"
                item.information = f"{item.information}; 중복 그룹: {locations}"
    return assets, notes


def render_markdown(assets: Iterable[Asset], notes: list[str], project: Path) -> str:
    lines = [
        "# Asset Inventory",
        "",
        f"- 프로젝트: `{project}`",
        "- 자동 분류는 파일명·형식 기반 초안이며, 상품 관련성과 시각 정보는 Codex가 직접 확인해야 합니다.",
    ]
    for note in notes:
        lines.append(f"- 경고: {note}")
    lines.extend(
        [
            "",
            "| 파일명 | 위치 | 자동 분류 | 제작 역할 | 확인 가능한 정보 | 품질 | 인물 포함 여부 | 최종 픽셀 합성 | 사용 여부 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for asset in assets:
        suffix = Path(asset.location).suffix.casefold()
        if asset.location.startswith("reference/"):
            person_status = "아트디렉션 참조만"
            composite_status = "금지"
        elif suffix in IMAGE_EXTS:
            person_status = "시각 판정 필요"
            composite_status = "사람 픽셀 없음 확인 전 금지"
        else:
            person_status = "해당 없음"
            composite_status = "이미지 합성 대상 아님"
        values = (
            asset.name,
            asset.location,
            asset.category,
            asset.production_role,
            asset.information,
            asset.quality,
            person_status,
            composite_status,
            asset.usage,
        )
        lines.append("| " + " | ".join(escape_markdown(value) for value in values) + " |")
    lines.extend(
        [
            "",
            "## 누락·후속 확인",
            "",
            "- [ ] 상품 정면, 후면, 측면, 상단, 하단, 디테일 유무를 시각 확인",
            "- [ ] 이미지별 확인 가능/확인 불가 정보 보완",
            "- [ ] 모든 raw 이미지에 product_only 또는 contains_person을 시각 판정",
            "- [ ] contains_person 이미지는 safe_for_final_composite=false로 잠금",
            "- [ ] 상품과 무관한 파일 표시",
            "- [ ] reference 유형과 적용 가능/금지 요소 보완",
            "- [ ] 모든 파일의 제작 역할을 PRODUCT_SOURCE / SUPPLIER_REFERENCE / COMPETITOR_REFERENCE / STYLE_REFERENCE / GENERATED_DRAFT / MEASUREMENT_EVIDENCE 중 하나로 확정",
            "- [ ] 지원하지 않는 형식의 수동 처리 여부 결정",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    if project.exists() and not project.is_dir():
        LOGGER.error("프로젝트 경로가 디렉터리가 아닙니다: %s", project)
        return 2
    project.mkdir(parents=True, exist_ok=True)
    output = (args.output or project / "output" / "asset-inventory.md").expanduser().resolve()
    try:
        assets, notes = build_inventory(project, args.low_res_short_edge)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(assets, notes, project), encoding="utf-8")
    except Exception as exc:
        LOGGER.exception("자산 검사 실패: %s", exc)
        return 1
    LOGGER.info("완료: %d개 파일 -> %s", len(assets), output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
