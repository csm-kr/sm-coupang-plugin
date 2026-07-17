#!/usr/bin/env python3
"""Filter verified Domeggook Best candidates by a one-unit high-markup signal.

This is a discovery gate, not a SHORTLIST or profit approval. It deliberately
fails closed when supplier terms, current sale price, bundle quantity, or exact
product identity are not verified.
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


DEFAULT_MAX_SUPPLY_PRICE = 5000.0
DEFAULT_MIN_MARKUP_MULTIPLE = 4.0
DEFAULT_MIN_REVIEW_COUNT = 5
REVIEW_COUNT_RE = re.compile(r"(?<!\d)(\d[\d,]*)")


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


def _timezone_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return observed.tzinfo is not None


def parse_review_count(product: dict[str, Any]) -> int | None:
    """Read a normalized count or legacy Coupang text such as ``(1,234)``."""
    count = product.get("review_count")
    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
        return count
    if isinstance(count, float) and math.isfinite(count) and count >= 0 and count.is_integer():
        return int(count)
    match = REVIEW_COUNT_RE.search(str(product.get("review") or ""))
    return int(match.group(1).replace(",", "")) if match else None


def validate_supplier_candidate(candidate: dict[str, Any]) -> list[str]:
    """Validate the source fields required before applying the discovery gate."""
    blockers: list[str] = []
    terms = candidate.get("supplier_terms")
    if not isinstance(terms, dict) or terms.get("verified") is not True:
        return ["SUPPLIER_TERMS_UNVERIFIED"]

    unit_price = _positive_number(terms.get("unit_supply_price"))
    minimum = _positive_int(terms.get("minimum_order_qty"))
    increment = _positive_int(terms.get("order_increment"))
    shipping = _nonnegative_number(terms.get("wholesale_shipping_total"))
    procurement = _positive_int(candidate.get("procurement_quantity"))
    sale_bundle = _positive_int(candidate.get("sale_bundle_quantity"))

    if unit_price is None:
        blockers.append("UNIT_SUPPLY_PRICE_UNVERIFIED")
    if minimum is None:
        blockers.append("MOQ_UNVERIFIED")
    if increment is None:
        blockers.append("ORDER_INCREMENT_UNVERIFIED")
    if shipping is None:
        blockers.append("WHOLESALE_SHIPPING_UNVERIFIED")
    if procurement is None:
        blockers.append("PROCUREMENT_QUANTITY_UNVERIFIED")
    if sale_bundle is None:
        blockers.append("SALE_BUNDLE_QUANTITY_UNVERIFIED")
    if not _timezone_datetime(terms.get("observed_at")):
        blockers.append("SUPPLIER_OBSERVED_AT_UNVERIFIED")
    if not _http_url(terms.get("source_url")):
        blockers.append("SUPPLIER_SOURCE_URL_UNVERIFIED")

    if minimum is not None and procurement is not None and procurement < minimum:
        blockers.append("PROCUREMENT_BELOW_MOQ")
    if minimum is not None and increment is not None and procurement is not None:
        if procurement >= minimum and (procurement - minimum) % increment != 0:
            blockers.append("PROCUREMENT_INCREMENT_MISMATCH")
    if sale_bundle is not None and procurement is not None and procurement < sale_bundle:
        blockers.append("PROCUREMENT_BELOW_SALE_BUNDLE")
    return blockers


def _qualifying_seller(
    product: dict[str, Any],
    unit_supply_price: float,
    min_markup_multiple: float,
    min_review_count: int,
) -> dict[str, Any] | None:
    if product.get("similarity") != "identical" or product.get("identity_verified") is not True:
        return None
    if _positive_int(product.get("quantity")) != 1:
        return None
    if product.get("price_verified") is not True:
        return None
    sale_price = _positive_number(product.get("sale_price"))
    if sale_price is None:
        return None
    review_count = parse_review_count(product)
    if review_count is None or review_count < min_review_count:
        return None
    if not _http_url(product.get("url")) or not _timezone_datetime(product.get("observed_at")):
        return None

    markup_multiple = sale_price / unit_supply_price
    if markup_multiple + 1e-12 < min_markup_multiple:
        return None
    return {
        "name": product.get("name"),
        "url": product.get("url"),
        "seller": product.get("seller"),
        "sale_price": sale_price,
        "quantity": 1,
        "review_count": review_count,
        "markup_multiple": round(markup_multiple, 4),
        "similarity": "identical",
        "identity_verified": True,
        "observed_at": product.get("observed_at"),
    }


def evaluate_candidate(
    candidate: dict[str, Any],
    *,
    max_supply_price: float = DEFAULT_MAX_SUPPLY_PRICE,
    min_markup_multiple: float = DEFAULT_MIN_MARKUP_MULTIPLE,
    min_review_count: int = DEFAULT_MIN_REVIEW_COUNT,
) -> dict[str, Any]:
    """Apply the user's discovery thresholds to one fully enriched candidate."""
    result = {
        "candidate_id": candidate.get("candidate_id") or candidate.get("id"),
        "name": candidate.get("name"),
        "wholesale_url": candidate.get("wholesale_url") or candidate.get("url"),
        "decision": "FILTERED_OUT",
        "unit_supply_price": None,
        "qualifying_sellers": [],
        "blockers": [],
        "next_gate": "FULL_SOURCING_REVIEW_REQUIRED",
    }

    source_blockers = validate_supplier_candidate(candidate)
    if source_blockers:
        result["decision"] = "PRICE_REVIEW_BLOCKED"
        result["blockers"] = source_blockers
        return result

    unit_supply_price = float(candidate["supplier_terms"]["unit_supply_price"])
    result["unit_supply_price"] = unit_supply_price
    if unit_supply_price > max_supply_price:
        result["blockers"].append(f"UNIT_SUPPLY_PRICE_OVER_{int(max_supply_price)}")
        return result
    if int(candidate["sale_bundle_quantity"]) != 1:
        result["blockers"].append("SALE_BUNDLE_NOT_ONE_UNIT")
        return result

    products = candidate.get("coupang_products")
    if not isinstance(products, list):
        result["blockers"].append("COUPANG_PRODUCTS_UNAVAILABLE")
        return result

    qualifying = [
        seller
        for product in products
        if isinstance(product, dict)
        for seller in [
            _qualifying_seller(
                product,
                unit_supply_price,
                min_markup_multiple,
                min_review_count,
            )
        ]
        if seller is not None
    ]
    qualifying.sort(key=lambda row: (-row["markup_multiple"], -row["review_count"]))
    result["qualifying_sellers"] = qualifying
    if qualifying:
        result["decision"] = "HIGH_MARKUP_DISCOVERY"
    else:
        result["blockers"].append(
            "NO_VERIFIED_IDENTICAL_ONE_UNIT_SELLER_AT_4X_WITH_5_REVIEWS"
        )
    return result


