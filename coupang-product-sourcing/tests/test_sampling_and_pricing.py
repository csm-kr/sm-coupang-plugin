from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_sampling_spans_rank_bands():
    mod = load("sample_top150")
    items = []
    for rank in (1, 2, 10, 35, 50, 70, 80, 110, 145):
        items.append({
            "rank": rank, "name": f"생활용품 후보 {rank}",
            "url": f"https://domeggook.com/{rank}", "supply_price": 3000 + rank,
            "moq": 1, "supplier": f"S{rank % 4}",
        })
    selected, rejected = mod.sample(items, 6)
    assert not rejected
    assert len(selected) == 6
    assert {row["rank_band"] for row in selected} == {"top", "middle", "tail"}


def test_sampling_covers_categories_origins_and_pool_types():
    mod = load("sample_top150")
    items = []
    rank = 1
    for category in ("생활", "패션", "스포츠"):
        for origin in ("domestic", "imported"):
            for pool_type in ("category_top150", "challenge_best"):
                items.append({
                    "rank": rank, "name": f"{category} {origin} 상품 {rank}",
                    "url": f"https://domeggook.com/{1000 + rank}", "supply_price": 4000,
                    "moq": 1, "supplier": f"SUP{rank}", "category": category,
                    "origin_scope": origin, "pool_type": pool_type,
                })
                rank += 12
    selected, _ = mod.sample(items, 9)
    assert len({row["category"] for row in selected}) == 3
    assert {row["origin_scope"] for row in selected} == {"domestic", "imported"}
    assert {row["pool_type"] for row in selected} == {"category_top150", "challenge_best"}


def test_pricing_rejects_market_mismatch_and_keeps_good_candidate():
    mod = load("recommend_prices")
    params = {"base_margin_pct": 40, "stress_margin_pct": 30, "stress_discount_pct": 10, "min_market_samples": 5}
    tumbler = {
        "id": "T1", "name": "1.18L 텀블러", "supply_price": 5900,
        "wholesale_shipping_per_unit": 0, "rocket_growth_cost": 3000,
        "other_cost": 0, "fee_rate_pct": 10.8, "demand_signal_score": 60,
        "vat_mode": "excel_rocket_growth_simplified", "costs_vat_included": True, "input_vat_creditable": True,
        "market_prices": [{"price": p, "similarity": "near_identical", "is_ad": False, "product_group_id": f"T{i}"}
                          for i, p in enumerate([8900, 9500, 9900, 10310, 10900, 10900, 12300, 12800, 13900, 16940, 19800])],
    }
    good = {
        "id": "G1", "name": "가상 저원가 생활용품", "supply_price": 2500,
        "wholesale_shipping_per_unit": 0, "rocket_growth_cost": 2500,
        "other_cost": 0, "fee_rate_pct": 10.8, "demand_signal_score": 70,
        "vat_mode": "excel_rocket_growth_simplified", "costs_vat_included": True, "input_vat_creditable": True,
        "market_prices": [{"price": p, "similarity": "near_identical", "is_ad": False, "product_group_id": f"G{i}"}
                          for i, p in enumerate([12900, 13900, 14900, 15900, 16900, 17900, 18900])],
    }
    bad_result = mod.evaluate(tumbler, params)
    good_result = mod.evaluate(good, params)
    assert bad_result["decision"] == "REJECT"
    assert bad_result["market_price_distribution"]["p50"] == 10900
    assert bad_result["final_floor_price"] == 19900
    assert good_result["decision"] == "PRICE_REVIEW"
    assert good_result["price_options"]["recommended"]["base"]["margin_pct"] >= 40
    assert good_result["price_options"]["recommended"]["stress"]["margin_pct"] >= 30


def test_pricing_allows_margin_between_35_and_40_as_conditional():
    mod = load("recommend_prices")
    params = {
        "base_margin_pct": 40,
        "stress_margin_pct": 30,
        "conditional_base_margin_pct": 35,
        "conditional_stress_margin_pct": 25,
        "stress_discount_pct": 10,
        "min_market_samples": 5,
    }
    candidate = {
        "id": "C35", "name": "조건부 마진 상품",
        "supply_price": 2600, "wholesale_shipping_per_unit": 1500,
        "rocket_growth_cost": 3000, "other_cost": 0, "fee_rate_pct": 10.8,
        "vat_mode": "excel_rocket_growth_simplified",
        "costs_vat_included": True, "input_vat_creditable": True,
        "market_prices": [
            {"price": price, "similarity": "identical", "is_ad": False, "product_group_id": f"C{i}"}
            for i, price in enumerate([14500, 14700, 14900, 15100, 15300])
        ],
    }

    result = mod.evaluate(candidate, params)

    assert result["decision"] == "CONDITIONAL_TEST_PRICE_REVIEW"
    assert result["margin_tier"] == "conditional_35_40"
    assert 35 <= result["price_options"]["recommended"]["base"]["margin_pct"] < 40
    assert result["price_options"]["recommended"]["stress"]["margin_pct"] >= 25


def test_candidate_evaluator_classifies_35_to_40_margin_as_conditional():
    mod = load("evaluate_candidates")
    economics = {
        "base": {"contribution_margin_pct": 37.4},
        "stress": {"contribution_margin_pct": 28.2},
    }
    params = dict(mod.DEFAULT_PARAMS)

    assert mod.classify_margin_tier(economics, params) == "conditional_35_40"


def test_pricing_fails_closed_on_invalid_costs_and_vat_contract():
    mod = load("recommend_prices")
    row = {
        "id": "BAD", "name": "잘못된 입력", "supply_price": -1,
        "wholesale_shipping_per_unit": 0, "rocket_growth_cost": 1000,
        "fee_rate_pct": 120,
        "market_prices": [{"price": 10000 + i * 100, "similarity": "identical", "product_group_id": str(i)} for i in range(5)],
    }
    result = mod.evaluate(row, {"min_market_samples": 5})
    assert result["decision"] == "PRICE_REVIEW_BLOCKED"
    assert any("부가세" in reason for reason in result["blockers"])
    assert any("판매수수료율" in reason for reason in result["blockers"])


def test_price_distribution_does_not_mix_similar_groups_or_duplicate_skus():
    mod = load("recommend_prices")
    candidate = {
        "market_prices": [
            {"price": 10000 + i * 100, "similarity": "identical", "product_group_id": f"I{i}"} for i in range(5)
        ] + [
            {"price": 50000 + i * 100, "similarity": "similar", "product_group_id": f"S{i}"} for i in range(5)
        ] + [
            {"price": 99999, "similarity": "identical", "product_group_id": "I0"}
        ]
    }
    group, prices = mod.comparable_prices(candidate, 5)
    assert group == "identical"
    assert len(prices) == 5
    assert max(prices) < 50000
