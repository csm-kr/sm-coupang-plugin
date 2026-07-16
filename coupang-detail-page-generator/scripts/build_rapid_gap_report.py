#!/usr/bin/env python3
"""Create a fast reference-vs-current visual gap brief before generation."""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

LOGGER = logging.getLogger("build_rapid_gap_report")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a rapid visual improvement brief")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--current-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def resolve(project: Path, value: Path) -> Path:
    value = value.expanduser()
    return value.resolve() if value.is_absolute() else (project / value).resolve()


def image_metrics(image: Image.Image) -> dict[str, float]:
    rgb = image.convert("RGB")
    width = min(256, rgb.width)
    height = max(1, round(rgb.height * width / max(1, rgb.width)))
    height = min(4096, height)
    sample = rgb.resize((width, height), Image.Resampling.BILINEAR)
    gray = sample.convert("L")
    histogram = gray.histogram()
    total = max(1, sum(histogram))
    bright_ratio = sum(histogram[236:]) / total
    dark_ratio = sum(histogram[:80]) / total
    saturation = ImageStat.Stat(sample.convert("HSV").getchannel("S")).mean[0] / 255
    edge = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0] / 255
    return {
        "bright_ratio": round(bright_ratio, 4),
        "dark_ratio": round(dark_ratio, 4),
        "saturation": round(saturation, 4),
        "edge_density": round(edge, 4),
    }


def reference_metrics(path: Path) -> tuple[dict[str, float], tuple[int, int]]:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        size = image.size
        metrics = []
        for index in range(10):
            top = round(image.height * index / 10)
            bottom = round(image.height * (index + 1) / 10)
            metrics.append(image_metrics(image.crop((0, top, image.width, bottom))))
    return average_metrics(metrics), size


def average_metrics(values: list[dict[str, float]]) -> dict[str, float]:
    if not values:
        return {"bright_ratio": 0.0, "dark_ratio": 0.0, "saturation": 0.0, "edge_density": 0.0}
    return {key: round(statistics.mean(item[key] for item in values), 4) for key in values[0]}


