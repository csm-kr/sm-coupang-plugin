#!/usr/bin/env python3
"""Build a diversified research sample from Domeggook category TOP 150 pools."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


RANK_BANDS = ((1, 30, "top"), (31, 75, "middle"), (76, 150, "tail"))
RISK_WORDS = {
    "의료", "치료", "건강기능", "영양제", "화장품", "유아", "아동", "어린이",
    "전기", "배터리", "충전", "식품", "먹는", "캐릭터", "정품", "브랜드",
}


def number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def normalize_name(value: str) -> str:
    text = re.sub(r"\[[^]]+\]|\([^)]*\)", " ", value.lower())
    text = re.sub(r"\b\d+(?:\.\d+)?\s*(?:ml|l|cm|mm|g|kg|개|매|color)\b", " ", text)
    tokens = re.findall(r"[가-힣a-z0-9]+", text)
    return " ".join(tokens[:8])


def rank_band(rank: int) -> str:
    for low, high, label in RANK_BANDS:
        if low <= rank <= high:
            return label
    return "outside"


def risk_flags(item: dict[str, Any]) -> list[str]:
    name = str(item.get("name") or "").lower()
    flags = sorted(word for word in RISK_WORDS if word.lower() in name)
    return [f"keyword:{word}" for word in flags]


def exploration_score(item: dict[str, Any]) -> float:
    """Score only research priority, never final sellability."""
    rank = int(item.get("rank") or 999)
    price = number(item.get("supply_price"))
    moq = number(item.get("moq"))
    score = 0.0
    if rank <= 150:
        score += 10 * (151 - rank) / 150
    if price is not None:
        score += 12 if 2000 <= price <= 12000 else 7 if 500 <= price <= 20000 else 2
    if moq is not None:
        score += 10 if moq <= 2 else 7 if moq <= 5 else 2 if moq <= 10 else -5
    if item.get("rank_change") == "NEW":
        score += 2
    score -= 5 * len(risk_flags(item))
    return round(score, 3)


def allocate(total: int) -> dict[str, int]:
    raw = {"top": total * 0.4, "middle": total * 0.35, "tail": total * 0.25}
    result = {key: int(value) for key, value in raw.items()}
    while sum(result.values()) < total:
        key = max(raw, key=lambda k: raw[k] - result[k])
        result[key] += 1
    return result


def proportional_quota(total: int, weights: dict[str, float], available: set[str]) -> dict[str, int]:
    active = {key: value for key, value in weights.items() if key in available}
    if not active:
        return {}
    weight_sum = sum(active.values())
    raw = {key: total * value / weight_sum for key, value in active.items()}
    result = {key: int(value) for key, value in raw.items()}
    while sum(result.values()) < total:
        key = max(raw, key=lambda k: raw[k] - result[k])
        result[key] += 1
    return result


def even_quota(total: int, values: set[str]) -> dict[str, int]:
    if not values:
        return {}
    ordered = sorted(values)
    return {value: total // len(ordered) + (1 if i < total % len(ordered) else 0)
            for i, value in enumerate(ordered)}


def sample(items: list[dict[str, Any]], target: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prepared: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for raw in items:
        item = dict(raw)
        url = str(item.get("url") or "")
        rank = item.get("rank")
        price = number(item.get("supply_price"))
        moq = number(item.get("moq"))
        if (not url.startswith("http") or not isinstance(rank, int) or isinstance(rank, bool)
                or not 1 <= rank <= 150 or not str(item.get("name") or "").strip()
                or price is None or price < 0 or moq is None or moq <= 0):
            rejected.append({"item": raw, "reason": "invalid_url_or_rank"})
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        item["rank_band"] = rank_band(rank)
        item["category"] = str(item.get("category") or "unknown")
        item["origin_scope"] = str(item.get("origin_scope") or "unknown")
        if item["origin_scope"] not in {"domestic", "imported", "unknown"}:
            item["origin_scope"] = "unknown"
        item["pool_type"] = str(item.get("pool_type") or "category_top150")
        if item["pool_type"] not in {"category_top150", "challenge_best"}:
            item["pool_type"] = "category_top150"
        item["normalized_name"] = normalize_name(str(item.get("name") or ""))
        item["risk_flags"] = risk_flags(item)
        item["exploration_score"] = exploration_score(item)
        prepared.append(item)

    rank_quotas = allocate(target)
    category_quotas = even_quota(target, {item["category"] for item in prepared})
    origin_quotas = proportional_quota(
        target, {"domestic": 0.45, "imported": 0.45, "unknown": 0.10},
        {item["origin_scope"] for item in prepared},
    )
    pool_quotas = proportional_quota(
        target, {"category_top150": 0.80, "challenge_best": 0.20},
        {item["pool_type"] for item in prepared},
    )
    selected: list[dict[str, Any]] = []
    selected_urls: set[str] = set()
    selected_keys: Counter[str] = Counter()
    supplier_counts: Counter[str] = Counter()
    rank_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    origin_counts: Counter[str] = Counter()
    pool_counts: Counter[str] = Counter()

    remaining = list(prepared)
    while remaining and len(selected) < target:
        def selection_score(item: dict[str, Any]) -> tuple[float, int]:
            bonus = 0.0
            bonus += 18 if rank_counts[item["rank_band"]] < rank_quotas.get(item["rank_band"], 0) else 0
            bonus += 22 if category_counts[item["category"]] < category_quotas.get(item["category"], 0) else 0
            bonus += 20 if origin_counts[item["origin_scope"]] < origin_quotas.get(item["origin_scope"], 0) else 0
            bonus += 12 if pool_counts[item["pool_type"]] < pool_quotas.get(item["pool_type"], 0) else 0
            return item["exploration_score"] + bonus, -item["rank"]

        remaining.sort(key=selection_score, reverse=True)
        chosen_index = None
        for index, item in enumerate(remaining):
            key = item["normalized_name"]
            supplier = str(item.get("supplier") or "UNKNOWN")
            if (key and selected_keys[key] >= 2) or (supplier != "UNKNOWN" and supplier_counts[supplier] >= 3):
                continue
            chosen_index = index
            break
        if chosen_index is None:
            break
        item = remaining.pop(chosen_index)
        selected.append(item)
        selected_urls.add(item["url"])
        selected_keys[item["normalized_name"]] += 1
        supplier = str(item.get("supplier") or "UNKNOWN")
        if supplier != "UNKNOWN":
            supplier_counts[supplier] += 1
        rank_counts[item["rank_band"]] += 1
        category_counts[item["category"]] += 1
        origin_counts[item["origin_scope"]] += 1
        pool_counts[item["pool_type"]] += 1

    selected.sort(key=lambda x: (-x["exploration_score"], x["rank"]))
    for index, item in enumerate(selected, 1):
        item["research_priority"] = index
    return selected, rejected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target", type=int, default=30)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    items = payload.get("items")
    if not isinstance(items, list):
        raise SystemExit("입력 오류: items 배열이 필요합니다.")
    target = min(max(args.target, 1), 150)
    selected, rejected = sample(items, target)
    result = {
        "schema_version": "1.0",
        "source_url": payload.get("source_url"),
        "category": payload.get("category"),
        "pool_count": len(items),
        "target": target,
        "selected_count": len(selected),
        "method": "rank_band_40_35_25_plus_name_diversity",
        "coverage": {
            "rank_band": dict(Counter(item["rank_band"] for item in selected)),
            "category": dict(Counter(item["category"] for item in selected)),
            "origin_scope": dict(Counter(item["origin_scope"] for item in selected)),
            "pool_type": dict(Counter(item["pool_type"] for item in selected)),
        },
        "note": "exploration_score는 조사 우선순위이며 판매 적합성 점수가 아님",
        "selected": selected,
        "rejected": rejected,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pool": len(items), "selected": len(selected)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
