# 입력 계약

## 목차

- 실행 단위
- 후보 단위
- 점수와 근거
- 상태값

## 실행 단위

UTF-8 JSON 파일 하나를 사용한다. `null`은 미확인 값이며 0과 다르다. 비용이 없다는 사실을 확인했을 때만 0을 쓴다.

```json
{
  "run": {
    "name": "2026-07 생활용품 소싱",
    "currency": "KRW",
    "wholesale_sites": ["도매꾹"],
    "category": null,
    "candidate_target": 30,
    "shortlist_limit": 5,
    "parameters": {
      "max_initial_purchase": 150000,
      "max_moq": 10,
      "max_options": 10,
      "min_contribution_profit": 3500,
      "min_contribution_margin_pct": 40,
      "stress_price_discount_pct": 10,
      "min_stress_margin_pct": 30
    }
  },
  "candidates": []
}
```

생략한 매개변수에는 위 값이 적용된다. 비용값이나 시장값에는 자동 기본값을 적용하지 않는다.

`run.category`는 선택 입력이다. `null` 또는 생략이면 도매꾹 Best의 `전체`와 실제 6개 대분류를 순환한다. 허용 선택값은 `전체`, `패션잡화/화장품`, `의류/언더웨어`, `출산/유아동/완구`, `가구/생활/취미`, `스포츠/건강/식품`, `가전/휴대폰/산업`이다. 후보 단위 `search_queries.category`는 각 상품의 쿠팡 대표 검색어이므로 실행 단위 선택 입력과 달리 조사 완결성에 필요하다.

## 후보 단위

```json
{
  "id": "C001",
  "name": "후보 상품명",
  "wholesale": {
    "site": "도매꾹",
    "url": "https://example.com/wholesale-item",
    "supplier": "공급사 표시명",
    "supply_price": 6200,
    "moq": 3,
    "wholesale_shipping_total": 3500,
    "option_count": 2,
    "photo_match_status": "confirmed",
    "image_status": "sufficient",
    "supply_update_status": "stable_updates_provided",
    "regulatory_status": "not_required_verified",
    "ip_status": "clear",
    "hard_risk_flags": [],
    "manual_hard_failures": []
  },
  "sale_bundle_quantity": 2,
  "procurement_quantity": 4,
  "supplier_terms": {
    "verified": true,
    "unit_supply_price": 1500,
    "minimum_order_qty": 4,
    "order_increment": 4,
    "wholesale_shipping_total": 2500,
    "observed_at": "2026-07-16T10:00:00+09:00",
    "source_url": "https://example.com/wholesale-item"
  },
  "search_queries": {
    "category": "대표 카테고리 검색어",
    "appeal": "핵심 소구 검색어",
    "identical": "모델명 또는 고유 표현"
  },
  "market": {
    "researched_at": "2026-07-15T16:00:00+09:00",
    "query_attempts": [
      {"query_type": "category", "status": "complete", "url": "https://www.coupang.com/..."},
      {"query_type": "appeal", "status": "complete", "url": "https://www.coupang.com/..."},
      {"query_type": "identical", "status": "no_results", "url": "https://www.coupang.com/..."}
    ],
    "results": [],
    "scores": {
      "demand_recent_purchase_reviews": 0,
      "demand_ranking_exposure": 0,
      "demand_multi_seller_sales": 0,
      "demand_seasonality_persistence": 0,
      "competition_seller_brand_dominance": 0,
      "competition_price_competition": 0,
      "competition_differentiation_room": 0,
      "operations_regulatory_ip_safety": 0,
      "operations_returns_options": 0,
      "operations_supply_images": 0
    },
    "score_evidence": {},
    "demand_scenarios": []
  },
  "pricing": {
    "conservative_sale_price": 17900,
    "price_basis_urls": ["https://www.coupang.com/..."],
    "price_basis_note": "일반상품 개당가격 중앙값과 하위 가격대를 함께 반영",
    "costs_verified": true,
    "cost_source_urls": ["https://example.com/fee-source"],
    "cost_basis_note": "수수료는 공식 표, 물류·포장비는 사용자 제공값",
    "costs": {
      "inbound_inspection": 300,
      "packaging": 500,
      "coupang_fee_rate_pct": 10.8,
      "customer_shipping": 3000,
      "other_variable": 0
    }
  },
  "content_handoff": {
    "ai_visual_priority": true,
    "sample_checks": ["실물 확인 항목"],
    "differentiators": ["소구 1", "소구 2", "소구 3"],
    "proof_scenes": ["장면 1", "장면 2", "장면 3"],
    "gif_idea": "한 문장 GIF 아이디어"
  }
}
```

