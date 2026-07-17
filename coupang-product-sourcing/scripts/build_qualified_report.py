#!/usr/bin/env python3
"""Build a user-selection report from fully qualified sourcing candidates."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def is_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def valid_output_dir(path: Path, *, repo_root: Path | None = None) -> bool:
    root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    reports_root = (root / "reports").resolve()
    target = path.resolve()
    try:
        relative = target.relative_to(reports_root)
    except ValueError:
        return True
    parts = relative.parts
    if len(parts) < 3:
        return False
    year, iso_date, run_name = parts[:3]
    return bool(
        re.fullmatch(r"\d{4}", year)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso_date)
        and iso_date.startswith(year + "-")
        and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", run_name)
    )


def margin_tier(row: dict[str, Any]) -> str | None:
    option = (row.get("price_options") or {}).get("recommended") or {}
    base = (option.get("base") or {}).get("margin_pct")
    stress = (option.get("stress") or {}).get("margin_pct")
    if not isinstance(base, (int, float)) or not isinstance(stress, (int, float)):
        return None
    if base >= 40 and stress >= 30:
        return "standard_40_plus"
    if base >= 35 and stress >= 25:
        return "conditional_35_40"
    return None


def qualified(row: dict[str, Any]) -> tuple[bool, list[str]]:
    gaps: list[str] = []
    if row.get("supplier_terms_verified") is not True:
        gaps.append("공급처 MOQ·구매단위 검증 미완료")
    if row.get("market_prices_verified") is not True:
        gaps.append("쿠팡 할인 후 실판매가 검증 미완료")
    quantity = row.get("sale_bundle_quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        gaps.append("판매 묶음 수량 검증 미완료")
    if row.get("decision") not in {"PRICE_REVIEW", "CONDITIONAL_TEST_PRICE_REVIEW", "QUALIFIED"}:
        gaps.append("가격·마진 게이트 미통과")
    if row.get("blockers"):
        gaps.append("차단 사유 존재")
    if not is_url(row.get("wholesale_url")):
        gaps.append("도매꾹 URL 누락")
    urls = [url for url in (row.get("coupang_urls") or []) if is_url(url)]
    search_evidence = row.get("coupang_search_evidence") or {}
    search_valid = (
        isinstance(search_evidence, dict)
        and bool(str(search_evidence.get("keyword") or "").strip())
        and is_url(search_evidence.get("search_url"))
        and isinstance(search_evidence.get("observed_product_count"), int)
        and search_evidence["observed_product_count"] >= 5
    )
    if len(urls) < 5 and not search_valid:
        gaps.append("쿠팡 상품 URL 5개 또는 검색 키워드 증거 누락")
    distribution = row.get("market_price_distribution") or {}
    if not isinstance(distribution.get("count"), int) or distribution["count"] < 5:
        gaps.append("비교 가격 표본 5개 미만")
    if (
        distribution.get("price_basis") != "demand_backed_current_sale_price"
        or not isinstance(distribution.get("demand_backed_price_count"), int)
        or distribution["demand_backed_price_count"] < 5
    ):
        gaps.append("판매 근거 가격 중앙값 검증 미완료")
    option = (row.get("price_options") or {}).get("recommended") or {}
    base = option.get("base") or {}
    stress = option.get("stress") or {}
    if margin_tier(row) is None:
        gaps.append("정상 마진 35% 또는 10% 하락 후 마진 25% 미달")
    if row.get("demand_verified") is not True:
        gaps.append("쿠팡 수요 검증 미완료")
    if row.get("operations_safe") is not True:
        gaps.append("운영·규제 안전 검증 미완료")
    retail = row.get("coupang_retail_competition")
    if retail == "coupang_retail_present":
        gaps.append("쿠팡 직접판매 동일·근접상품 존재")
    elif retail not in {"none", "seller_rocket_only"}:
        gaps.append("쿠팡 직접판매 여부 미확인")
    return not gaps, gaps


def money(value: Any) -> str:
    return f"{value:,.0f}원" if isinstance(value, (int, float)) else "UNKNOWN"


def percent(value: Any) -> str:
    return f"{value:.1f}%" if isinstance(value, (int, float)) else "UNKNOWN"


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--minimum", type=int, default=5)
    parser.add_argument("--round-target", type=int, choices=(3, 5), default=5)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=6)
    args = parser.parse_args()
    if not valid_output_dir(args.output_dir):
        raise SystemExit("출력 경로 오류: reports/YYYY/YYYY-MM-DD/<run-name>/ 구조를 사용하세요.")
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    rows = payload.get("candidates")
    if not isinstance(rows, list):
        raise SystemExit("입력 오류: candidates 배열이 필요합니다.")

    accepted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            excluded.append({"candidate_id": None, "gaps": ["후보 행 형식 오류"]})
            continue
        passed, gaps = qualified(row)
        if passed:
            accepted.append(row)
        else:
            excluded.append({
                "candidate_id": row.get("candidate_id"), "name": row.get("name"), "decision": row.get("decision"),
                "wholesale_url": row.get("wholesale_url"), "coupang_urls": row.get("coupang_urls") or [],
                "coupang_search_evidence": row.get("coupang_search_evidence") or {}, "gaps": gaps,
            })
    accepted.sort(key=lambda row: (-float(row.get("recommendation_score") or 0), str(row.get("candidate_id") or "")))
    for index, row in enumerate(accepted, 1):
        row["qualified_rank"] = index

    minimum = max(args.minimum, 1)
    if len(accepted) >= minimum:
        status = "AWAITING_USER_SELECTION"
    elif args.round < args.max_rounds:
        status = "RESEARCH_EXPANSION_REQUIRED"
    else:
        status = "INSUFFICIENT_QUALIFIED_CANDIDATES"
    output = {
        "schema_version": "1.0", "status": status, "minimum": minimum,
        "qualified_count": len(accepted),
        "standard_count": sum(margin_tier(row) == "standard_40_plus" for row in accepted),
        "conditional_count": sum(margin_tier(row) == "conditional_35_40" for row in accepted),
        "qualified_candidates": accepted, "excluded": excluded,
        "research_round": args.round, "round_target": args.round_target, "max_rounds": args.max_rounds,
        "selection": {"selected_candidate_ids": [], "selected_price_option": {}, "approved": False},
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "qualified-candidates.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    rows_html: list[str] = []
    cards_html: list[str] = []
    for row in accepted:
        option = row["price_options"]["recommended"]
        tier = margin_tier(row)
        tier_label = "STANDARD 40%+" if tier == "standard_40_plus" else "CONDITIONAL 35~40%"
        tier_class = "pass" if tier == "standard_40_plus" else "conditional"
        links = [f'<a href="{e(row["wholesale_url"])}" target="_blank" rel="noopener">도매꾹</a>']
        links.extend(
            f'<a href="{e(url)}" target="_blank" rel="noopener">쿠팡 {i + 1}</a>'
            for i, url in enumerate(row["coupang_urls"][:5])
        )
        search = row.get("coupang_search_evidence") or {}
        search_html = ""
        if is_url(search.get("search_url")):
            search_html = (
                f'<a href="{e(search["search_url"])}" target="_blank" rel="noopener">검색어: {e(search.get("keyword") or "")}</a> '
                f'({e(search.get("observed_product_count") or 0)}개 관찰)'
            )
        rows_html.append(
            "<tr>"
            f"<td>{row['qualified_rank']}</td><td>{e(row.get('name') or row.get('candidate_id'))}</td>"
            f"<td>{e(money(row.get('supply_price')))}</td><td>{e(money(option.get('price')))}</td>"
            f"<td>{e(percent(option['base'].get('margin_pct')))}</td>"
            f"<td>{e(percent(option['stress'].get('margin_pct')))}</td>"
            f"<td>{e(money((row.get('market_price_distribution') or {}).get('p50')))}</td>"
            f"<td>{'판매자로켓 가능' if row.get('coupang_retail_competition') == 'seller_rocket_only' else '쿠팡 직접판매 없음'}</td>"
            f"<td>{search_html or '개별 상품 URL 근거'}</td><td>{' · '.join(links)}</td></tr>"
        )
        rocket_count = row.get("regular_rocket_count_top10")
        cards_html.append(
            '<article class="candidate-card">'
            f'<div class="card-head"><span class="rank">#{row["qualified_rank"]}</span><h2>{e(row.get("name") or row.get("candidate_id"))}</h2><span class="{tier_class}">{tier_label}</span></div>'
            '<div class="metrics">'
            f'<div><small>도매가</small><strong>{e(money(row.get("supply_price")))}</strong></div>'
            f'<div><small>추천 판매가</small><strong>{e(money(option.get("price")))}</strong></div>'
            f'<div><small>정상 마진</small><strong>{e(percent(option["base"].get("margin_pct")))}</strong></div>'
            f'<div><small>10% 하락 마진</small><strong>{e(percent(option["stress"].get("margin_pct")))}</strong></div>'
            f'<div><small>일반 로켓 TOP10</small><strong>{e(rocket_count if rocket_count is not None else "UNKNOWN")}개</strong></div>'
            f'<div><small>비교 표본</small><strong>{e((row.get("market_price_distribution") or {}).get("count") or 0)}개</strong></div>'
            '</div>'
            f'<div class="evidence"><div>{search_html or "개별 상품 URL 근거"}</div><div class="links">{" · ".join(links)}</div></div>'
            '</article>'
        )
    notice = "" if status == "AWAITING_USER_SELECTION" else (
        '<p class="warning">기준 통과 상품이 부족하므로 사용자 선택 단계로 진행하지 않습니다.</p>'
    )
    excluded_html: list[str] = []
    for row in excluded:
        wholesale = row.get("wholesale_url")
        wholesale_html = f'<a href="{e(wholesale)}" target="_blank" rel="noopener">도매꾹</a>' if is_url(wholesale) else "없음"
        search = row.get("coupang_search_evidence") or {}
        evidence_links = [
            f'<a href="{e(url)}" target="_blank" rel="noopener">상품 {i + 1}</a>'
            for i, url in enumerate(row.get("coupang_urls") or []) if is_url(url)
        ][:5]
        if is_url(search.get("search_url")):
            evidence_links.insert(0, f'<a href="{e(search["search_url"])}" target="_blank" rel="noopener">검색어: {e(search.get("keyword") or "")}</a>')
        excluded_html.append(
            "<tr>"
            f"<td>{e(row.get('name') or row.get('candidate_id') or 'UNKNOWN')}</td>"
            f"<td>{e(row.get('decision') or 'BLOCKED')}</td><td>{e(' · '.join(row.get('gaps') or []))}</td>"
            f"<td>{wholesale_html}</td><td>{' · '.join(evidence_links) or '근거 미확보'}</td></tr>"
        )
    report_html = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>쿠팡 소싱 기준 통과 상품 보고서</title>
<style>
body{{font-family:Arial,'Noto Sans KR',sans-serif;background:#f5f7fb;color:#172033;margin:0;padding:32px}}
main{{max-width:1200px;margin:auto;background:white;border-radius:18px;padding:32px;box-shadow:0 10px 30px #17203318}}
h1{{margin-top:0}} .summary{{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}}
.badge{{background:#edf2ff;border-radius:999px;padding:9px 14px;font-weight:700}} .warning{{background:#fff2e8;color:#9a3412;padding:14px;border-radius:10px}}
.assumption{{background:#fffbea;border:1px solid #fde68a;color:#713f12;padding:14px 16px;border-radius:12px;line-height:1.6}}
table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{padding:12px;border-bottom:1px solid #e5e7eb;text-align:left}} th{{background:#f8fafc}} a{{color:#2457d6}}
.candidate-grid{{display:grid;gap:18px;margin:24px 0 36px}} .candidate-card{{border:1px solid #dbe4f0;border-radius:16px;padding:20px;background:linear-gradient(180deg,#fff,#f8fbff);box-shadow:0 6px 18px #1720330d}}
.card-head{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}} .card-head h2{{font-size:20px;margin:0;flex:1}} .rank{{font-weight:800;color:#2457d6}} .pass,.conditional{{border-radius:999px;padding:6px 10px;font-size:12px;font-weight:800}} .pass{{background:#dcfce7;color:#166534}} .conditional{{background:#fff3e6;color:#b45309}}
.metrics{{display:grid;grid-template-columns:repeat(6,minmax(110px,1fr));gap:10px;margin:18px 0}} .metrics div{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:12px}} .metrics small{{display:block;color:#64748b;margin-bottom:5px}} .metrics strong{{font-size:17px}} .evidence{{display:grid;gap:10px}} .links{{line-height:1.9}}
.excluded-wrap{{overflow:auto;border:1px solid #e5e7eb;border-radius:12px}} .excluded-wrap table{{min-width:900px}}
@media(max-width:800px){{body{{padding:12px}}main{{padding:18px}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}.card-head h2{{font-size:18px}}table{{min-width:900px}}}}
</style></head><body><main>
<h1>쿠팡 소싱 기준 통과 상품 보고서</h1>
<div class="summary"><span class="badge">상태: {e(status)}</span><span class="badge">기준 통과: {len(accepted)}개 / 최소 {minimum}개</span><span class="badge">표준 {sum(margin_tier(row) == 'standard_40_plus' for row in accepted)} · 조건부 {sum(margin_tier(row) == 'conditional_35_40' for row in accepted)}</span><span class="badge">조사 라운드: {args.round}/{args.max_rounds} · 목표 {args.round_target}개</span></div>
<p class="assumption"><strong>선소싱 산정 가정</strong> · 도매 배송비 3,000원/개 · 로켓그로스 비용 3,000원/개 · 판매수수료 10.8% · 부가세 포함 계산. 발주 전 실제 크기·무게·묶음배송 조건으로 다시 확정합니다.</p>
{notice}
<section class="candidate-grid">{''.join(cards_html)}</section>
<h2>보류·탈락·검증 차단 후보</h2>
<p>사용자 검토를 위해 합격하지 못한 후보도 삭제하지 않고 사유와 근거를 표시합니다.</p>
<div class="excluded-wrap"><table><thead><tr><th>상품</th><th>판정</th><th>사유</th><th>도매 URL</th><th>쿠팡 검색·상품 근거</th></tr></thead>
<tbody>{''.join(excluded_html)}</tbody></table></div>
<h2>사용자 선택</h2><p>상품과 가격안을 사용자가 승인하기 전에는 상세페이지 제작으로 넘기지 않습니다.</p>
</main></body></html>"""
    (args.output_dir / "qualified-candidates.html").write_text(report_html, encoding="utf-8")
    print(json.dumps({"status": status, "qualified": len(accepted), "minimum": minimum}, ensure_ascii=False))
    return 0 if status == "AWAITING_USER_SELECTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
