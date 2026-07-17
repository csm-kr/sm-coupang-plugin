from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_report_module():
    path = ROOT / "scripts" / "build_qualified_report.py"
    spec = importlib.util.spec_from_file_location("build_qualified_report", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def valid_row(index: int) -> dict:
    return {
        "candidate_id": f"C{index:02d}", "name": f"기준 통과 상품 {index}",
        "decision": "PRICE_REVIEW", "blockers": [],
        "wholesale_url": f"https://domeggook.com/{1000 + index}",
        "coupang_urls": [f"https://www.coupang.com/vp/products/{2000 + index}-{n}" for n in range(5)],
        "supply_price": 3000, "recommendation_score": 80 - index,
        "market_price_distribution": {
            "count": 8,
            "p50": 15900,
            "price_basis": "demand_backed_current_sale_price",
            "demand_backed_price_count": 8,
        },
        "price_options": {"recommended": {
            "price": 15900, "base": {"margin_pct": 44.2}, "stress": {"margin_pct": 34.1}
        }},
        "demand_verified": True, "operations_safe": True,
        "supplier_terms_verified": True, "market_prices_verified": True,
        "sale_bundle_quantity": 1,
        "coupang_retail_competition": "seller_rocket_only",
    }


def test_requires_all_qualification_gates():
    mod = load_report_module()
    passed, gaps = mod.qualified(valid_row(1))
    assert passed and not gaps
    bad = valid_row(2)
    bad["demand_verified"] = False
    passed, gaps = mod.qualified(bad)
    assert not passed
    assert "쿠팡 수요 검증 미완료" in gaps
    retail = valid_row(3)
    retail["coupang_retail_competition"] = "coupang_retail_present"
    passed, gaps = mod.qualified(retail)
    assert not passed
    assert "쿠팡 직접판매 동일·근접상품 존재" in gaps
    weak = valid_row(4)
    weak["coupang_urls"] = weak["coupang_urls"][:1]
    passed, gaps = mod.qualified(weak)
    assert not passed
    assert "쿠팡 상품 URL 5개 또는 검색 키워드 증거 누락" in gaps
    weak["coupang_search_evidence"] = {
        "keyword": "테스트 판매상품", "search_url": "https://www.coupang.com/np/search?q=test",
        "observed_product_count": 8,
    }
    assert mod.qualified(weak)[0]


def test_five_valid_rows_are_available_for_user_selection():
    mod = load_report_module()
    accepted = [row for row in (valid_row(i) for i in range(1, 6)) if mod.qualified(row)[0]]
    assert len(accepted) == 5


def test_margin_between_35_and_40_is_accepted_as_conditional():
    mod = load_report_module()
    row = valid_row(1)
    row["decision"] = "CONDITIONAL_TEST_PRICE_REVIEW"
    row["price_options"]["recommended"]["base"]["margin_pct"] = 37.4
    row["price_options"]["recommended"]["stress"]["margin_pct"] = 28.2

    passed, gaps = mod.qualified(row)

    assert passed is True
    assert not gaps
    assert mod.margin_tier(row) == "conditional_35_40"


def test_unverified_supplier_terms_or_sale_prices_cannot_qualify():
    mod = load_report_module()
    supplier = valid_row(1)
    supplier["supplier_terms_verified"] = False
    passed, gaps = mod.qualified(supplier)
    assert not passed
    assert "공급처 MOQ·구매단위 검증 미완료" in gaps

    market = valid_row(2)
    market["market_prices_verified"] = False
    passed, gaps = mod.qualified(market)
    assert not passed
    assert "쿠팡 할인 후 실판매가 검증 미완료" in gaps


def test_report_rejects_market_distribution_without_demand_backed_price_basis():
    mod = load_report_module()
    row = valid_row(1)
    row["market_price_distribution"] = {"count": 8, "p50": 6900}

    passed, gaps = mod.qualified(row)

    assert passed is False
    assert "판매 근거 가격 중앙값 검증 미완료" in gaps


def test_main_writes_html_report(tmp_path, monkeypatch):
    mod = load_report_module()
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"candidates": [valid_row(i) for i in range(1, 6)]}), encoding="utf-8")
    output = tmp_path / "report"
    monkeypatch.setattr(sys, "argv", ["build_qualified_report.py", "--input", str(source), "--output-dir", str(output)])
    assert mod.main() == 0
    report = output / "qualified-candidates.html"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert '<html lang="ko">' in text
    assert "https://domeggook.com/1001" in text
    assert not (output / "qualified-candidates.md").exists()


def test_output_directory_under_reports_requires_year_date_and_run_name(tmp_path):
    mod = load_report_module()
    valid = tmp_path / "reports" / "2026" / "2026-07-16" / "sourcing-qualified-5"
    invalid = tmp_path / "reports" / "sourcing-qualified-5"
    temporary = tmp_path / "tmp" / "report"
    assert mod.valid_output_dir(valid, repo_root=tmp_path)
    assert not mod.valid_output_dir(invalid, repo_root=tmp_path)
    assert mod.valid_output_dir(temporary, repo_root=tmp_path)
