#!/usr/bin/env python3
"""Validate supplier offer terms and normalize current Coupang sale prices.

The contract is intentionally fail-closed: ambiguous prices and unverified
supplier terms cannot enter bundle-cost or margin calculations.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SALE_PRICE_CLASS_MARKERS = (
    "productprice_pricevalue",
    "sales-price",
    "sale-price",
    "discount-price",
    "final-price",
)
LIST_PRICE_CLASS_MARKERS = (
    "origin-price",
    "original-price",
    "list-price",
    "regular-price",
)
MONEY_RE = re.compile(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d+)\s*원")


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0 else None


def _nonnegative_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number >= 0 else None


def _positive_int(value: Any) -> int | None:
    number = _positive_number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _iso_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return observed.tzinfo is not None


def validate_supplier_terms(row: dict[str, Any]) -> list[str]:
    """Return blockers for supplier MOQ, increment, price, shipping and bundle."""
    errors: list[str] = []
    terms = row.get("supplier_terms")
    if not isinstance(terms, dict) or terms.get("verified") is not True:
        return ["공급처 조건 검증 미완료"]

    unit_price = _positive_number(terms.get("unit_supply_price"))
    minimum = _positive_int(terms.get("minimum_order_qty"))
    increment = _positive_int(terms.get("order_increment"))
    shipping = _nonnegative_number(terms.get("wholesale_shipping_total"))
    if unit_price is None:
        errors.append("공급처 단가 검증값 오류")
    if minimum is None:
        errors.append("공급처 MOQ 검증값 오류")
    if increment is None:
        errors.append("공급처 구매단위 검증값 오류")
    if shipping is None:
        errors.append("공급처 배송비 검증값 오류")
    if not _iso_datetime(terms.get("observed_at")):
        errors.append("공급처 조건 조사시각 누락")
    if not _http_url(terms.get("source_url")):
        errors.append("공급처 조건 원문 URL 누락")

    legacy_price = _positive_number(row.get("supply_price"))
    if unit_price is not None and legacy_price != unit_price:
        errors.append(f"공급가 불일치: 입력 {row.get('supply_price')} / 검증 {unit_price:g}")
    legacy_moq = _positive_int(row.get("moq"))
    if minimum is not None and legacy_moq != minimum:
        errors.append(f"MOQ 불일치: 입력 {row.get('moq')} / 검증 {minimum}")

    sale_quantity = _positive_int(row.get("sale_bundle_quantity"))
    procurement = _positive_int(row.get("procurement_quantity"))
    if sale_quantity is None:
        errors.append("판매 묶음 수량 오류")
    if procurement is None:
        errors.append("매입 수량 오류")
    if minimum is not None and procurement is not None and procurement < minimum:
        errors.append(f"매입 수량이 MOQ 미달: {procurement}/{minimum}")
    if sale_quantity is not None and procurement is not None and procurement < sale_quantity:
        errors.append("매입 수량이 판매 묶음 수량보다 작음")
    if minimum is not None and increment is not None and procurement is not None:
        if (procurement - minimum) % increment != 0:
            errors.append("매입 수량이 공급처 구매단위와 불일치")
    return errors


def cost_per_sale_bundle(row: dict[str, Any]) -> dict[str, float]:
    """Calculate verified source cost for one sale bundle."""
    errors = validate_supplier_terms(row)
    if errors:
        raise ValueError("; ".join(errors))
    terms = row["supplier_terms"]
    sale_quantity = int(row["sale_bundle_quantity"])
    procurement = int(row["procurement_quantity"])
    supply_cost = float(terms["unit_supply_price"]) * sale_quantity
    shipping = float(terms["wholesale_shipping_total"]) / procurement * sale_quantity
    return {
        "supply_cost": supply_cost,
        "wholesale_shipping_per_sale_bundle": shipping,
        "fixed_source_cost": supply_cost + shipping,
    }


def extract_bundle_quantity(text: str) -> int:
    """Extract explicit multi-pack quantity; an unmarked product is one unit."""
    value = str(text or "")
    plus = re.search(r"(?<!\d)(\d+)\s*\+\s*(\d+)(?!\d)", value)
    if plus:
        return int(plus.group(1)) + int(plus.group(2))
    for pattern in (
        r"(?<!\d)(\d+)\s*[Pp](?:\s*세트)?",
        r"(?<!\d)(\d+)\s*종\s*세트",
        r"(?<!\d)(\d+)\s*(?:개|매|장|입|팩)(?:\s*세트)?",
        r"(?<!\d)(\d+)\s*세트",
    ):
        match = re.search(pattern, value)
        if match:
            return int(match.group(1))
    return 1


def _money_values(text: Any) -> list[int]:
    return [int(value.replace(",", "")) for value in MONEY_RE.findall(str(text or ""))]


def _semantic_prices(nodes: Any, markers: tuple[str, ...], roles: tuple[str, ...]) -> set[int]:
    values: set[int] = set()
    if not isinstance(nodes, list):
        return values
    for node in nodes:
        if not isinstance(node, dict):
            continue
        class_name = str(node.get("class_name") or "").lower()
        role = str(node.get("role") or "").lower()
        if role not in roles and not any(marker in class_name for marker in markers):
            continue
        prices = _money_values(node.get("text"))
        if len(prices) == 1 and prices[0] > 0:
            values.add(prices[0])
    return values


def normalize_market_product(product: dict[str, Any]) -> dict[str, Any]:
    """Normalize one Coupang card using semantically labelled current prices."""
    normalized = dict(product)
    nodes = product.get("price_nodes")
    sale_prices = _semantic_prices(nodes, SALE_PRICE_CLASS_MARKERS, ("sale_price",))
    list_prices = _semantic_prices(nodes, LIST_PRICE_CLASS_MARKERS, ("list_price",))
    normalized["quantity"] = extract_bundle_quantity(str(product.get("name") or ""))
    normalized["sale_price"] = next(iter(sale_prices)) if len(sale_prices) == 1 else None
    normalized["list_price"] = next(iter(list_prices)) if len(list_prices) == 1 else None
    normalized["price_basis"] = "search_card_current_sale_price"
    if len(sale_prices) == 1:
        normalized["price"] = normalized["sale_price"]
        normalized["price_verified"] = True
        normalized["price_error"] = None
    else:
        normalized["price"] = None
        normalized["price_verified"] = False
        normalized["price_error"] = (
            "현재 실판매가 후보가 여러 개여서 가격 확정 불가"
            if len(sale_prices) > 1
            else "의미가 확인된 현재 실판매가 가격 노드 없음"
        )
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    rows = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        rows = [payload] if isinstance(payload, dict) else []
    results = []
    failed = False
    for row in rows:
        errors = validate_supplier_terms(row) if isinstance(row, dict) else ["후보 행 형식 오류"]
        failed = failed or bool(errors)
        results.append({"candidate_id": row.get("candidate_id") if isinstance(row, dict) else None, "errors": errors})
    result = {"schema_version": "1.0", "valid": not failed, "results": results}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
