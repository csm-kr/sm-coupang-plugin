from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def verified_supplier_terms(*, unit_price: int, moq: int, shipping: int) -> dict:
    return {
        "verified": True,
        "unit_supply_price": unit_price,
        "minimum_order_qty": moq,
        "order_increment": moq,
        "wholesale_shipping_total": shipping,
        "observed_at": "2026-07-16T10:00:00+09:00",
        "source_url": "https://domeggook.com/7509189",
    }


def test_supplier_terms_reject_listing_moq_mismatch():
    mod = load("evidence_contract")
    row = {
        "supply_price": 55,
        "moq": 1,
        "sale_bundle_quantity": 100,
        "procurement_quantity": 100,
        "supplier_terms": verified_supplier_terms(unit_price=55, moq=100, shipping=3000),
    }
    errors = mod.validate_supplier_terms(row)
    assert any("MOQ 불일치" in error for error in errors)


def test_hair_tie_bundle_cost_multiplies_unit_price_and_allocates_shipping():
    mod = load("evidence_contract")
    row = {
        "supply_price": 55,
        "moq": 100,
        "sale_bundle_quantity": 100,
        "procurement_quantity": 100,
        "supplier_terms": verified_supplier_terms(unit_price=55, moq=100, shipping=3000),
    }
    result = mod.cost_per_sale_bundle(row)
    assert result["supply_cost"] == 5500
    assert result["wholesale_shipping_per_sale_bundle"] == 3000
    assert result["fixed_source_cost"] == 8500


def test_cooling_scarf_moq_four_is_preserved():
    mod = load("evidence_contract")
    row = {
        "supply_price": 1500,
        "moq": 4,
        "sale_bundle_quantity": 2,
        "procurement_quantity": 4,
        "supplier_terms": verified_supplier_terms(unit_price=1500, moq=4, shipping=2500),
    }
    assert mod.validate_supplier_terms(row) == []
    result = mod.cost_per_sale_bundle(row)
    assert result["supply_cost"] == 3000
    assert result["wholesale_shipping_per_sale_bundle"] == 1250


def test_verified_sale_price_wins_over_discount_reference_price():
    mod = load("evidence_contract")
    product = {
        "name": "나쥬랑 아이스 넥쿨러 쿨 스카프, 2개",
        "price_nodes": [
            {"class_name": "origin-price", "text": "10,000원"},
            {"class_name": "ProductPrice_priceValue__abc", "text": "6,900원"},
        ],
    }
    result = mod.normalize_market_product(product)
    assert result["sale_price"] == 6900
    assert result["list_price"] == 10000
    assert result["price"] == 6900
    assert result["price_verified"] is True
    assert result["price_basis"] == "search_card_current_sale_price"
    assert result["quantity"] == 2


def test_ambiguous_price_nodes_fail_closed_instead_of_choosing_a_value():
    mod = load("evidence_contract")
    product = {
        "name": "가격 근거 불명 상품",
        "price_nodes": [
            {"class_name": "price-container", "text": "9,900원 26,900원"},
        ],
    }
    result = mod.normalize_market_product(product)
    assert result["price"] is None
    assert result["price_verified"] is False
    assert "가격" in result["price_error"]


def test_bundle_quantity_parses_piece_markers_and_one_plus_one():
    mod = load("evidence_contract")
    assert mod.extract_bundle_quantity("트위스트 꼬임링 100P 세트") == 100
    assert mod.extract_bundle_quantity("쿨 스카프 블루 3개") == 3
    assert mod.extract_bundle_quantity("아이스 넥쿨러 1+1") == 2
    assert mod.extract_bundle_quantity("국내산 순면 스카프 손수건 5개세트") == 5
    assert mod.extract_bundle_quantity("플라워 손수건 5종세트") == 5
    assert mod.extract_bundle_quantity("국산 여성 손수건 3장세트") == 3


def test_coupang_structural_price_roles_separate_sale_price_from_del_price():
    mod = load("evidence_contract")
    product = {
        "name": "로튼 국산 면스카프 손수건 1+1",
        "price_nodes": [
            {
                "role": "list_price",
                "tag_name": "DEL",
                "class_name": "fw-line-through fw-text-bluegray-600",
                "text": "9,900원",
            },
            {
                "role": "sale_price",
                "tag_name": "DIV",
                "class_name": "fw-text-[20px]/[24px] fw-font-bold",
                "text": "7,700원",
            },
        ],
    }
    result = mod.normalize_market_product(product)
    assert result["sale_price"] == 7700
    assert result["list_price"] == 9900
    assert result["price_verified"] is True
    assert result["quantity"] == 2


def test_coupang_collector_card_script_captures_product_thumbnail_url():
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = load("collect_coupang_nodriver")
    script = mod.build_card_extract_script(5)
    assert "image_url" in script
    assert "currentSrc" in script
    assert ".slice(0,5)" in script


def test_coupang_collector_keeps_explicit_candidate_id_with_wholesale_url_only():
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = load("collect_coupang_nodriver")
    row = {
        "candidate_id": "43946300-m",
        "wholesale_url": "https://domeggook.com/43946300",
        "search_keyword": "모던 체크 규조토 발매트 40x60",
    }

    assert mod.resolve_candidate_id(row, row["search_keyword"]) == "43946300-m"


def test_execution_guide_backpack_example_uses_verified_moq_two():
    guide_path = next(
        (parent / "docs" / "SOURCING-EXECUTION-GUIDE.md" for parent in (ROOT, *ROOT.parents)
         if (parent / "docs" / "SOURCING-EXECUTION-GUIDE.md").exists()),
        None,
    )
    assert guide_path is not None
    guide = guide_path.read_text(encoding="utf-8-sig")
    example = guide.split('"candidate_id": "7215172"', 1)[1].split("```", 1)[0]

    assert '"moq": 2' in example
    assert '"procurement_quantity": 2' in example
    assert '"minimum_order_qty": 2' in example


def test_pricing_candidate_uses_verified_bundle_cost_and_matching_sale_prices_only():
    mod = load("price_nodriver_candidates")
    row = {
        "candidate_id": "66433446",
        "name": "아이스 쿨링 스카프",
        "url": "https://domeggook.com/66433446",
        "supply_price": 1500,
        "moq": 4,
        "sale_bundle_quantity": 2,
        "procurement_quantity": 4,
        "supplier_terms": verified_supplier_terms(unit_price=1500, moq=4, shipping=2500),
        "coupang_products": [
            {
                "name": f"아이스 쿨링 스카프 {index} 2개",
                "price": 6900 + index * 100,
                "price_verified": True,
                "quantity": 2,
                "url": f"https://www.coupang.com/vp/products/{index}",
            }
            for index in range(5)
        ] + [{
            "name": "아이스 쿨링 스카프 3개",
            "price": 5900,
            "price_verified": True,
            "quantity": 3,
            "url": "https://www.coupang.com/vp/products/wrong-bundle",
        }],
    }
    candidate, evidence = mod.build_pricing_candidate(
        row, rocket_growth_cost=3000, fee_rate=10.8, min_market_samples=5
    )
    assert candidate["supply_price"] == 3000
    assert candidate["wholesale_shipping_per_unit"] == 1250
    assert len(candidate["market_prices"]) == 5
    assert evidence["supplier_terms_verified"] is True
    assert evidence["market_prices_verified"] is True
    assert evidence["excluded_market_products"][0]["reason"] == "판매 묶음 수량 불일치"
