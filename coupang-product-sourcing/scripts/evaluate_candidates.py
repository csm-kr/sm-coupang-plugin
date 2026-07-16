#!/usr/bin/env python3
"""Calculate traceable Coupang sourcing economics, scores, and decisions."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


DEFAULT_PARAMS = {
    "max_initial_purchase": 150000,
    "max_moq": 10,
    "max_options": 10,
    "min_contribution_profit": 3500,
    "min_contribution_margin_pct": 40,
    "min_conditional_margin_pct": 35,
    "stress_price_discount_pct": 10,
    "min_stress_margin_pct": 30,
    "min_conditional_stress_margin_pct": 25,
}

OBSERVED_SCORE_LIMITS = {
    "demand_recent_purchase_reviews": 15,
    "demand_ranking_exposure": 10,
    "demand_multi_seller_sales": 10,
    "demand_seasonality_persistence": 5,
    "competition_seller_brand_dominance": 4,
    "competition_price_competition": 3,
    "competition_differentiation_room": 3,
    "operations_regulatory_ip_safety": 4,
    "operations_returns_options": 3,
    "operations_supply_images": 3,
}

DEMAND_KEYS = [key for key in OBSERVED_SCORE_LIMITS if key.startswith("demand_")]
COMPETITION_KEYS = [key for key in OBSERVED_SCORE_LIMITS if key.startswith("competition_")]
OPERATIONS_KEYS = [key for key in OBSERVED_SCORE_LIMITS if key.startswith("operations_")]
COST_KEYS = [
    "inbound_inspection",
    "packaging",
    "coupang_fee_rate_pct",
    "customer_shipping",
    "other_variable",
]


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def is_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def has_timezone(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def get_params(run: dict[str, Any]) -> dict[str, float]:
    params = dict(DEFAULT_PARAMS)
    supplied = run.get("parameters") or {}
    for key in DEFAULT_PARAMS:
        value = supplied.get(key)
        if is_number(value):
            params[key] = value
    return params


def add_failure(items: list[dict[str, Any]], code: str, reason: str, urls: list[str] | None = None) -> None:
    items.append({"code": code, "reason": reason, "urls": unique(urls or [])})


def hard_filter_failures(candidate: dict[str, Any], params: dict[str, float]) -> list[dict[str, Any]]:
    wholesale = candidate.get("wholesale") or {}
    failures: list[dict[str, Any]] = []
    wholesale_url = wholesale.get("url")
    urls = [wholesale_url] if is_url(wholesale_url) else []
    price = wholesale.get("supply_price")
    moq = wholesale.get("moq")
    shipping = wholesale.get("wholesale_shipping_total")
    options = wholesale.get("option_count")

    if not is_url(wholesale_url):
        add_failure(failures, "WHOLESALE_URL_UNKNOWN", "도매 상품 URL을 확인할 수 없음")
    if not wholesale.get("supplier"):
        add_failure(failures, "SUPPLIER_UNKNOWN", "공급사를 확인할 수 없음", urls)
    if not is_number(price) or price < 0:
        add_failure(failures, "SUPPLY_PRICE_UNKNOWN", "공급가를 확인할 수 없음", urls)
    if not is_number(moq) or moq <= 0 or int(moq) != moq:
        add_failure(failures, "MOQ_UNKNOWN", "유효한 최소구매수량을 확인할 수 없음", urls)
    if not is_number(shipping) or shipping < 0:
        add_failure(failures, "WHOLESALE_SHIPPING_UNKNOWN", "도매 배송비를 확인할 수 없음", urls)
    if not is_number(options) or options < 1:
        add_failure(failures, "OPTION_COUNT_UNKNOWN", "옵션 수를 확인할 수 없음", urls)
    elif options > params["max_options"]:
        add_failure(failures, "TOO_MANY_OPTIONS", f"옵션 수 {options:g}개가 한도 {params['max_options']:g}개를 초과", urls)

    if is_number(moq) and moq > params["max_moq"]:
        add_failure(failures, "MOQ_OVER_LIMIT", f"MOQ {moq:g}개가 한도 {params['max_moq']:g}개를 초과", urls)
    if is_number(price) and is_number(moq) and price * moq > params["max_initial_purchase"]:
        add_failure(
            failures,
            "INITIAL_PURCHASE_OVER_LIMIT",
            f"초기 매입액 {price * moq:,.0f}원이 한도 {params['max_initial_purchase']:,.0f}원을 초과",
            urls,
        )

    status_rules = [
        ("photo_match_status", {"confirmed"}, "PHOTO_MATCH_UNCLEAR", "상품 사진과 실제 공급상품의 일치 여부가 불명확"),
        ("image_status", {"sufficient"}, "IMAGES_UNUSABLE", "상세페이지에 사용할 수 있는 이미지가 부족하거나 사용이 제한됨"),
        ("supply_update_status", {"stable_updates_provided"}, "SUPPLY_UPDATES_MISSING", "품절·가격변경·배송지연 정보 제공 여부가 불명확"),
        ("regulatory_status", {"not_required_verified", "documents_verified", "separate_review"}, "REGULATORY_UNKNOWN", "필요한 인증·시험·허가 여부를 확인할 수 없음"),
        ("ip_status", {"clear"}, "IP_RISK", "상표권·캐릭터·브랜드 도용 위험이 해소되지 않음"),
    ]
    for field, allowed, code, reason in status_rules:
        if wholesale.get(field) not in allowed:
            add_failure(failures, code, reason, urls)

    for flag in wholesale.get("hard_risk_flags") or []:
        add_failure(failures, "HIGH_OPERATION_RISK", str(flag), urls)
    for item in wholesale.get("manual_hard_failures") or []:
        if isinstance(item, dict):
            add_failure(
                failures,
                str(item.get("code") or "MANUAL_HARD_FAILURE"),
                str(item.get("reason") or "수동 하드 필터 실패"),
                [u for u in item.get("urls", []) if is_url(u)],
            )
        else:
            add_failure(failures, "MANUAL_HARD_FAILURE", str(item), urls)
    return failures


def collect_market_stats(candidate: dict[str, Any]) -> dict[str, Any]:
    market = candidate.get("market") or {}
    results = [row for row in market.get("results") or [] if isinstance(row, dict)]
    ranked = [row for row in results if row.get("sort", "ranking") == "ranking"]
    representative = [row for row in ranked if row.get("query_type") == "category"] or ranked
    top20 = [row for row in representative if is_number(row.get("rank")) and row["rank"] <= 20]
    identical = [row for row in top20 if row.get("similarity") in {"identical", "near_identical"}]
    organic = [row for row in top20 if row.get("is_ad") is False]
    review_counts = [row["review_count"] for row in organic if is_number(row.get("review_count"))]
    comparable_prices = [
        row.get("unit_price") if is_number(row.get("unit_price")) else row.get("price")
        for row in organic
        if is_number(row.get("unit_price")) or is_number(row.get("price"))
    ]
    comparable_prices.sort()
    lower_quartile = None
    if comparable_prices:
        lower_quartile = comparable_prices[max(0, math.ceil(len(comparable_prices) * 0.25) - 1)]
    top10 = [row for row in organic if (row.get("organic_position") or row.get("rank", 999)) <= 10]
    strong_count = sum(1 for row in top10 if is_number(row.get("review_count")) and row["review_count"] >= 1000)

    attempts = {row.get("query_type"): row for row in market.get("query_attempts") or [] if isinstance(row, dict)}
    queries = candidate.get("search_queries") or {}
    incomplete: list[str] = []
    for query_type in ("category", "appeal", "identical"):
        if not queries.get(query_type):
            incomplete.append(f"검색어 누락: {query_type}")
        attempt = attempts.get(query_type)
        if not attempt or attempt.get("status") not in {"complete", "no_results"} or not is_url(attempt.get("url")):
            incomplete.append(f"검색 시도 미완료: {query_type}")
    for query_type in ("category", "appeal"):
        if not any(row.get("query_type") == query_type and is_url(row.get("url")) for row in results):
            incomplete.append(f"실제 경쟁상품 결과 없음: {query_type}")
    if not has_timezone(market.get("researched_at")):
        incomplete.append("시간대가 포함된 조사시각 누락")
    for index, row in enumerate(results, 1):
        if (
            not is_url(row.get("url"))
            or not isinstance(row.get("is_ad"), bool)
            or not has_timezone(row.get("observed_at"))
            or not row.get("title")
            or not is_number(row.get("price"))
        ):
            incomplete.append(f"경쟁상품 {index}의 제목·URL·광고 여부·가격·조사시각 불완전")

    return {
        "identical_top20_count": len(identical),
        "organic_review_median": statistics.median(review_counts) if review_counts else None,
        "organic_unit_price_median": statistics.median(comparable_prices) if comparable_prices else None,
        "organic_unit_price_lower_quartile": lower_quartile,
        "top10_reviews_ge_1000": strong_count,
        "representative_result_count": len(top20),
        "organic_result_count": len(organic),
        "research_complete": not incomplete,
        "research_gaps": unique(incomplete),
    }


def calculate_economics(candidate: dict[str, Any], params: dict[str, float]) -> tuple[dict[str, Any] | None, list[str]]:
    wholesale = candidate.get("wholesale") or {}
    pricing = candidate.get("pricing") or {}
    costs = pricing.get("costs") or {}
    missing: list[str] = []
    required = {
        "wholesale.supply_price": wholesale.get("supply_price"),
        "wholesale.moq": wholesale.get("moq"),
        "wholesale.wholesale_shipping_total": wholesale.get("wholesale_shipping_total"),
        "pricing.conservative_sale_price": pricing.get("conservative_sale_price"),
        **{f"pricing.costs.{key}": costs.get(key) for key in COST_KEYS},
    }
    for key, value in required.items():
        if not is_number(value) or value < 0:
            missing.append(key)
    if missing or wholesale.get("moq") == 0 or pricing.get("conservative_sale_price") == 0:
        return None, missing

    supply_price = float(wholesale["supply_price"])
    moq = float(wholesale["moq"])
    shipping_unit = float(wholesale["wholesale_shipping_total"]) / moq
    initial_purchase = supply_price * moq

    def at_price(sale_price: float) -> dict[str, float | None]:
        coupang_fee = sale_price * float(costs["coupang_fee_rate_pct"]) / 100
        fixed_costs = (
            supply_price
            + shipping_unit
            + float(costs["inbound_inspection"])
            + float(costs["packaging"])
            + float(costs["customer_shipping"])
            + float(costs["other_variable"])
        )
        # 지옥캠프 로켓그로스 계산기와 동일한 선소싱 부가세 모델:
        # 매출 부가세 10% - 원가·입출고/배송비·판매수수료의 매입세액 10%.
        vat = sale_price * 0.10 - (fixed_costs + coupang_fee) * 0.10
        variable_cost = fixed_costs + coupang_fee + vat
        contribution = sale_price - variable_cost
        margin = contribution / sale_price * 100
        # 참고 계산기의 =110%/마진율과 동일하다.
        break_even_roas = 1.10 * sale_price / contribution if contribution > 0 else None
        return {
            "sale_price": round(sale_price, 2),
            "coupang_fee": round(coupang_fee, 2),
            "vat": round(vat, 2),
            "variable_cost": round(variable_cost, 2),
            "contribution_profit": round(contribution, 2),
            "contribution_margin_pct": round(margin, 4),
            "break_even_roas_x": round(break_even_roas, 4) if break_even_roas is not None else None,
            "break_even_roas_pct": round(break_even_roas * 100, 2) if break_even_roas is not None else None,
        }

    base = at_price(float(pricing["conservative_sale_price"]))
    stress_price = float(pricing["conservative_sale_price"]) * (1 - params["stress_price_discount_pct"] / 100)
    return {
        "supply_price": round(supply_price, 2),
        "moq": int(moq),
        "initial_purchase": round(initial_purchase, 2),
        "wholesale_shipping_per_unit": round(shipping_unit, 2),
        "base": base,
        "stress_discount_pct": params["stress_price_discount_pct"],
        "stress": at_price(stress_price),
    }, []


def band(value: float, thresholds: list[tuple[float, int]]) -> int:
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return 0


def margin_scores(economics: dict[str, Any] | None, pricing: dict[str, Any]) -> dict[str, Any]:
    if not economics:
        return {"subtotal": None}
    base = economics["base"]
    stress = economics["stress"]
    scores = {
        "contribution_margin": band(base["contribution_margin_pct"], [(40, 12), (35, 10), (30, 8), (25, 6), (20, 3), (15, 1)]),
        "contribution_profit": band(base["contribution_profit"], [(10000, 10), (7500, 9), (6000, 8), (5000, 7), (3500, 5), (2000, 2)]),
        "price_resilience": band(stress["contribution_margin_pct"], [(25, 7), (20, 6), (15, 4), (10, 2), (0, 1)]),
        "initial_purchase": band(-economics["initial_purchase"], [(-30000, 5), (-75000, 4), (-150000, 3), (-200000, 1)]),
        "stability": 1
        if pricing.get("costs_verified") is True
        and (any(is_url(url) for url in pricing.get("cost_source_urls") or []) or pricing.get("cost_basis_note"))
        and stress["contribution_profit"] > 0
        else 0,
    }
    scores["subtotal"] = sum(scores.values())
    return scores


def classify_margin_tier(economics: dict[str, Any] | None, params: dict[str, float]) -> str:
    if not economics:
        return "unknown"
    base_margin = economics["base"]["contribution_margin_pct"]
    stress_margin = economics["stress"]["contribution_margin_pct"]
    if base_margin >= params["min_contribution_margin_pct"] and stress_margin >= params["min_stress_margin_pct"]:
        return "standard_40_plus"
    if base_margin >= params["min_conditional_margin_pct"] and stress_margin >= params["min_conditional_stress_margin_pct"]:
        return "conditional_35_40"
    return "below_conditional"


def observed_scores(candidate: dict[str, Any]) -> tuple[dict[str, float | None], list[str]]:
    market = candidate.get("market") or {}
    supplied = market.get("scores") or {}
    evidence = market.get("score_evidence") or {}
    result: dict[str, float | None] = {}
    gaps: list[str] = []
    for key, maximum in OBSERVED_SCORE_LIMITS.items():
        value = supplied.get(key)
        proof = evidence.get(key) or {}
        if not is_number(value) or value < 0 or value > maximum:
            result[key] = None
            gaps.append(f"점수 누락 또는 범위 오류: {key} (0~{maximum})")
            continue
        if not proof.get("note") or not any(is_url(url) for url in proof.get("urls") or []):
            result[key] = None
            gaps.append(f"점수 근거 누락: {key}")
            continue
        result[key] = float(value)
    return result, gaps


def subtotal(scores: dict[str, float | None], keys: list[str]) -> float | None:
    values = [scores.get(key) for key in keys]
    return sum(values) if all(is_number(value) for value in values) else None


def saturation_score(count: int) -> int:
    if count <= 3:
        return 5
    if count <= 5:
        return 4
    if count <= 7:
        return 3
    if count <= 9:
        return 2
    if count <= 12:
        return 1
    return 0


def calculate_scenarios(candidate: dict[str, Any], economics: dict[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    market = candidate.get("market") or {}
    raw = market.get("demand_scenarios") or []
    contribution = economics["base"]["contribution_profit"] if economics else None
    calculated: list[dict[str, Any]] = []
    gaps: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        row = copy.deepcopy(item)
        orders = item.get("market_orders")
        share = item.get("expected_share_pct")
        valid_evidence = bool(item.get("basis")) and any(is_url(url) for url in item.get("source_urls") or [])
        if is_number(orders) and orders >= 0 and is_number(share) and 0 <= share <= 100 and is_number(contribution) and valid_evidence:
            row["monthly_expected_profit"] = round(orders * share / 100 * contribution, 2)
        else:
            row["monthly_expected_profit"] = None
            gaps.append(f"수요 시나리오 계산 불가: {item.get('label') or '미지정'}")
        calculated.append(row)
    labels = {row.get("label") for row in calculated if row.get("monthly_expected_profit") is not None}
    for label in ("low", "mid", "high"):
        if label not in labels:
            gaps.append(f"근거 있는 수요 시나리오 누락: {label}")
    profits = [row["monthly_expected_profit"] for row in calculated if is_number(row.get("monthly_expected_profit"))]
    shares = [row["expected_share_pct"] for row in calculated if is_number(row.get("expected_share_pct"))]
    summary = {
        "expected_share_low_pct": min(shares) if shares else None,
        "expected_share_high_pct": max(shares) if shares else None,
        "monthly_expected_profit_low": min(profits) if profits else None,
        "monthly_expected_profit_high": max(profits) if profits else None,
        "scenario_complete": {"low", "mid", "high"}.issubset(labels),
    }
    return calculated, summary, unique(gaps)


def demand_level(score: float | None) -> str:
    if score is None:
        return "uncertain"
    if score >= 32:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def all_candidate_urls(candidate: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    wholesale_url = (candidate.get("wholesale") or {}).get("url")
    if is_url(wholesale_url):
        urls.append(wholesale_url)
    for row in (candidate.get("market") or {}).get("results") or []:
        if isinstance(row, dict) and is_url(row.get("url")):
            urls.append(row["url"])
    for url in (candidate.get("pricing") or {}).get("price_basis_urls") or []:
        if is_url(url):
            urls.append(url)
    return unique(urls)


def evaluate_candidate(candidate: dict[str, Any], params: dict[str, float]) -> dict[str, Any]:
    hard_failures = hard_filter_failures(candidate, params)
    market_stats = collect_market_stats(candidate)
    economics, economics_gaps = calculate_economics(candidate, params)
    observed, score_gaps = observed_scores(candidate)
    margin = margin_scores(economics, candidate.get("pricing") or {})
    margin_tier = classify_margin_tier(economics, params)

    demand = subtotal(observed, DEMAND_KEYS)
    competition_manual = subtotal(observed, COMPETITION_KEYS)
    competition = competition_manual + saturation_score(market_stats["identical_top20_count"]) if competition_manual is not None else None
    operations = subtotal(observed, OPERATIONS_KEYS)
    total = None
    if all(is_number(value) for value in (demand, competition, operations, margin.get("subtotal"))):
        total = demand + competition + operations + margin["subtotal"]

    scenarios, scenario_summary, scenario_gaps = calculate_scenarios(candidate, economics)
    pricing = candidate.get("pricing") or {}
    wholesale = candidate.get("wholesale") or {}
    handoff = candidate.get("content_handoff") or {}
    blockers: list[str] = []
    blockers.extend(economics_gaps)
    blockers.extend(score_gaps)
    blockers.extend(market_stats["research_gaps"])
    blockers.extend(scenario_gaps)
    has_cost_basis = any(is_url(url) for url in pricing.get("cost_source_urls") or []) or bool(pricing.get("cost_basis_note"))
    if pricing.get("costs_verified") is not True or not has_cost_basis:
        blockers.append("비용 확인 또는 비용 출처 미완료")
    if not any(is_url(url) for url in pricing.get("price_basis_urls") or []):
        blockers.append("보수적 판매가 근거 URL 누락")
    if not pricing.get("price_basis_note"):
        blockers.append("보수적 판매가 산정 메모 누락")
    if wholesale.get("regulatory_status") == "separate_review":
        blockers.append("규제 중요 카테고리 별도 검토 필요")
    if not handoff.get("sample_checks"):
        blockers.append("샘플 확인 항목 누락")
    if len(handoff.get("differentiators") or []) != 3:
        blockers.append("차별화 소구는 정확히 3개 필요")
    if len(handoff.get("proof_scenes") or []) != 3:
        blockers.append("증명 장면은 정확히 3개 필요")
    if not handoff.get("gif_idea"):
        blockers.append("GIF 아이디어 누락")

    margin_rejects: list[str] = []
    margin_gates: list[str] = []
    if economics:
        base = economics["base"]
        stress = economics["stress"]
        if base["contribution_profit"] <= 0:
            margin_rejects.append("배송비·수수료·충당금을 포함하면 공헌이익 적자")
        if base["contribution_profit"] < 2000:
            margin_rejects.append("선소싱 주문당 공헌이익이 2,000원 미만")
        if stress["contribution_profit"] <= 0:
            margin_rejects.append("판매가 10% 인하 시 공헌이익 적자")
        if base["contribution_profit"] < params["min_contribution_profit"]:
            margin_gates.append("최소 주문당 공헌이익 미달")
        if base["contribution_margin_pct"] < params["min_conditional_margin_pct"]:
            margin_gates.append("조건부 최소 공헌이익률 35% 미달")
        if stress["contribution_margin_pct"] < params["min_conditional_stress_margin_pct"]:
            margin_gates.append("조건부 가격 인하 내성 25% 미달")
    blockers.extend(margin_gates)
    blockers = unique(blockers)

    if hard_failures or margin_rejects:
        decision = "REJECT"
    elif total is None:
        decision = "WATCH"
    elif total < 60:
        decision = "REJECT"
    elif total >= 75 and not blockers:
        decision = "SHORTLIST" if margin_tier == "standard_40_plus" else "CONDITIONAL"
    else:
        decision = "WATCH"

    scores = {
        "demand": demand,
        "margin": margin.get("subtotal"),
        "competition_opportunity": competition,
        "operations_safety": operations,
        "total": total,
        "observed_components": observed,
        "margin_components": margin,
        "competition_saturation": saturation_score(market_stats["identical_top20_count"]),
    }
    return {
        "candidate_id": candidate.get("id"),
        "name": candidate.get("name"),
        "decision": decision,
        "margin_tier": margin_tier,
        "decision_reasons": [item["reason"] for item in hard_failures] + margin_rejects + blockers,
        "hard_filter_failures": hard_failures,
        "shortlist_blockers": blockers,
        "margin_reject_reasons": margin_rejects,
        "market_stats": market_stats,
        "economics": economics,
        "scores": scores,
        "demand_level": demand_level(demand),
        "demand_scenarios": scenarios,
        "scenario_summary": scenario_summary,
        "content_handoff": handoff,
        "evidence_urls": all_candidate_urls(candidate),
        "score_evidence": (candidate.get("market") or {}).get("score_evidence") or {},
        "source_candidate": candidate,
    }


def decision_priority(value: str) -> int:
    return {"SHORTLIST": 0, "CONDITIONAL": 1, "WATCH": 2, "REJECT": 3}.get(value, 4)


def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    total = row["scores"].get("total")
    ai_priority = bool((row.get("content_handoff") or {}).get("ai_visual_priority"))
    expected = row["scenario_summary"].get("monthly_expected_profit_high")
    return (
        decision_priority(row["decision"]),
        -(total if is_number(total) else -1),
        -int(ai_priority),
        -(expected if is_number(expected) else -1),
        str(row.get("candidate_id") or ""),
    )


def enforce_shortlist_limit(rows: list[dict[str, Any]], limit: int) -> None:
    shortlisted = sorted([row for row in rows if row["decision"] == "SHORTLIST"], key=sort_key)
    for row in shortlisted[limit:]:
        row["decision"] = "WATCH"
        row["shortlist_blockers"].append(f"SHORTLIST 최대 {limit}개 제한")
        row["decision_reasons"].append(f"SHORTLIST 최대 {limit}개 제한")


def fmt_num(value: Any, digits: int = 0) -> str:
    if not is_number(value):
        return "UNKNOWN"
    return f"{value:,.{digits}f}"


def flattened_row(row: dict[str, Any]) -> dict[str, Any]:
    economics = row.get("economics") or {}
    base = economics.get("base") or {}
    scenario = row.get("scenario_summary") or {}
    source = row.get("source_candidate") or {}
    wholesale = source.get("wholesale") or {}
    handoff = row.get("content_handoff") or {}
    return {
        "순위": row.get("rank"),
        "판정": row["decision"],
        "상품명": row.get("name"),
        "도매 URL": wholesale.get("url"),
        "공급가": economics.get("supply_price"),
        "MOQ": economics.get("moq"),
        "초기 매입액": economics.get("initial_purchase"),
        "쿠팡 예상 판매가": base.get("sale_price"),
        "예상 공헌이익": base.get("contribution_profit"),
        "공헌이익률": base.get("contribution_margin_pct"),
        "마진 구간": row.get("margin_tier"),
        "수요 점수": row["scores"].get("demand"),
        "수요 수준": row.get("demand_level"),
        "예상 점유율 범위": f"{fmt_num(scenario.get('expected_share_low_pct'), 2)}%~{fmt_num(scenario.get('expected_share_high_pct'), 2)}%",
        "월 기대이익 범위": f"{fmt_num(scenario.get('monthly_expected_profit_low'))}~{fmt_num(scenario.get('monthly_expected_profit_high'))}",
        "경쟁기회 점수": row["scores"].get("competition_opportunity"),
        "마진 점수": row["scores"].get("margin"),
        "운영위험 점수": row["scores"].get("operations_safety"),
        "총점": row["scores"].get("total"),
        "동일상품 수": row["market_stats"].get("identical_top20_count"),
        "상위 경쟁상품 리뷰 중앙값": row["market_stats"].get("organic_review_median"),
        "핵심 차별화 소구": " | ".join(handoff.get("differentiators") or []),
        "리스크와 확인 필요 항목": " | ".join(row.get("decision_reasons") or []),
        "근거 URL": " | ".join(row.get("evidence_urls") or []),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    flat = [flattened_row(row) for row in rows]
    fieldnames = list(flat[0].keys()) if flat else list(flattened_row({"decision": "", "scores": {}, "market_stats": {}}).keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat)


def write_markdown(path: Path, run: dict[str, Any], rows: list[dict[str, Any]], created_at: str) -> None:
    lines = [
        "# 쿠팡 상품 소싱 결과",
        "",
        f"- 조사명: {run.get('name') or '미지정'}",
        f"- 생성시각: {created_at}",
        f"- 통화: {run.get('currency') or 'KRW'}",
        f"- 후보 수: {len(rows)}",
        f"- SHORTLIST 수: {sum(1 for row in rows if row['decision'] == 'SHORTLIST')}",
        "",
        "| 순위 | 판정 | 상품명 | 공급가/MOQ | 판매가 | 공헌이익(률) | 수요/총점 | 동일상품/리뷰중앙값 | 월 기대이익 |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        econ = row.get("economics") or {}
        base = econ.get("base") or {}
        scenario = row.get("scenario_summary") or {}
        lines.append(
            f"| {row['rank']} | {row['decision']} | {row.get('name') or 'UNKNOWN'} | "
            f"{fmt_num(econ.get('supply_price'))}/{fmt_num(econ.get('moq'))} | {fmt_num(base.get('sale_price'))} | "
            f"{fmt_num(base.get('contribution_profit'))} ({fmt_num(base.get('contribution_margin_pct'), 1)}%) | "
            f"{fmt_num(row['scores'].get('demand'))}/{fmt_num(row['scores'].get('total'))} | "
            f"{fmt_num(row['market_stats'].get('identical_top20_count'))}/{fmt_num(row['market_stats'].get('organic_review_median'))} | "
            f"{fmt_num(scenario.get('monthly_expected_profit_low'))}~{fmt_num(scenario.get('monthly_expected_profit_high'))} |"
        )
    for decision in ("SHORTLIST", "CONDITIONAL", "WATCH", "REJECT"):
        selected = [row for row in rows if row["decision"] == decision]
        if not selected:
            continue
        lines.extend(["", f"## {decision}", ""])
        for row in selected:
            source = row.get("source_candidate") or {}
            wholesale = source.get("wholesale") or {}
            lines.append(f"### {row['rank']}. {row.get('name') or row.get('candidate_id')}")
            lines.append("")
            if is_url(wholesale.get("url")):
                lines.append(f"- 도매: [{wholesale['url']}]({wholesale['url']})")
            lines.append(f"- 판정 근거: {'; '.join(row.get('decision_reasons') or ['게이트 통과'])}")
            lines.append(f"- 차별화 소구: {'; '.join((row.get('content_handoff') or {}).get('differentiators') or []) or 'UNKNOWN'}")
            evidence = row.get("evidence_urls") or []
            lines.append(f"- 근거 URL: {'; '.join(evidence[:8]) if evidence else 'UNKNOWN'}")
            lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_handoff(path: Path, rows: list[dict[str, Any]], created_at: str) -> None:
    payload = {"generated_at": created_at, "count": 0, "shortlist": []}
    for row in rows:
        if row["decision"] != "SHORTLIST":
            continue
        source = row.get("source_candidate") or {}
        economics = row.get("economics") or {}
        handoff = row.get("content_handoff") or {}
        payload["shortlist"].append({
            "candidate_id": row.get("candidate_id"),
            "name": row.get("name"),
            "wholesale_url": (source.get("wholesale") or {}).get("url"),
            "scores": row.get("scores"),
            "economics": economics,
            "sample_checks": handoff.get("sample_checks") or [],
            "differentiators": handoff.get("differentiators") or [],
            "proof_scenes": handoff.get("proof_scenes") or [],
            "gif_idea": handoff.get("gif_idea"),
            "evidence_urls": row.get("evidence_urls") or [],
        })
    payload["count"] = len(payload["shortlist"])
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    run = payload.get("run") or {}
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise SystemExit("입력 오류: candidates는 배열이어야 합니다.")
    ids = [candidate.get("id") for candidate in candidates if isinstance(candidate, dict)]
    if any(not value for value in ids) or len(ids) != len(set(ids)) or len(ids) != len(candidates):
        raise SystemExit("입력 오류: 모든 후보에는 중복되지 않는 id가 필요합니다.")

    params = get_params(run)
    rows = [evaluate_candidate(candidate, params) for candidate in candidates]
    limit = int(min(max(run.get("shortlist_limit", 5), 0), 5)) if is_number(run.get("shortlist_limit", 5)) else 5
    enforce_shortlist_limit(rows, limit)
    rows.sort(key=sort_key)
    for index, row in enumerate(rows, 1):
        row["rank"] = index

    created_at = iso_now()
    output = {
        "schema_version": "1.0",
        "generated_at": created_at,
        "source_input": str(args.input.resolve()),
        "run": run,
        "effective_parameters": params,
        "summary": {
            "candidate_count": len(rows),
            "shortlist_count": sum(1 for row in rows if row["decision"] == "SHORTLIST"),
            "conditional_count": sum(1 for row in rows if row["decision"] == "CONDITIONAL"),
            "watch_count": sum(1 for row in rows if row["decision"] == "WATCH"),
            "reject_count": sum(1 for row in rows if row["decision"] == "REJECT"),
        },
        "candidates": rows,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "evaluation.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(args.output_dir / "candidate-table.csv", rows)
    write_markdown(args.output_dir / "candidate-report.md", run, rows, created_at)
    write_handoff(args.output_dir / "handoff-shortlist.json", rows, created_at)
    print(json.dumps(output["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
