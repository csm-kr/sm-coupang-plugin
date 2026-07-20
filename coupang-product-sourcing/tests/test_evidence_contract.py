from __future__ import annotations

import asyncio
import importlib.util
import io
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


def test_coupang_collector_captures_satisfaction_badge_as_sales_evidence():
    mod = load("collect_coupang_nodriver")

    script = mod.build_card_extract_script(10)

    assert "satisfaction_signal" in script
    assert "satisfaction_count" in script
    assert "만족" in script


def test_coupang_collector_launches_headless_isolated_chrome(monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = load("collect_coupang_nodriver")
    starts = []

    class FakeBrowser:
        stopped = False

        async def get(self, _url):
            return object()

        def stop(self):
            self.stopped = True

    browser = FakeBrowser()

    async def fake_start(**kwargs):
        starts.append(kwargs)
        return browser

    async def no_sleep(_seconds):
        return None

    monkeypatch.setitem(sys.modules, "nodriver", type("FakeNodriver", (), {"start": fake_start}))
    monkeypatch.setattr(mod.asyncio, "sleep", no_sleep)

    assert asyncio.run(mod.collect([], top_n=10, delay=0)) == []
    assert starts[0]["headless"] is True
    assert "coupang-headless-" in str(starts[0]["user_data_dir"])
    assert browser.stopped is True


def test_coupang_collector_waits_and_retries_windows_profile_cleanup(monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = load("collect_coupang_nodriver")
    events = []

    class FakeProcess:
        async def wait(self):
            events.append("process-waited")
            return 0

    class FakeBrowser:
        _process = FakeProcess()

        def stop(self):
            events.append("browser-stopped")

    class LockedProfile:
        calls = 0

        def cleanup(self):
            self.calls += 1
            events.append(f"cleanup-{self.calls}")
            if self.calls == 1:
                raise PermissionError("profile still locked")

    async def no_sleep(_seconds):
        events.append("retry-wait")

    monkeypatch.setattr(mod.asyncio, "sleep", no_sleep)
    profile = LockedProfile()

    asyncio.run(mod.stop_browser_and_cleanup(FakeBrowser(), profile, cleanup_attempts=3, cleanup_delay=0))

    assert events == [
        "browser-stopped",
        "process-waited",
        "cleanup-1",
        "retry-wait",
        "cleanup-2",
    ]


def test_browser_harness_launcher_builds_focus_free_headless_chrome_contract(tmp_path):
    mod = load("run_headless_browser_harness")
    profile_dir = tmp_path / "profile"

    args = mod.build_chrome_args(port=9333, profile_dir=profile_dir)
    env = mod.build_harness_env("http://127.0.0.1:9333", {"BU_NAME": "old", "BU_CDP_WS": "ws://old"})

    assert "--headless=new" in args
    assert "--remote-debugging-port=9333" in args
    assert f"--user-data-dir={profile_dir}" in args
    assert "--start-maximized" not in args
    assert env["BU_CDP_URL"] == "http://127.0.0.1:9333"
    assert "BU_NAME" not in env
    assert "BU_CDP_WS" not in env


def test_browser_harness_launcher_preserves_utf8_stdin_as_bytes(monkeypatch):
    mod = load("run_headless_browser_harness")
    script = 'start_recording("도매꾹 조사")\n'.encode("utf-8")
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    payload = mod.read_script_bytes(io.BytesIO(script))
    result = mod.run_harness("browser-harness", payload, {"BU_CDP_URL": "http://127.0.0.1:9333"})

    assert result == 0
    assert calls[0][1]["input"] == script
    assert calls[0][1]["text"] is False
    assert calls[0][1]["env"]["PYTHONUTF8"] == "1"
    assert calls[0][1]["env"]["PYTHONIOENCODING"] == "utf-8"


def test_browser_harness_launcher_normalizes_windows_cp949_pipe_to_utf8():
    mod = load("run_headless_browser_harness")
    source = 'start_recording("도매꾹 조사")\n'

    payload = mod.read_script_bytes(io.BytesIO(source.encode("cp949")))

    assert payload == source.encode("utf-8")


def test_sourcing_runtime_guides_require_headless_without_visible_fallback():
    repo_root = next(parent for parent in ROOT.parents if (parent / "docs" / "SOURCING-PROCESS.md").exists())
    source_files = [
        repo_root / "coupang-product-sourcing" / "SKILL.md",
        repo_root / "coupang-best-high-markup-sourcing" / "SKILL.md",
        repo_root / "docs" / "SOURCING-PROCESS.md",
        repo_root / "docs" / "SOURCING-EXECUTION-GUIDE.md",
    ]
    contract = "\n".join(path.read_text(encoding="utf-8-sig") for path in source_files)

    assert "headless=False" not in contract
    assert "표시형 `nodriver`" not in contract
    assert "표시형 Chrome" not in contract
    assert "headless" in contract
    assert "표시형 브라우저로 자동 전환하지 않는다" in contract


def test_coupang_collector_money_regex_matches_digits_in_live_card_dom():
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = load("collect_coupang_nodriver")

    script = mod.build_card_extract_script(5)

    assert r"/[\d,]+\s*원/" in script
    assert r"/[\\d,]+\\s*원/" not in script
    assert r"/(^|\s)fw-font-bold(\s|$)/" in script
    assert r"/(^|\\s)fw-font-bold(\\s|$)/" not in script
    assert r"[^\d]{0,10}([\d,]+)" in script
    assert r"[^\\d]{0,10}([\\d,]+)" not in script


def test_coupang_collector_card_script_captures_recent_purchase_evidence():
    sys.path.insert(0, str(ROOT / "scripts"))
    mod = load("collect_coupang_nodriver")

    script = mod.build_card_extract_script(10)

    assert "recent_purchase_signal" in script
    assert "recent_purchase_count" in script
    assert "명 이상 구매" in script


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
                "review_count": 5,
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
    assert evidence["verified_current_price_count"] == 5
    assert evidence["demand_backed_price_count"] == 5
    assert evidence["excluded_no_demand_evidence_count"] == 0
    assert evidence["excluded_market_products"][0]["reason"] == "판매 묶음 수량 불일치"


def test_pricing_candidate_does_not_count_zero_review_listings_as_demand_backed():
    mod = load("price_nodriver_candidates")
    row = {
        "candidate_id": "60851997",
        "name": "동일상품 판매 근거 검증",
        "url": "https://domeggook.com/60851997",
        "supply_price": 1800,
        "moq": 4,
        "sale_bundle_quantity": 1,
        "procurement_quantity": 50,
        "supplier_terms": verified_supplier_terms(unit_price=1800, moq=4, shipping=3000),
        "coupang_products": [
            {
                "name": f"동일상품 옵션 {index}",
                "price": 5500 + index * 100,
                "price_verified": True,
                "quantity": 1,
                "review_count": 5 if index < 4 else 0,
                "url": f"https://www.coupang.com/vp/products/{index}",
            }
            for index in range(7)
        ],
    }

    candidate, evidence = mod.build_pricing_candidate(
        row, rocket_growth_cost=3000, fee_rate=10.8, min_market_samples=5
    )

    assert len(candidate["market_prices"]) == 7
    assert sum(price["demand_evidence_verified"] for price in candidate["market_prices"]) == 4
    assert evidence["verified_current_price_count"] == 7
    assert evidence["demand_backed_price_count"] == 4
    assert evidence["excluded_no_demand_evidence_count"] == 3
    assert evidence["market_prices_verified"] is False
