#!/usr/bin/env python3
"""Recommend evidence-backed Coupang price options under Rocket Growth margin gates."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def percentile(values: list[float], p: float) -> float:
    rows = sorted(values)
    point = (len(rows) - 1) * p
    low = int(point)
    high = min(low + 1, len(rows) - 1)
    weight = point - low
    return rows[low] * (1 - weight) + rows[high] * weight


def rounded_market_price(value: float) -> int:
    if value < 10000:
        return max(100, int(round(value / 100) * 100))
    return int(round(value / 100) * 100)


def validate_candidate(candidate: dict[str, Any], params: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("supply_price", "wholesale_shipping_per_unit", "rocket_growth_cost", "fee_rate_pct"):
        value = number(candidate.get(key))
        if value is None or value < 0:
            errors.append(f"유효하지 않은 비용: {key}")
    fee = number(candidate.get("fee_rate_pct"))
    if fee is not None and not 0 <= fee < 100:
        errors.append("판매수수료율은 0 이상 100 미만이어야 함")
    if candidate.get("vat_mode") != "excel_rocket_growth_simplified":
        errors.append("부가세 계산 모드 미확정")
    if candidate.get("costs_vat_included") is not True or candidate.get("input_vat_creditable") is not True:
        errors.append("비용 VAT 포함 및 매입세액 공제 가능 여부 미확정")
    for key, low, high in (
        ("base_margin_pct", 0, 90), ("stress_margin_pct", 0, 90),
        ("conditional_base_margin_pct", 0, 90), ("conditional_stress_margin_pct", 0, 90),
        ("stress_discount_pct", 0, 99), ("min_market_samples", 1, 1000),
    ):
        value = number(params.get(key))
        if value is not None and not low <= value <= high:
            errors.append(f"유효하지 않은 매개변수: {key}")
    return errors


def economics(candidate: dict[str, Any], sale_price: float) -> dict[str, float]:
    supply = float(candidate["supply_price"])
    wholesale_shipping = float(candidate["wholesale_shipping_per_unit"])
    growth = float(candidate["rocket_growth_cost"])
    other = float(candidate.get("other_cost") or 0)
    fee_rate = float(candidate["fee_rate_pct"])
    fixed = supply + wholesale_shipping + growth + other
    fee = sale_price * fee_rate / 100
    vat = sale_price * 0.10 - (fixed + fee) * 0.10
    profit = sale_price - fixed - fee - vat
    return {
        "sale_price": round(sale_price, 2),
        "fixed_cost": round(fixed, 2),
        "fee": round(fee, 2),
        "vat": round(vat, 2),
        "profit": round(profit, 2),
        "margin_pct": round(profit / sale_price * 100, 4),
    }


def floor_price(candidate: dict[str, Any], target_margin: float, discount: float = 0) -> int | None:
    low, high = 100.0, 1_000_000.0
    for _ in range(80):
        mid = (low + high) / 2
        actual = mid * (1 - discount / 100)
        if economics(candidate, actual)["margin_pct"] >= target_margin:
            high = mid
        else:
            low = mid
    result = int(math.ceil(high / 100) * 100)
    actual = result * (1 - discount / 100)
    return result if actual > 0 and economics(candidate, actual)["margin_pct"] >= target_margin else None


def demand_evidence_verified(row: dict[str, Any]) -> bool:
    """Require a purchase signal or at least five reviews for a price row."""
    recent_purchase = number(row.get("recent_purchase_count"))
    if recent_purchase is not None and recent_purchase >= 1:
        return True
    review_count = number(row.get("review_count"))
    return review_count is not None and review_count >= 5


def comparable_price_evidence(
    candidate: dict[str, Any], min_samples: int
) -> tuple[str | None, list[float], dict[str, Any]]:
    groups: dict[str, list[float]] = {"identical": [], "near_identical": [], "similar": []}
    seen: set[str] = set()
    verified_current_price_count = 0
    demand_backed_price_count = 0
    for row in candidate.get("market_prices") or []:
        price = number(row.get("price")) if isinstance(row, dict) else None
        if price is None or price <= 0:
            continue
        if candidate.get("require_verified_market_prices") is True and row.get("price_verified") is not True:
            continue
        required_quantity = candidate.get("required_bundle_quantity")
        if required_quantity is not None and row.get("quantity") != required_quantity:
            continue
        if row.get("is_ad") is True or row.get("exclude") is True:
            continue
        similarity = row.get("similarity")
        if similarity not in groups:
            continue
        group_id = str(row.get("product_group_id") or row.get("url") or f"{similarity}:{price}:{len(seen)}")
        if group_id in seen:
            continue
        seen.add(group_id)
        verified_current_price_count += 1
        if not demand_evidence_verified(row):
            continue
        demand_backed_price_count += 1
        groups[similarity].append(price)
    metadata = {
        "verified_current_price_count": verified_current_price_count,
        "demand_backed_price_count": demand_backed_price_count,
        "excluded_no_demand_evidence_count": (
            verified_current_price_count - demand_backed_price_count
        ),
        "price_basis": "demand_backed_current_sale_price",
        "demand_evidence_rule": "recent_purchase_count>=1_or_review_count>=5",
        "review_evidence_is_proxy": True,
    }
    if len(groups["identical"]) >= min_samples:
        return "identical", groups["identical"], metadata
    near = groups["identical"] + groups["near_identical"]
    if len(near) >= min_samples:
        return "near_identical", near, metadata
    if len(groups["similar"]) >= min_samples:
        return "similar", groups["similar"], metadata
    return None, near if len(near) >= len(groups["similar"]) else groups["similar"], metadata


def comparable_prices(candidate: dict[str, Any], min_samples: int) -> tuple[str | None, list[float]]:
    comparison_group, prices, _ = comparable_price_evidence(candidate, min_samples)
    return comparison_group, prices


def price_distribution(
    comparison_group: str | None,
    prices: list[float],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    distribution: dict[str, Any] = {
        "comparison_group": comparison_group,
        "count": len(prices),
        **metadata,
    }
    if prices:
        distribution.update({
            "min": min(prices),
            "p10": round(percentile(prices, .10), 2),
            "p25": round(percentile(prices, .25), 2),
            "p50": round(percentile(prices, .50), 2),
            "p75": round(percentile(prices, .75), 2),
            "max": max(prices),
        })
    return distribution


def evaluate(candidate: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    min_samples = int(params.get("min_market_samples", 5))
    validation_errors = validate_candidate(candidate, params)
    comparison_group, prices, price_evidence = comparable_price_evidence(candidate, min_samples)
    distribution = price_distribution(comparison_group, prices, price_evidence)
    if validation_errors or len(prices) < min_samples or comparison_group is None:
        sample_blocker = (
            f"판매 근거 가격 표본 부족: {len(prices)}/{min_samples}"
            if len(prices) < min_samples
            else None
        )
        return {
            "candidate_id": candidate.get("id"), "name": candidate.get("name"),
            "decision": "PRICE_REVIEW_BLOCKED",
            "blockers": validation_errors
            + ([sample_blocker] if sample_blocker else []),
            "market_price_distribution": distribution,
            "source_ref": {"id": candidate.get("id"), "url": candidate.get("url")},
        }

    standard_base_margin = float(params.get("base_margin_pct", 40))
    standard_stress_margin = float(params.get("stress_margin_pct", 30))
    conditional_base_margin = float(params.get("conditional_base_margin_pct", 35))
    conditional_stress_margin = float(params.get("conditional_stress_margin_pct", 25))
    stress_discount = float(params.get("stress_discount_pct", 10))
    base_floor = floor_price(candidate, standard_base_margin)
    stress_floor = floor_price(candidate, standard_stress_margin, stress_discount)
    conditional_base_floor = floor_price(candidate, conditional_base_margin)
    conditional_stress_floor = floor_price(candidate, conditional_stress_margin, stress_discount)
    if None in (base_floor, stress_floor, conditional_base_floor, conditional_stress_floor):
        return {
            "candidate_id": candidate.get("id"), "name": candidate.get("name"),
            "decision": "PRICE_REVIEW_BLOCKED", "blockers": ["목표 마진 가격 하한 계산 불가"],
            "source_ref": {"id": candidate.get("id"), "url": candidate.get("url")},
        }
    standard_final_floor = max(base_floor, stress_floor)
    conditional_final_floor = max(conditional_base_floor, conditional_stress_floor)
    if distribution["p50"] >= standard_final_floor:
        margin_tier = "standard_40_plus"
        final_floor = standard_final_floor
        required_base_margin = standard_base_margin
        required_stress_margin = standard_stress_margin
    elif distribution["p50"] >= conditional_final_floor:
        margin_tier = "conditional_35_40"
        final_floor = conditional_final_floor
        required_base_margin = conditional_base_margin
        required_stress_margin = conditional_stress_margin
    else:
        margin_tier = "below_conditional"
        final_floor = standard_final_floor
        required_base_margin = standard_base_margin
        required_stress_margin = standard_stress_margin
    raw_options = {
        "entry": max(final_floor, rounded_market_price(distribution["p25"])),
        "recommended": max(final_floor, rounded_market_price(distribution["p50"])),
        "premium": max(final_floor, rounded_market_price(distribution["p75"])),
    }
    options: dict[str, Any] = {}
    for label, price in raw_options.items():
        base = economics(candidate, price)
        stress = economics(candidate, price * (1 - stress_discount / 100))
        options[label] = {"price": price, "base": base, "stress": stress}

    evidence = candidate.get("differentiation_evidence") or []
    differentiated = any(
        isinstance(row, dict) and row.get("status") == "verified" and str(row.get("url") or "").startswith("http")
        for row in evidence
    )
    blockers: list[str] = []
    if margin_tier == "below_conditional":
        blockers.append("시장 p50이 조건부 35%/25% 원가 하한보다 낮음")
    if final_floor > distribution["p75"] and not differentiated:
        blockers.append("원가 가격 하한이 시장 p75를 초과하고 차별화 증거가 없음")
    recommended = options["recommended"]
    if recommended["base"]["margin_pct"] < required_base_margin:
        blockers.append(f"추천가 정상 마진 {required_base_margin:g}% 미달")
    if recommended["stress"]["margin_pct"] < required_stress_margin:
        blockers.append(f"추천가 10% 하락 후 마진 {required_stress_margin:g}% 미달")

    demand = number(candidate.get("demand_signal_score")) or 0
    headroom = distribution["p50"] - final_floor
    recommendation_score = demand + max(-30, min(30, headroom / max(distribution["p50"], 1) * 100))
    decision = "REJECT" if blockers else (
        "CONDITIONAL_TEST_PRICE_REVIEW" if margin_tier == "conditional_35_40" else "PRICE_REVIEW"
    )
    return {
        "candidate_id": candidate.get("id"), "name": candidate.get("name"), "decision": decision,
        "margin_tier": margin_tier, "blockers": blockers, "market_price_distribution": distribution,
        "base_floor_price": base_floor, "stress_floor_price": stress_floor,
        "standard_final_floor_price": standard_final_floor,
        "conditional_base_floor_price": conditional_base_floor,
        "conditional_stress_floor_price": conditional_stress_floor,
        "conditional_final_floor_price": conditional_final_floor,
        "final_floor_price": final_floor, "price_options": options,
        "recommendation_score": round(recommendation_score, 3),
        "source_ref": {"id": candidate.get("id"), "url": candidate.get("url")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise SystemExit("입력 오류: candidates 배열이 필요합니다.")
    params = payload.get("parameters") or {}
    rows = [evaluate(row, params) if isinstance(row, dict) else {
        "candidate_id": None, "name": None, "decision": "PRICE_REVIEW_BLOCKED",
        "blockers": ["후보 행은 객체여야 함"], "source_ref": {},
    } for row in candidates]
    priority = {"PRICE_REVIEW": 0, "CONDITIONAL_TEST_PRICE_REVIEW": 1, "PRICE_REVIEW_BLOCKED": 2, "REJECT": 3}
    rows.sort(key=lambda x: (priority.get(x["decision"], 9), -float(x["recommendation_score"] if x.get("recommendation_score") is not None else -999)))
    for index, row in enumerate(rows, 1):
        row["rank"] = index
    result = {"schema_version": "1.0", "parameters": params, "count": len(rows), "candidates": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: sum(1 for r in rows if r["decision"] == key) for key in priority}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
