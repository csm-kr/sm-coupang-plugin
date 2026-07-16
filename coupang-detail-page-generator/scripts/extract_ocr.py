#!/usr/bin/env python3
"""Extract OCR text when available and compare it with expected page copy."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


NAME_PATTERN = re.compile(r"^(\d{2})(?:-.+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract OCR and flag expected-copy mismatches without treating OCR as ground truth")
    parser.add_argument("--images-dir", type=Path, required=True)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def normalized(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).casefold()


def load_expected(path: Path | None) -> dict[str, list[str]]:
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    pages = data.get("pages", data)
    if not isinstance(pages, dict):
        raise ValueError("expected copy JSON must contain a pages object")
    result: dict[str, list[str]] = {}
    for key, value in pages.items():
        page = f"{int(key):02d}" if str(key).isdigit() else str(key)
        if isinstance(value, str):
            result[page] = [value]
        elif isinstance(value, list):
            result[page] = [str(item) for item in value if str(item).strip()]
        else:
            raise ValueError(f"expected copy for {key} must be a string or array")
    return result


def detect_tesseract():
    try:
        import pytesseract

        version = str(pytesseract.get_tesseract_version())
        languages = set(pytesseract.get_languages(config=""))
        language = "kor+eng" if {"kor", "eng"}.issubset(languages) else "kor" if "kor" in languages else "eng" if "eng" in languages else ""
        if not language:
            return None, {"name": "tesseract", "available": False, "reason": "no usable language data"}
        return (pytesseract, language), {"name": "tesseract", "available": True, "version": version, "language": language}
    except Exception as exc:
        return None, {"name": "none", "available": False, "reason": str(exc)}


def collect_pages(root: Path) -> dict[str, Path]:
    pages: dict[str, Path] = {}
    for path in sorted((value for value in root.iterdir() if value.is_file() and not value.name.startswith(".")), key=lambda value: value.name.casefold()):
        match = NAME_PATTERN.fullmatch(path.stem)
        if match and match.group(1) not in pages:
            pages[match.group(1)] = path
    return pages


def main() -> int:
    args = parse_args()
    root = args.images_dir.expanduser().resolve()
    output = args.output.expanduser().resolve()
    try:
        expected = load_expected(args.expected.expanduser().resolve() if args.expected else None)
    except Exception as exc:
        print(f"ERROR: expected-copy parse failed: {exc}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"ERROR: images directory missing: {root}", file=sys.stderr)
        return 2
    engine, engine_info = detect_tesseract()
    page_paths = collect_pages(root)
    page_reports: dict[str, dict] = {}
    review_required = False
    for page, path in page_paths.items():
        expected_strings = expected.get(page, [])
        if engine is None:
            page_reports[page] = {
                "file": path.name,
                "status": "manual_review_required",
                "expected": expected_strings,
                "ocr_text": "",
                "missing_candidates": expected_strings,
                "note": "OCR engine unavailable; compare the rendered image visually",
            }
            review_required = True
            continue
        pytesseract, language = engine
        try:
            from PIL import Image

            with Image.open(path) as image:
                ocr_text = pytesseract.image_to_string(image, lang=language)
        except Exception as exc:
            page_reports[page] = {
                "file": path.name,
                "status": "manual_review_required",
                "expected": expected_strings,
                "ocr_text": "",
                "missing_candidates": expected_strings,
                "note": f"OCR failed: {exc}",
            }
            review_required = True
            continue
        normalized_ocr = normalized(ocr_text)
        missing = [value for value in expected_strings if normalized(value) not in normalized_ocr]
        expected_joined = normalized(" ".join(expected_strings))
        similarity = SequenceMatcher(None, expected_joined, normalized_ocr).ratio() if expected_joined or normalized_ocr else 1.0
        unexpected_candidate = bool(normalized_ocr and not expected_strings)
        status = "pass" if not missing and not unexpected_candidate else "review_required"
        review_required = review_required or status != "pass"
        page_reports[page] = {
            "file": path.name,
            "status": status,
            "expected": expected_strings,
            "ocr_text": ocr_text.strip(),
            "missing_candidates": missing,
            "unexpected_text_candidate": unexpected_candidate,
            "character_similarity": round(similarity, 4),
            "note": "OCR is a review signal, not the final verdict",
        }
    report = {
        "overall_status": "review_required" if review_required else "pass",
        "engine": engine_info,
        "expected_path": str(args.expected) if args.expected else "",
        "pages": page_reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"overall_status": report["overall_status"], "engine": engine_info["name"], "page_count": len(page_reports)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
