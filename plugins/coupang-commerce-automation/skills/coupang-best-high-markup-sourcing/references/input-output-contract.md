# 입출력 계약

## 정의

- `unit_supply_price`: 도매꾹 상세 원문에서 확인한 상품 1개의 공급 단가
- `sale_price`: 쿠팡 카드에서 의미가 확인된 할인 후 현재 실판매가
- `markup_multiple`: `sale_price ÷ unit_supply_price`
- `review_count`: 동일 쿠팡 판매상품에 표시된 누적 리뷰 수
- `HIGH_MARKUP_DISCOVERY`: 사용자 탐색 조건 일치. 수익성 승인·`SHORTLIST`와 다름

경계값 5,000원, 4.0배, 리뷰 5개는 포함한다.

## 샘플링 입력

기존 `coupang-product-sourcing/scripts/sample_top150.py` 입력을 사용한다.

```json
{
  "source_url": "https://domeggook.com/main/item/itemPopular.php",
  "items": [
    {
      "rank": 12,
      "name": "생활용품 후보",
      "url": "https://domeggook.com/12345678",
      "supply_price": 4500,
      "moq": 2,
      "category": "생활",
      "origin_scope": "domestic",
      "pool_type": "category_top150"
    }
  ]
}
```

목록의 `supply_price`와 `moq`는 표본화 신호일 뿐 최종 필터 값이 아니다. 선택된 상품의 상세 원문에서 다시 확인한다.

## 필터 입력

```json
{
  "candidates": [
    {
      "candidate_id": "BEST-001",
      "name": "생활용품 후보",
      "wholesale_url": "https://domeggook.com/12345678",
      "sale_bundle_quantity": 1,
      "procurement_quantity": 2,
      "supplier_terms": {
        "verified": true,
        "unit_supply_price": 4500,
        "minimum_order_qty": 2,
        "order_increment": 1,
        "wholesale_shipping_total": 3000,
        "observed_at": "2026-07-17T16:00:00+09:00",
        "source_url": "https://domeggook.com/12345678"
      },
      "coupang_products": [
        {
          "name": "생활용품 후보, 1개",
          "url": "https://www.coupang.com/vp/products/100",
          "seller": "판매자명",
          "quantity": 1,
          "sale_price": 18900,
          "list_price": 29900,
          "price_verified": true,
          "review_count": 7,
          "similarity": "identical",
          "identity_verified": true,
          "observed_at": "2026-07-17T16:05:00+09:00"
        }
      ]
    }
  ]
}
```

`supplier_terms`에는 단가·MOQ·구매 증분·주문 배송비·조사시각·원문 URL이 모두 있어야 한다. `procurement_quantity`는 MOQ 이상이며 구매 증분에 맞아야 한다.

쿠팡 행은 1개 구성, 현재가 의미 확인, 리뷰 수, URL, 조사시각이 필요하다. 공급처와 쿠팡의 이미지·구조·규격·모델·고유 문구를 확인한 경우에만 `identity_verified: true`를 쓴다.

## 출력

```json
{
  "status": "DISCOVERY_MATCHES_FOUND",
  "thresholds": {
    "max_unit_supply_price": 5000,
    "required_sale_bundle_quantity": 1,
    "min_current_sale_price_multiple": 4,
    "min_review_count": 5
  },
  "match_count": 1,
  "matches": [
    {
      "decision": "HIGH_MARKUP_DISCOVERY",
      "unit_supply_price": 4500,
      "qualifying_sellers": [
        {
          "sale_price": 18900,
          "review_count": 7,
          "markup_multiple": 4.2
        }
      ],
      "next_gate": "FULL_SOURCING_REVIEW_REQUIRED"
    }
  ]
}
```

공급조건이 불완전하면 `PRICE_REVIEW_BLOCKED`, 임곗값을 충족하지 않으면 `FILTERED_OUT`으로 둔다. 필터 결과가 없어도 실행 자체는 정상이며 `NO_DISCOVERY_MATCHES`를 출력한다.