def current_metrics(directory: Path | None) -> tuple[dict[str, float] | None, list[Path], list[tuple[int, int]]]:
    if directory is None or not directory.is_dir():
        return None, [], []
    paths = sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES)
    metrics = []
    sizes = []
    for path in paths[:20]:
        try:
            with Image.open(path) as image:
                sizes.append(image.size)
                metrics.append(image_metrics(image))
        except Exception:
            LOGGER.warning("skipped unreadable current image: %s", path)
    return (average_metrics(metrics) if metrics else None), paths, sizes


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def choose_current(project: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return resolve(project, explicit)
    for candidate in (
        project / "output" / "images",
        project / "output" / "preview-images",
        project / "project3" / "output" / "preview-images",
    ):
        if candidate.is_dir() and any(path.suffix.casefold() in IMAGE_SUFFIXES for path in candidate.iterdir() if path.is_file()):
            return candidate
    return None


def build_priorities(reference: dict[str, float], current: dict[str, float] | None, count: int) -> list[tuple[str, str, str]]:
    priorities: list[tuple[str, str, str]] = [
        ("첫 화면 상업 훅 강화", "예쁜 사진만으로는 상품·상황·구매 이유가 1초 안에 연결되지 않음", "01에 질문 또는 상황, 큰 상품, 72~92px Black 헤드라인과 강조 구절 하나를 결합"),
        ("주장-증거 전환 흐름 잠금", "룩북형 장면 반복은 구매 이유를 누적시키지 못함", "03~09를 선택 기준 → 구조·디테일·마감 증거 → 사용/저항 해소 → 구매정보 순으로 연결"),
    ]
    if current is not None:
        if current["bright_ratio"] - reference["bright_ratio"] > 0.08:
            priorities.append(("미완성처럼 보이는 공백 축소", "현재 결과의 밝은 빈 영역 비율이 레퍼런스보다 높음", "02·06·09의 제품 매크로와 정보 카드를 키우고 화면 하단까지 콘텐츠 연결"))
        if reference["edge_density"] - current["edge_density"] > 0.015:
            priorities.append(("제품 디테일 밀도 강화", "레퍼런스보다 윤곽·디테일 변화가 적음", "04·05·06에 전체형, 확대 원형, 봉제·라벨 매크로를 교차 배치"))
        if abs(reference["saturation"] - current["saturation"]) > 0.06:
            priorities.append(("팔레트 통일", "현재 결과와 레퍼런스의 평균 채도 차이가 큼", "화이트·아이보리·파우더 블루·연한 식물색으로 색 범위를 잠금"))
    if count and count != 10:
        priorities.append(("산출물 수를 10장으로 고정", f"현재 비교 이미지가 {count}장", "PG-01~PG-10을 페이지와 1:1 대응하고 누락·중복 금지"))
    defaults = [
        ("실제 인물 픽셀 완전 제거", "기존 보존 편집은 실제 착용자 얼굴·피부·신체를 남길 수 있음", "사람 포함 원본은 모든 생성 입력에서 제외하고, 모든 인물은 PG-01의 텍스트 기반 합성 모델로 생성"),
        ("상업형 타이포 위계 강화", "레퍼런스의 굵은 질문형 제목, 핵심어 컬러 강조, 번호·카드 라벨 체계가 전환 리듬을 만듦", "히어로 72~92px, 섹션 58~76px, Black 제목, 강조 구절 1개, 좌측/중앙축 변주를 01~10에 잠금"),
        ("사진·정보 밀도 강화", "완성 레퍼런스는 섹션 하단까지 사진·카드·다음 장면이 이어져 미완성 공백이 거의 없음", "02·06·09의 제품 크기와 정보 카드를 키우고 모든 페이지 콘텐츠를 하단 85%까지 연결"),
        ("제품 증명 디테일 확대", "완성 레퍼런스는 제품 전체, 착용 실루엣, 핵심부, 원단, 봉제, 라벨을 서로 다른 크기로 반복 확인시킴", "04·05·06에 전체형·원형 확대·매크로를 분리하고 같은 사진의 단순 크롭 반복 금지"),
        ("장면 리듬 확대", "레퍼런스는 히어로·플랫레이·착용·매크로·모자이크가 짧게 교차함", "01·03·07·10 인물 장면 사이에 02·05·06·09 제품 중심 장면 배치"),
        ("타이포 위계와 사진의 연결", "레퍼런스는 큰 Black 제목, 핵심어 강조, 짧은 설명, 번호·카드 순서가 명확함", "무문자 비주얼을 조건 이미지로 다시 넣고 모델이 실제 여백에 제목·설명·라벨·단계를 강한 대비로 통합"),
    ]
    for item in defaults:
        if item[0] not in {value[0] for value in priorities}:
            priorities.append(item)
        if len(priorities) == 5:
            break
    return priorities[:5]


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    reference = resolve(project, args.reference)
    if not reference.is_file():
        LOGGER.error("reference image missing: %s", reference)
        return 2
    current_dir = choose_current(project, args.current_dir)
    output = resolve(project, args.output) if args.output else project / "output" / "rapid-improvement-brief.md"
    ref_metrics, ref_size = reference_metrics(reference)
    cur_metrics, current_paths, current_sizes = current_metrics(current_dir)
    priorities = build_priorities(ref_metrics, cur_metrics, len(current_paths))
    metrics_payload = {"reference": ref_metrics, "current": cur_metrics, "current_count": len(current_paths)}
    lines = [
        "# 빠른 개선 브리프",
        "",
        f"- 기준 레퍼런스: `{reference.name}` ({ref_size[0]}×{ref_size[1]})",
        f"- 현재 결과: `{current_dir}` ({len(current_paths)}장)" if current_dir else "- 현재 결과: 없음 — 레퍼런스 목표만 추출",
        "- 인물 정책: 실제 인물 픽셀 0건, 모든 인물은 합성 모델",
        "",
        "## 우선 개선점 5개",
        "",
        "| 우선 | 개선점 | 빠른 근거 | 10장 적용 |",
        "|---:|---|---|---|",
    ]
    for index, (title, reason, action) in enumerate(priorities, start=1):
        lines.append(f"| {index} | {title} | {reason} | {action} |")
    lines.extend(
        [
            "",
            "## 자동 시각 지표",
            "",
            "| 항목 | 레퍼런스 | 현재 결과 | 해석 |",
            "|---|---:|---:|---|",
            f"| 밝은 영역 비율 | {percent(ref_metrics['bright_ratio'])} | {percent(cur_metrics['bright_ratio']) if cur_metrics else '—'} | 높을수록 화이트·여백이 많음 |",
            f"| 어두운 영역 비율 | {percent(ref_metrics['dark_ratio'])} | {percent(cur_metrics['dark_ratio']) if cur_metrics else '—'} | 제목·윤곽·대비 밀도 참고 |",
            f"| 평균 채도 | {percent(ref_metrics['saturation'])} | {percent(cur_metrics['saturation']) if cur_metrics else '—'} | 팔레트 강도 참고 |",
            f"| 윤곽 밀도 | {percent(ref_metrics['edge_density'])} | {percent(cur_metrics['edge_density']) if cur_metrics else '—'} | 사진·카드·디테일 변화량 참고 |",
            "",
            "자동 지표는 진단 보조값이다. 제품 의미, 실제 사람 사용 여부, 카피 적합성은 반드시 시각 검토한다.",
            "",
            "## 가져올 시각 원리",
            "",
            "- 밝은 창가 자연광과 화이트·아이보리·파우더 블루 팔레트",
            "- 72~92px Black 히어로 제목, 58~76px 섹션 제목, 핵심어 한 구절의 고대비 강조",
            "- 훅 → 선택 기준 → 해결 → 구조·디테일·마감 증거 → 사용/저항 해소 → 구매정보 → 요약 리듬",
            "- 전면 사진, 2열 비교, 원형 확대, 단계 번호, 다장면 모자이크, 정보표의 교차",
            "- 페이지 하단이 다음 장면으로 자연스럽게 이어지는 연속감",
            "",
            "## 가져오지 않을 요소",
            "",
            "- 레퍼런스 인물 얼굴·정체성·신체 픽셀",
            "- 브랜드·로고·제품 외형·라벨·카피",
            "- 근거 없는 기능·소재·수치·추천 대상·비교 주장",
            "- 레퍼런스의 동일 구도와 문구를 그대로 복제한 페이지",
            "",
            "## 페이지별 적용 잠금",
            "",
            "- 01·03·04·05·07·08·10: PG-01 기반 동일 합성 모델만 사용",
            "- 02·06·09: 사람·피부·손·팔이 없는 제품 중심 장면",
            "- 04·05·06: 제품 형태 검증용 전체형·핵심부·원단 매크로 분리",
            "- 08: 서로 다른 4개 상황을 한 장의 모자이크로 구성",
            "- 09: 검증된 사실만 조건부 타이포 패스로 합성",
            "",
            "<!-- machine-metrics " + json.dumps(metrics_payload, ensure_ascii=False) + " -->",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOGGER.info("rapid improvement brief created: %s", output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
