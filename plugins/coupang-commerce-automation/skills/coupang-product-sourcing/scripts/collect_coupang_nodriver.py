#!/usr/bin/env python3
"""Collect small, serial Coupang evidence batches with a visible Chrome session.

This collector only gathers public search evidence. It never fabricates margins or
seller identity; downstream qualification remains fail-closed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from evidence_contract import normalize_market_product


SEARCH = "https://www.coupang.com/np/search?q={q}&channel=user&sorter=saleCountDesc"
CARD = '[class*="ProductUnit_productUnit"]'
REVIEW = '[class*="ProductRating_productRating"]'


def resolve_candidate_id(row: dict, keyword: str) -> str:
    """Preserve an explicit ID, otherwise derive it from either source URL."""
    explicit = str(row.get("candidate_id") or "").strip()
    if explicit:
        return explicit
    source_url = str(row.get("wholesale_url") or row.get("url") or "")
    match = re.search(r"/(\d+)(?:[/?#]|$)", source_url)
    return match.group(1) if match else keyword


def build_card_extract_script(top_n: int) -> str:
    """Build the card extraction script used by the live nodriver collector."""
    return f'''JSON.stringify(Array.from(document.querySelectorAll('{CARD}')).slice(0,{int(top_n)}).map(card => {{
        const img=card.querySelector('img'); const a=card.querySelector('a[href]');
        const r=card.querySelector('{REVIEW}'); let rocket=false, seller=false;
        const price_nodes=[];
        for (const el of card.querySelectorAll('[class*="PriceArea_priceArea"] *')) {{
            const text=(el.innerText||'').trim(); const class_name=el.getAttribute('class')||'';
            if (!/[\\d,]+\\s*원/.test(text)) continue;
            let role='';
            if (el.tagName==='DEL' || el.closest('del')) role='list_price';
            else if (!el.closest('[class*="feePrice"]') && /(^|\\s)fw-font-bold(\\s|$)/.test(class_name)) role='sale_price';
            if (role) price_nodes.push({{role,tag_name:el.tagName,class_name,text}});
        }}
        for (const el of card.querySelectorAll('[class*="ProductPrice_priceValue"],[class*="sales-price"],[class*="sale-price"],[class*="discount-price"],[class*="final-price"],[class*="origin-price"],[class*="list-price"]')) {{
            const text=(el.innerText||'').trim(); const class_name=el.getAttribute('class')||'';
            if (/[\\d,]+\\s*원/.test(text)) price_nodes.push({{role:'',tag_name:el.tagName,class_name,text}});
        }}
        for (const im of card.querySelectorAll('img')) {{ const s=im.getAttribute('src')||''; if (/logo_rocket/i.test(s)) {{ if (/merchant/i.test(s)) seller=true; else rocket=true; }} }}
        return {{name:img?(img.alt||''):'', image_url:img?(img.currentSrc||img.src||''):'', review:r?(r.innerText||''):'', price_nodes, rocket, seller_rocket:seller, url:a?a.href:''}};
    }}))'''


async def collect(rows: list[dict], top_n: int, delay: float) -> list[dict]:
    import nodriver as uc

    chrome = os.environ.get("CHROME_PATH")
    browser = await uc.start(browser_executable_path=chrome, headless=False) if chrome else await uc.start(headless=False)
    out: list[dict] = []
    try:
        await browser.get("https://www.coupang.com/")
        await asyncio.sleep(max(3.0, delay))
        for row in rows:
            keyword = str(row.get("search_keyword") or row.get("name") or "").strip()
            if not keyword:
                continue
            url = SEARCH.format(q=quote(keyword))
            page = await browser.get(url)
            await asyncio.sleep(delay)
            title = await page.evaluate("document.title")
            if title and ("Access Denied" in title or "사용권한" in title):
                out.append({**row, "coupang_search_evidence": {"keyword": keyword, "search_url": url, "observed_product_count": 0}, "coupang_blocked": True})
                continue
            extract_script = build_card_extract_script(top_n)
            raw = await page.evaluate(extract_script)
            products = json.loads(raw) if isinstance(raw, str) else []
            if not products:
                await asyncio.sleep(max(3.0, delay))
                page = await browser.get(url)
                await asyncio.sleep(max(4.0, delay))
                raw = await page.evaluate(extract_script)
                products = json.loads(raw) if isinstance(raw, str) else []
            observed_at = datetime.now().astimezone().isoformat(timespec="seconds")
            products = [
                {**normalize_market_product(product), "observed_at": observed_at}
                for product in products if isinstance(product, dict)
            ]
            urls = [p.get("url") for p in products if isinstance(p, dict) and str(p.get("url") or "").startswith("http")]
            prices = [int(p["price"]) for p in products if p.get("price_verified") is True and isinstance(p.get("price"), int)]
            enriched = dict(row)
            enriched["wholesale_url"] = str(row.get("wholesale_url") or row.get("url") or "")
            enriched["name"] = str(row.get("name") or keyword)
            enriched["candidate_id"] = resolve_candidate_id(row, keyword)
            enriched["coupang_urls"] = urls[:5]
            enriched["coupang_products"] = products
            enriched["coupang_search_evidence"] = {"keyword": keyword, "search_url": url, "observed_product_count": len(products), "observed_at": observed_at}
            enriched["coupang_blocked"] = not bool(products)
            enriched["market_price_distribution"] = {"count": len(prices), "prices": prices, "p50": sorted(prices)[len(prices)//2] if prices else None, "price_basis": "verified_current_sale_price_only"}
            enriched["coupang_retail_competition"] = "unknown"
            out.append(enriched)
    finally:
        browser.stop()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--delay", type=float, default=4.0)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    rows = payload.get("selected") or payload.get("candidates") or []
    result = {"schema_version": "1.0", "candidates": asyncio.run(collect(rows, args.top_n, args.delay))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(result["candidates"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
