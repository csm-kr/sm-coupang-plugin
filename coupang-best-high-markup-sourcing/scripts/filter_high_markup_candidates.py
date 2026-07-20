#!/usr/bin/env python3
"""Filter verified Domeggook Best candidates by a one-unit high-markup signal.

This is a discovery gate, not a SHORTLIST or profit approval. It deliberately
fails closed when supplier terms, current sale price, bundle quantity, or exact
product identity are not verified.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_MAX_SUPPLY_PRICE = 5000.0
DEFAULT_MIN_MARKUP_MULTIPLE = 4.0
DEFAULT_MIN_REVIEW_COUNT = 1
DEFAULT_MIN_SATISFACTION_COUNT = 100
SCENARIO_ROCKET_GROWTH_COST = 3000.0
SCENARIO_FEE_RATE_PCT = 10.8
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


def parse_satisfaction_count(product: dict[str, Any]) -> int | None:
    """Read ``100명 이상 만족했어요`` style sales-evidence badges."""
    count = product.get("satisfaction_count")
    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
        return count
    if isinstance(count, float) and math.isfinite(count) and count >= 0 and count.is_integer():
        return int(count)
    signal = str(product.get("satisfaction_signal") or product.get("satisfaction") or "")
    if "만족" not in signal:
        return None
    match = REVIEW_COUNT_RE.search(signal)
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


def _verified_identical_one_unit_seller(
    product: dict[str, Any],
    unit_supply_price: float,
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
    satisfaction_count = parse_satisfaction_count(product)
    if not _http_url(product.get("url")) or not _timezone_datetime(product.get("observed_at")):
        return None

    markup_multiple = sale_price / unit_supply_price
    return {
        "name": product.get("name"),
        "url": product.get("url"),
        "seller": product.get("seller"),
        "sale_price": sale_price,
        "quantity": 1,
        "review_count": review_count if review_count is not None else 0,
        "satisfaction_count": satisfaction_count if satisfaction_count is not None else 0,
        "satisfaction_signal": str(product.get("satisfaction_signal") or ""),
        "markup_multiple": round(markup_multiple, 4),
        "similarity": "identical",
        "identity_verified": True,
        "observed_at": product.get("observed_at"),
    }


def _qualifying_seller(
    product: dict[str, Any],
    unit_supply_price: float,
    min_markup_multiple: float,
    min_review_count: int,
    min_satisfaction_count: int,
) -> dict[str, Any] | None:
    seller = _verified_identical_one_unit_seller(product, unit_supply_price)
    if seller is None:
        return None
    if seller["review_count"] >= min_review_count:
        seller["sales_evidence"] = {
            "type": "review",
            "count": seller["review_count"],
            "label": f'리뷰 {seller["review_count"]}개',
        }
    elif seller["satisfaction_count"] >= min_satisfaction_count:
        seller["sales_evidence"] = {
            "type": "satisfaction_badge",
            "count": seller["satisfaction_count"],
            "label": seller["satisfaction_signal"] or f'{seller["satisfaction_count"]}명 이상 만족했어요',
        }
    else:
        return None
    if seller["markup_multiple"] + 1e-12 < min_markup_multiple:
        return None
    return seller


def _qualifying_pair(candidate: dict[str, Any], seller: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id") or candidate.get("id"),
        "wholesale_name": candidate.get("name"),
        "wholesale_url": candidate.get("wholesale_url") or candidate.get("url"),
        "unit_supply_price": float(candidate["supplier_terms"]["unit_supply_price"]),
        "coupang_name": seller.get("name"),
        "coupang_url": seller.get("url"),
        "current_sale_price": seller.get("sale_price"),
        "markup_multiple": seller.get("markup_multiple"),
        "sales_evidence": seller.get("sales_evidence"),
        "observed_at": seller.get("observed_at"),
    }


def _scenario_profit(candidate: dict[str, Any], seller: dict[str, Any]) -> dict[str, Any]:
    terms = candidate["supplier_terms"]
    sale_price = float(seller["sale_price"])
    unit_supply_price = float(terms["unit_supply_price"])
    shipping_per_unit = float(terms["wholesale_shipping_total"]) / int(candidate["procurement_quantity"])
    fixed_cost = unit_supply_price + shipping_per_unit + SCENARIO_ROCKET_GROWTH_COST
    fee = sale_price * SCENARIO_FEE_RATE_PCT / 100
    vat = sale_price * 0.10 - (fixed_cost + fee) * 0.10
    profit = sale_price - fixed_cost - fee - vat
    return {
        "sale_price": sale_price,
        "url": seller["url"],
        "profit": round(profit, 2),
        "margin_pct": round(profit / sale_price * 100, 4),
    }


def evaluate_candidate(
    candidate: dict[str, Any],
    *,
    max_supply_price: float = DEFAULT_MAX_SUPPLY_PRICE,
    min_markup_multiple: float = DEFAULT_MIN_MARKUP_MULTIPLE,
    min_review_count: int = DEFAULT_MIN_REVIEW_COUNT,
    min_satisfaction_count: int = DEFAULT_MIN_SATISFACTION_COUNT,
) -> dict[str, Any]:
    """Apply the user's discovery thresholds to one fully enriched candidate."""
    result = {
        "candidate_id": candidate.get("candidate_id") or candidate.get("id"),
        "name": candidate.get("name"),
        "wholesale_url": candidate.get("wholesale_url") or candidate.get("url"),
        "decision": "FILTERED_OUT",
        "unit_supply_price": None,
        "qualifying_sellers": [],
        "qualifying_pairs": [],
        "discovery_rule": "EXISTS_SALES_EVIDENCED_PAIR_AT_OR_ABOVE_MULTIPLE",
        "lower_price_listings_do_not_disqualify": True,
        "market_price_range": None,
        "high_price_reference": None,
        "profitability_range": None,
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

    verified_sellers = [
        seller
        for product in products
        if isinstance(product, dict)
        for seller in [
            _verified_identical_one_unit_seller(product, unit_supply_price)
        ]
        if seller is not None
    ]
    sales_evidenced_sellers = []
    qualifying = []
    for product in products:
        if not isinstance(product, dict):
            continue
        seller = _qualifying_seller(
            product,
            unit_supply_price,
            0,
            min_review_count,
            min_satisfaction_count,
        )
        if seller is not None:
            sales_evidenced_sellers.append(seller)
            if seller["markup_multiple"] + 1e-12 >= min_markup_multiple:
                qualifying.append(seller)
    qualifying.sort(key=lambda row: (-row["markup_multiple"], -row["review_count"]))
    result["qualifying_sellers"] = qualifying
    result["qualifying_pairs"] = [_qualifying_pair(candidate, seller) for seller in qualifying]
    if sales_evidenced_sellers:
        low = min(sales_evidenced_sellers, key=lambda row: row["sale_price"])
        high = max(sales_evidenced_sellers, key=lambda row: row["sale_price"])
        result["market_price_range"] = {
            "basis": "demand_backed_verified_current_sale_price",
            "count": len(sales_evidenced_sellers),
            "min": low["sale_price"],
            "max": high["sale_price"],
            "excluded_no_demand_evidence_count": len(verified_sellers) - len(sales_evidenced_sellers),
            "review_evidence_is_proxy": True,
        }
        result["high_price_reference"] = {
            **high,
            "basis": "highest_demand_backed_verified_current_sale_price",
        }
        result["profitability_range"] = {
            "basis": "demand_backed_verified_current_sale_price_range",
            "low": _scenario_profit(candidate, low),
            "high": _scenario_profit(candidate, high),
            "scenario_assumptions": {
                "rocket_growth_cost_per_unit": SCENARIO_ROCKET_GROWTH_COST,
                "fee_rate_pct": SCENARIO_FEE_RATE_PCT,
                "vat_mode": "excel_rocket_growth_simplified",
            },
        }
    if qualifying:
        result["decision"] = "HIGH_MARKUP_DISCOVERY"
    else:
        result["blockers"].append(
            f"NO_VERIFIED_IDENTICAL_ONE_UNIT_SALES_EVIDENCED_PAIR_AT_{min_markup_multiple:g}X"
        )
    return result


def filter_candidates(
    candidates: list[dict[str, Any]],
    *,
    max_supply_price: float = DEFAULT_MAX_SUPPLY_PRICE,
    min_markup_multiple: float = DEFAULT_MIN_MARKUP_MULTIPLE,
    min_review_count: int = DEFAULT_MIN_REVIEW_COUNT,
    min_satisfaction_count: int = DEFAULT_MIN_SATISFACTION_COUNT,
) -> dict[str, Any]:
    results = [
        evaluate_candidate(
            candidate,
            max_supply_price=max_supply_price,
            min_markup_multiple=min_markup_multiple,
            min_review_count=min_review_count,
            min_satisfaction_count=min_satisfaction_count,
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
            "min_satisfaction_count": min_satisfaction_count,
            "sales_evidence_rule": "review_or_satisfaction_badge",
            "required_similarity": "identical",
            "identity_verification_required": True,
        },
        "input_count": len(candidates),
        "match_count": len(matches),
        "matches": matches,
        "results": results,
        "notice": (
            "리뷰·만족 라벨은 구매 발생의 대리 신호이며 낮은 가격의 다른 등록은 "
            "기준을 충족한 pair를 탈락시키지 않는다. HIGH_MARKUP_DISCOVERY는 "
            "SHORTLIST 또는 수익성 승인 상태가 아니다."
        ),
    }


def _money(value: Any) -> str:
    return f"{value:,.0f}원" if isinstance(value, (int, float)) else "UNKNOWN"


def _percent(value: Any) -> str:
    return f"{value:.1f}%" if isinstance(value, (int, float)) else "UNKNOWN"


def render_html(payload: dict[str, Any]) -> str:
    rows: list[str] = []
    for result in payload.get("results") or []:
        pairs = result.get("qualifying_pairs") or []
        pair = pairs[0] if pairs else {}
        wholesale_url = str(result.get("wholesale_url") or "")
        wholesale_link = (
            f'<a href="{html.escape(wholesale_url, quote=True)}" target="_blank" rel="noopener">도매꾹</a>'
            if _http_url(wholesale_url)
            else "없음"
        )
        coupang_url = str(pair.get("coupang_url") or "")
        coupang_link = (
            f'<a href="{html.escape(coupang_url, quote=True)}" target="_blank" rel="noopener">'
            f'{html.escape(str(pair.get("coupang_name") or "쿠팡 판매 상품"))}</a>'
            if _http_url(coupang_url)
            else "기준 충족 pair 미확보"
        )
        sales_evidence = pair.get("sales_evidence") or {}
        evidence_text = str(sales_evidence.get("label") or "판매 근거 미확보")
        multiple = pair.get("markup_multiple")
        multiple_text = f"{multiple:.2f}배" if isinstance(multiple, (int, float)) else "UNKNOWN"
        blockers = " · ".join(result.get("blockers") or []) or "없음"
        rows.append(
            "<tr>"
            f'<td>{html.escape(str(result.get("name") or result.get("candidate_id") or "UNKNOWN"))}<br><small>{_money(result.get("unit_supply_price"))}</small></td>'
            f'<td>{html.escape(multiple_text)}</td>'
            f'<td>{coupang_link}<br><small>{_money(pair.get("current_sale_price"))}</small></td>'
            f'<td>{html.escape(evidence_text)}</td>'
            f'<td>{html.escape(str(result.get("decision") or "UNKNOWN"))}</td>'
            f'<td>{wholesale_link}</td><td>{html.escape(blockers)}</td></tr>'
        )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>도매꾹 Best 고배수 소싱 보고서</title><style>
body{{font-family:Arial,'Noto Sans KR',sans-serif;background:#f5f7fb;color:#172033;margin:0;padding:24px}}main{{max-width:1200px;margin:auto;background:#fff;border-radius:16px;padding:28px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:12px;border-bottom:1px solid #e5e7eb;text-align:left;vertical-align:top}}th{{background:#f8fafc}}.notice{{padding:14px;background:#fff7ed;border-radius:10px;line-height:1.6}}a{{color:#2457d6}}small{{color:#64748b}}
</style></head><body><main><h1>도매꾹 Best 고배수 소싱 보고서</h1>
<p class="notice">도매꾹 1개 상품과 쿠팡의 판매 근거가 있는 동일 1개 상품을 pair로 비교합니다. 설정한 배수 이상인 pair가 하나라도 있으면 탐색 일치이며, <strong>낮은 가격의 다른 등록은 이 pair를 탈락시키지 않습니다.</strong> 리뷰·만족 라벨은 현재 가격에서의 판매량 확정값이 아닌 구매 발생 대리 신호입니다.</p>
<p>상태: <strong>{html.escape(str(payload.get("status") or "UNKNOWN"))}</strong> · 탐색 일치 {int(payload.get("match_count") or 0)}개 / 입력 {int(payload.get("input_count") or 0)}개</p>
<div style="overflow:auto"><table><thead><tr><th>도매꾹 상품·개당 원가</th><th>가격 배수</th><th>쿠팡 판매 상품·현재가</th><th>판매 근거</th><th>판정</th><th>도매 원문</th><th>차단·탈락 사유</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--html-output", type=Path)
    parser.add_argument("--max-supply-price", type=float, default=DEFAULT_MAX_SUPPLY_PRICE)
    parser.add_argument("--min-markup-multiple", type=float, default=DEFAULT_MIN_MARKUP_MULTIPLE)
    parser.add_argument("--min-reviews", type=int, default=DEFAULT_MIN_REVIEW_COUNT)
    parser.add_argument("--min-satisfaction", type=int, default=DEFAULT_MIN_SATISFACTION_COUNT)
    args = parser.parse_args()
    if args.max_supply_price <= 0 or args.min_markup_multiple <= 0 or args.min_reviews < 0 or args.min_satisfaction < 0:
        raise SystemExit("임곗값은 양수이고 최소 리뷰·만족 수는 0 이상이어야 합니다.")

    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    candidates = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(candidates, list) or not all(isinstance(row, dict) for row in candidates):
        raise SystemExit("입력 오류: candidates 객체 배열이 필요합니다.")

    result = filter_candidates(
        candidates,
        max_supply_price=args.max_supply_price,
        min_markup_multiple=args.min_markup_multiple,
        min_review_count=args.min_reviews,
        min_satisfaction_count=args.min_satisfaction,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    html_output = args.html_output or args.output.with_suffix(".html")
    html_output.parent.mkdir(parents=True, exist_ok=True)
    html_output.write_text(render_html(result), encoding="utf-8")
    print(json.dumps({"input": len(candidates), "matches": result["match_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