def filter_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_supply_price: float = DEFAULT_MAX_SUPPLY_PRICE,
    min_markup_multiple: float = DEFAULT_MIN_MARKUP_MULTIPLE,
    min_review_count: int = DEFAULT_MIN_REVIEW_COUNT,
) -> dict[str, Any]:
    results = [
        evaluate_candidate(
            candidate,
            max_supply_price=max_supply_price,
            min_markup_multiple=min_markup_multiple,
            min_review_count=min_review_count,
        )
        for candidate in candidates
    ]
    matches = [row for row in results if row["decision"] == "HIGH_MARKUP_DISCOVERY"]
    return {
        "schema_version": "1.0",
        "status": "DISCOVERY_MATCHES_FOUND" if matches else "NO_DISCOVERY_MATCHES",
        "thresholds": {
            "max_unit_supply_price": max_supply_price,
            "required_sale_bundle_quantity": 1,
            "min_current_sale_price_multiple": min_markup_multiple,
            "min_review_count": min_review_count,
            "required_similarity": "identical",
            "identity_verification_required": True,
        },
        "input_count": len(candidates),
        "match_count": len(matches),
        "matches": matches,
        "results": results,
        "notice": (
            "리뷰 수는 구매 발생의 보수적 대리 신호이며 HIGH_MARKUP_DISCOVERY는 "
            "SHORTLIST 또는 수익성 승인 상태가 아니다."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-supply-price", type=float, default=DEFAULT_MAX_SUPPLY_PRICE)
    parser.add_argument("--min-markup-multiple", type=float, default=DEFAULT_MIN_MARKUP_MULTIPLE)
    parser.add_argument("--min-reviews", type=int, default=DEFAULT_MIN_REVIEW_COUNT)
    args = parser.parse_args()
    if args.max_supply_price <= 0 or args.min_markup_multiple <= 0 or args.min_reviews < 0:
        raise SystemExit("임곗값은 양수이고 최소 리뷰 수는 0 이상이어야 합니다.")

    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    candidates = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(candidates, list) or not all(isinstance(row, dict) for row in candidates):
        raise SystemExit("입력 오류: candidates 객체 배열이 필요합니다.")

    result = filter_candidates(
        candidates,
        max_supply_price=args.max_supply_price,
        min_markup_multiple=args.min_markup_multiple,
        min_review_count=args.min_reviews,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"input": len(candidates), "matches": result["match_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