`customer_shipping`에는 로켓그로스 입출고·배송비 중 위의 다른 필드에 포함되지 않은 주문당 비용을 넣는다. 선소싱 마진에는 광고비와 실제 반품 회수·재입고비를 넣지 않는다. 광고비·반품비는 판매 후 `매출 × 선소싱 마진율 - 광고비 - 반품 회수·재입고비 × 반품 수`로 별도 평가한다.

`supplier_terms`는 공급처 상품 원문에서 확인한 조건의 정본이다. `wholesale.supply_price`와 `wholesale.moq`가 각각 검증 단가·MOQ와 다르면 차단한다. 판매 묶음 원가는 `unit_supply_price × sale_bundle_quantity`, 배분 배송비는 `wholesale_shipping_total ÷ procurement_quantity × sale_bundle_quantity`로 계산한다. `order_increment`에 맞지 않는 매입 수량과 미검증 조건은 가격 계산에 사용할 수 없다.

`market.results`의 각 항목은 다음 필드를 사용한다.

- `query_type`: `category`, `appeal`, `identical`
- `query`, `sort`, `rank`, `title`, `url`
- `is_ad`: 반드시 `true` 또는 `false`
- `sale_price`, `list_price`, `price`, `price_verified`, `price_basis`, `quantity`, `unit_price`, `rating`, `review_count`
- `rocket`, `free_shipping`, `seller`, `brand`
- `recent_purchase_signal`, `recent_purchase_count`, `recent_review_signal`
- `demand_evidence_verified`: 최근 구매 수 1건 이상 또는 리뷰 5개 이상이면 `true`
- `demand_evidence_type`: `recent_purchase`, `review_proxy`, `null`
- `similarity`: `identical`, `near_identical`, `similar`, `different`, `unknown`
- `image_reuse`: `true`, `false`, `null`
- `observed_at`: 시간대가 포함된 ISO 8601

`price`는 `price_verified=true`인 할인 후 현재 실판매가와 같아야 한다. 정상가·할인 참고가는 `list_price`에만 보존한다. 한 카드에서 현재 실판매가를 의미적으로 특정할 수 없으면 `price=null`, `price_verified=false`로 두고 비교 분포에서 제외한다.

가격 중앙값에는 `price_verified=true`, 동일 판매 묶음, 동일성 잠금과 함께 `demand_evidence_verified=true`인 행만 사용한다. `recent_purchase_count>=1`은 최근 구매 근거이고 `review_count>=5`는 구매 발생 대리 신호다. 리뷰는 현재 판매자·현재 가격에서의 판매량 확정값이 아니므로 `demand_evidence_type=review_proxy`로 보존한다. 두 근거가 없는 등록가는 시장 맥락에는 남길 수 있지만 가격 분포에서는 제외한다.

## 점수와 근거

수요·경쟁·운영 점수는 브라우저에서 관찰한 사실을 바탕으로 입력한다. 각 점수 키와 같은 키를 `score_evidence`에 만들고 `note`와 `urls`를 둔다.

```json
"score_evidence": {
  "demand_recent_purchase_reviews": {
    "note": "일반상품 4개에서 최근 구매 배지와 최근 리뷰가 반복됨",
    "urls": ["https://www.coupang.com/..."]
  }
}
```

`demand_scenarios`는 확인 판매량이 아니라 명시적 가정이다. 숫자를 쓸 근거가 없으면 `market_orders`를 `null`로 둔다.

```json
{
  "label": "low",
  "market_orders": 300,
  "expected_share_pct": 0.4,
  "basis": "최근 구매 배지와 리뷰 증가를 하방 가정으로 환산한 시나리오",
  "source_urls": ["https://www.coupang.com/..."]
}
```

SHORTLIST 확정에는 `low`, `mid`, `high` 세 시나리오와 각각의 근거가 필요하다.

`price_basis_note`에는 판매 근거가 있는 가격만 선별한 방법, 중앙값·하위 가격대·구성수량, 제외한 무판매 근거 등록 수를 적는다. `cost_basis_note`에는 공식 출처와 사용자가 직접 제공한 비용을 구분한다. 비용 URL이 없는 사용자 제공값은 이 메모로 출처를 남긴다.

## 상태값

- `photo_match_status`: `confirmed`, `uncertain`, `unknown`
- `image_status`: `sufficient`, `insufficient`, `restricted`, `unknown`
- `supply_update_status`: `stable_updates_provided`, `not_provided`, `unknown`
- `regulatory_status`: `not_required_verified`, `documents_verified`, `separate_review`, `unknown`, `failed`
- `ip_status`: `clear`, `needs_review`, `unknown`, `failed`
- `query_attempts.status`: `complete`, `no_results`, `blocked`

전기용품, 어린이제품, 의료기기, 화장품, 건강기능식품, 식품 등은 첫 버전에서 `separate_review`로 둔다. 자동화가 인증 적합성을 확정하지 않는다.
