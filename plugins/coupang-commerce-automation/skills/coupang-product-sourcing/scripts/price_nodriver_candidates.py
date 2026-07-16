#!/usr/bin/env python3
"""Connect nodriver market evidence to the Rocket Growth pricing engine."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


def load_pricer(skill_dir: Path):
    path = skill_dir / "scripts" / "recommend_prices.py"
    spec = importlib.util.spec_from_file_location("recommend_prices", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_evidence_contract(skill_dir: Path):
    path = skill_dir / "scripts" / "evidence_contract.py"
    spec = importlib.util.spec_from_file_location("evidence_contract", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[가-힣A-Za-z0-9.]+", text or "") if len(t) >= 2}


def similarity(candidate_name: str, product_name: str) -> str:
    base = tokens(candidate_name)
    other = tokens(product_name)
    overlap = len(base & other) / max(1, len(base))
    if overlap >= 0.25:
        return "similar"
    return "unrelated"


def build_pricing_candidate(
    row: dict,
    *,
    rocket_growth_cost: float,
    fee_rate: float,
    min_market_samples: int = 5,
) -> tuple[dict, dict]:
    """Build a pricing row from verified supplier terms and like-for-like sale prices."""
    skill_dir = Path(__file__).resolve().parents[1]
    contract = load_evidence_contract(skill_dir)
    supplier_errors = contract.validate_supplier_terms(row)
    source_cost = None if supplier_errors else contract.cost_per_sale_bundle(row)
    sale_quantity = row.get("sale_bundle_quantity")
    market = []
    excluded = []
    for index, raw_product in enumerate(row.get("coupang_products") or []):
        if not isinstance(raw_product, dict):
            continue
        product = (
            contract.normalize_market_product(raw_product)
            if raw_product.get("price_nodes") is not None
            else dict(raw_product)
        )
        label = similarity(str(row.get("name") or ""), str(product.get("name") or ""))
        if label == "unrelated":
            excluded.append({"url": product.get("url"), "reason": "상품 유사도 불일치"})
            continue
        if product.get("price_verified") is not True or not isinstance(product.get("price"), (int, float)):
            excluded.append({"url": product.get("url"), "reason": product.get("price_error") or "현재 실판매가 미검증"})
            continue
        quantity = product.get("quantity")
        if quantity != sale_quantity:
            excluded.append({"url": product.get("url"), "reason": "판매 묶음 수량 불일치", "observed_quantity": quantity})
            continue
        market.append({
            "price": int(product["price"]), "price_verified": True, "quantity": quantity,
            "similarity": label, "is_ad": False,
            "product_group_id": re.sub(r"[?#].*$", "", str(product.get("url") or index)),
            "url": product.get("url"), "observed_at": product.get("observed_at"),
        })
    supplier_verified = not supplier_errors
    market_verified = len(market) >= min_market_samples
    candidate = {
        "id": row.get("candidate_id"), "name": row.get("name"),
        "url": row.get("wholesale_url") or row.get("url"),
        "supply_price": source_cost["supply_cost"] if source_cost else None,
        "wholesale_shipping_per_unit": source_cost["wholesale_shipping_per_sale_bundle"] if source_cost else None,
        "rocket_growth_cost": rocket_growth_cost,
        "other_cost": 0, "fee_rate_pct": fee_rate,
        "vat_mode": "excel_rocket_growth_simplified",
        "costs_vat_included": True, "input_vat_creditable": True,
        "market_prices": market,
        "required_bundle_quantity": sale_quantity,
        "require_verified_market_prices": True,
    }
    evidence = {
        "supplier_terms_verified": supplier_verified,
        "supplier_term_errors": supplier_errors,
        "market_prices_verified": market_verified,
        "verified_market_price_count": len(market),
        "excluded_market_products": excluded,
        "source_cost_per_sale_bundle": source_cost,
    }
    return candidate, evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--wholesale-shipping", type=float, help="폐기 예정: 검증된 supplier_terms 배송비만 사용")
    parser.add_argument("--rocket-growth-cost", type=float, default=3000)
    parser.add_argument("--fee-rate", type=float, default=10.8)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    rows = payload.get("candidates") or []
    pricer = load_pricer(Path(__file__).resolve().parents[1])
    params = {
        "base_margin_pct": 40,
        "stress_margin_pct": 30,
        "conditional_base_margin_pct": 35,
        "conditional_stress_margin_pct": 25,
        "stress_discount_pct": 10,
        "min_market_samples": 5,
    }
    out = []
    for row in rows:
        candidate, evidence = build_pricing_candidate(
            row, rocket_growth_cost=args.rocket_growth_cost, fee_rate=args.fee_rate,
            min_market_samples=params["min_market_samples"],
        )
        priced = pricer.evaluate(candidate, params)
        verification_blockers = list(evidence["supplier_term_errors"])
        if not evidence["market_prices_verified"]:
            verification_blockers.append(
                f"할인 후 실판매가·동일 묶음 표본 부족: {evidence['verified_market_price_count']}/{params['min_market_samples']}"
            )
        if verification_blockers:
            priced["decision"] = "PRICE_REVIEW_BLOCKED"
            priced["blockers"] = list(dict.fromkeys((priced.get("blockers") or []) + verification_blockers))
        merged = dict(row)
        merged.update(priced)
        merged.update(evidence)
        merged["decision"] = priced["decision"]
        merged["pricing_assumptions"] = {
            "source_cost_basis": "verified_supplier_terms_per_sale_bundle",
            "sale_bundle_quantity": row.get("sale_bundle_quantity"),
            "deprecated_wholesale_shipping_argument_ignored": args.wholesale_shipping,
            "rocket_growth_cost": args.rocket_growth_cost,
            "fee_rate_pct": args.fee_rate,
        }
        merged["market_similarity_rows"] = candidate["market_prices"]
        reviews = [int(re.sub(r"[^0-9]", "", str(p.get("review") or "")) or 0) for p in row.get("coupang_products") or []]
        merged["demand_verified"] = len(reviews) >= 5 and any(reviews)
        low_risk = not any(word in str(row.get("name") or "") for word in ("선풍기", "텀블러", "식물재배", "화장품", "식품", "유아", "전기"))
        merged["operations_safe"] = low_risk
        products = row.get("coupang_products") or []
        regular_rocket = sum(bool(p.get("rocket")) for p in products)
        seller_rocket = sum(bool(p.get("seller_rocket")) for p in products)
        merged["regular_rocket_count_top10"] = regular_rocket
        merged["seller_rocket_count_top10"] = seller_rocket
        if regular_rocket > 3:
            merged["coupang_retail_competition"] = "coupang_retail_present"
        elif regular_rocket or seller_rocket:
            merged["coupang_retail_competition"] = "seller_rocket_only"
        else:
            merged["coupang_retail_competition"] = "none"
        out.append(merged)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": "1.0", "candidates": out}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "candidates": len(out),
        "price_review": sum(r.get("decision") == "PRICE_REVIEW" for r in out),
        "conditional_price_review": sum(r.get("decision") == "CONDITIONAL_TEST_PRICE_REVIEW" for r in out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
