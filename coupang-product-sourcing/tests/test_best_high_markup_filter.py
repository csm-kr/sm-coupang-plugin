from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "coupang-best-high-markup-sourcing"
    / "scripts"
    / "filter_high_markup_candidates.py"
)
SKILL = ROOT / "coupang-best-high-markup-sourcing" / "SKILL.md"


def load_filter_module():
    spec = importlib.util.spec_from_file_location("filter_high_markup_candidates", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def candidate(*, unit_price: int = 5000, sale_price: int = 20000, reviews: int = 1):
    return {
        "candidate_id": "BEST-001",
        "name": "베스트 생활용품",
        "wholesale_url": "https://domeggook.com/12345678",
        "sale_bundle_quantity": 1,
        "procurement_quantity": 2,
        "supplier_terms": {
            "verified": True,
            "unit_supply_price": unit_price,
            "minimum_order_qty": 2,
            "order_increment": 1,
            "wholesale_shipping_total": 3000,
            "observed_at": "2026-07-17T16:00:00+09:00",
            "source_url": "https://domeggook.com/12345678",
        },
        "coupang_products": [
            {
                "name": "베스트 생활용품, 1개",
                "url": "https://www.coupang.com/vp/products/100",
                "quantity": 1,
                "sale_price": sale_price,
                "list_price": 39000,
                "price_verified": True,
                "review_count": reviews,
                "similarity": "identical",
                "identity_verified": True,
                "observed_at": "2026-07-17T16:05:00+09:00",
            }
        ],
    }


def test_exact_boundaries_pass_as_discovery_match():
    mod = load_filter_module()

    result = mod.evaluate_candidate(candidate())

    assert result["decision"] == "HIGH_MARKUP_DISCOVERY"
    assert result["unit_supply_price"] == 5000
    assert result["qualifying_sellers"][0]["markup_multiple"] == 4.0
    assert result["qualifying_sellers"][0]["review_count"] == 1


def test_configurable_multiple_is_an_existential_pair_gate_and_ignores_cheaper_listings():
    mod = load_filter_module()
    row = candidate(unit_price=3000, sale_price=9000, reviews=2)
    row["coupang_products"].insert(0, {
        **row["coupang_products"][0],
        "name": "더 싼 동일 상품",
        "url": "https://www.coupang.com/vp/products/50",
        "sale_price": 4500,
        "review_count": 300,
    })

    result = mod.evaluate_candidate(row, min_markup_multiple=3)

    assert result["decision"] == "HIGH_MARKUP_DISCOVERY"
    assert len(result["qualifying_pairs"]) == 1
    assert result["qualifying_pairs"][0]["markup_multiple"] == 3.0
    assert result["qualifying_pairs"][0]["coupang_url"].endswith("/100")
    assert result["discovery_rule"] == "EXISTS_SALES_EVIDENCED_PAIR_AT_OR_ABOVE_MULTIPLE"
    assert result["lower_price_listings_do_not_disqualify"] is True


def test_review_or_satisfaction_badge_can_prove_the_pair_has_sales_evidence():
    mod = load_filter_module()
    review_pair = mod.evaluate_candidate(candidate(reviews=1))
    satisfaction_row = candidate(reviews=0)
    satisfaction_row["coupang_products"][0].update({
        "satisfaction_signal": "100명 이상 만족했어요",
        "satisfaction_count": 100,
    })

    satisfaction_pair = mod.evaluate_candidate(satisfaction_row)

    assert review_pair["decision"] == "HIGH_MARKUP_DISCOVERY"
    assert review_pair["qualifying_pairs"][0]["sales_evidence"]["type"] == "review"
    assert satisfaction_pair["decision"] == "HIGH_MARKUP_DISCOVERY"
    assert satisfaction_pair["qualifying_pairs"][0]["sales_evidence"] == {
        "type": "satisfaction_badge",
        "count": 100,
        "label": "100명 이상 만족했어요",
    }


def test_filter_rejects_price_over_5000_and_bundle_mismatch():
    mod = load_filter_module()
    over_limit = mod.evaluate_candidate(candidate(unit_price=5001))
    bundled = candidate()
    bundled["sale_bundle_quantity"] = 2

    assert over_limit["decision"] == "FILTERED_OUT"
    assert "UNIT_SUPPLY_PRICE_OVER_5000" in over_limit["blockers"]
    assert mod.evaluate_candidate(bundled)["decision"] == "FILTERED_OUT"


def test_filter_uses_current_price_and_requires_exact_verified_identity():
    mod = load_filter_module()
    row = candidate(sale_price=19999, reviews=5)
    row["coupang_products"][0]["list_price"] = 50000
    similar = candidate(sale_price=25000, reviews=30)
    similar["coupang_products"][0]["similarity"] = "similar"

    assert mod.evaluate_candidate(row)["decision"] == "FILTERED_OUT"
    assert mod.evaluate_candidate(similar)["decision"] == "FILTERED_OUT"


def test_filter_honors_a_stricter_review_threshold_and_requires_verified_supplier_terms():
    mod = load_filter_module()
    too_few_reviews = mod.evaluate_candidate(candidate(reviews=4), min_review_count=5)
    unverified = candidate(reviews=10)
    unverified["supplier_terms"]["verified"] = False

    assert too_few_reviews["decision"] == "FILTERED_OUT"
    blocked = mod.evaluate_candidate(unverified)
    assert blocked["decision"] == "PRICE_REVIEW_BLOCKED"
    assert "SUPPLIER_TERMS_UNVERIFIED" in blocked["blockers"]


def test_filter_parses_existing_parenthesized_review_text():
    mod = load_filter_module()
    row = candidate(reviews=0)
    product = row["coupang_products"][0]
    product.pop("review_count")
    product["review"] = "(1,234)"

    result = mod.evaluate_candidate(row)

    assert result["decision"] == "HIGH_MARKUP_DISCOVERY"
    assert result["qualifying_sellers"][0]["review_count"] == 1234


def test_highest_demand_backed_price_sets_the_upper_profit_reference():
    mod = load_filter_module()
    row = candidate(unit_price=3000, sale_price=12000, reviews=30)
    row["procurement_quantity"] = 10
    row["supplier_terms"]["minimum_order_qty"] = 10
    row["coupang_products"].extend([
        {
            **row["coupang_products"][0],
            "name": "베스트 생활용품 고가 판매자",
            "url": "https://www.coupang.com/vp/products/200",
            "sale_price": 24000,
            "review_count": 5,
        },
        {
            **row["coupang_products"][0],
            "name": "판매 근거 없는 최고가 등록",
            "url": "https://www.coupang.com/vp/products/300",
            "sale_price": 30000,
            "review_count": 0,
        },
    ])

    result = mod.evaluate_candidate(row)

    assert result["decision"] == "HIGH_MARKUP_DISCOVERY"
    assert result["market_price_range"] == {
        "basis": "demand_backed_verified_current_sale_price",
        "count": 2,
        "min": 12000,
        "max": 24000,
        "excluded_no_demand_evidence_count": 1,
        "review_evidence_is_proxy": True,
    }
    assert result["high_price_reference"]["sale_price"] == 24000
    assert result["high_price_reference"]["url"].endswith("/200")
    assert result["high_price_reference"]["basis"] == "highest_demand_backed_verified_current_sale_price"
    assert result["profitability_range"]["low"]["sale_price"] == 12000
    assert result["profitability_range"]["high"]["sale_price"] == 24000
    assert result["profitability_range"]["low"]["margin_pct"] < result["profitability_range"]["high"]["margin_pct"]


def test_html_report_shows_actual_products_and_profitability_range():
    mod = load_filter_module()
    row = candidate(unit_price=3000, sale_price=12000, reviews=30)
    row["coupang_products"].append({
        **row["coupang_products"][0],
        "name": "고가 판매 근거 상품",
        "url": "https://www.coupang.com/vp/products/200",
        "sale_price": 24000,
        "review_count": 5,
    })

    report = mod.render_html(mod.filter_candidates([row]))

    assert "베스트 생활용품" in report
    assert "도매꾹 상품·개당 원가" in report
    assert "쿠팡 판매 상품·현재가" in report
    assert "가격 배수" in report
    assert "판매 근거" in report
    assert "8.00배" in report
    assert "고가 판매 근거 상품" in report
    assert "https://www.coupang.com/vp/products/200" in report
    assert "낮은 가격의 다른 등록은 이 pair를 탈락시키지 않습니다" in report


def test_skill_contract_files_do_not_end_with_an_extra_blank_line():
    skill_root = SKILL.parent
    contract_files = [
        SKILL,
        skill_root / "AGENTS.md",
        skill_root / "agents" / "openai.yaml",
        skill_root / "references" / "input-output-contract.md",
    ]

    for path in contract_files:
        assert not path.read_text(encoding="utf-8").endswith("\n\n"), path


def test_skill_contract_samples_best_and_keeps_matches_out_of_shortlist():
    text = SKILL.read_text(encoding="utf-8")

    assert "sample_top150.py" in text
    assert "개당 공급가 상한" in text
    assert "최소 가격 배수" in text
    assert "리뷰 1개 이상" in text
    assert "100명 이상 만족" in text
    assert "낮은 가격" in text
    assert "HIGH_MARKUP_DISCOVERY" in text
    assert "SHORTLIST" in text
    assert "도매꾹 Best" in text


def test_skill_contract_uses_real_categories_and_requires_an_actual_pair_report():
    text = SKILL.read_text(encoding="utf-8")
    contract = (SKILL.parent / "references" / "input-output-contract.md").read_text(encoding="utf-8")

    for category in (
        "전체",
        "패션잡화/화장품",
        "의류/언더웨어",
        "출산/유아동/완구",
        "가구/생활/취미",
        "스포츠/건강/식품",
        "가전/휴대폰/산업",
    ):
        assert category in text
    assert "카테고리 선택은 필수가 아니다" in text
    assert "--html-output" in text
    assert "도매꾹 상품·개당 원가 ↔ 쿠팡 판매상품·현재가" in text
    assert "qualifying_pairs" in contract
    assert "lower_price_listings_do_not_disqualify" in contract


def test_failed_report_contract_preserves_the_sampled_domeggook_items():
    text = SKILL.read_text(encoding="utf-8")
    contract = (SKILL.parent / "references" / "input-output-contract.md").read_text(encoding="utf-8")

    assert "실패 이유" in text
    assert "도매꾹 샘플" in text
    assert "sampled_items" in contract
    assert "실패·차단" in contract
