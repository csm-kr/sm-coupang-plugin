# 출력 계약

## `evaluation.json`

각 후보에 다음을 포함한다.

- 순위, 판정, 상품명, 도매 URL
- 하드 필터 실패와 SHORTLIST 차단 사유
- 공급가, MOQ, 초기 매입액, 도매 배송비 배분액
- 보수적 판매가, 변동비, 공헌이익, 공헌이익률, 손익분기 ROAS
- 10% 가격 인하 결과
- 수요·마진·경쟁기회·운영안전 점수와 총점
- 동일상품 수, 일반상품 리뷰 중앙값, 상위 강자 수
- 수요 수준, 점유율 범위, 시나리오별 월 기대이익과 전체 범위
- 점수 근거와 출처 URL
- 차별화 소구, 리스크, 확인 필요 항목

원자료 후보도 `source_candidate`에 보존해 계산을 역추적할 수 있게 한다.

## `sampling-plan.json`

도매꾹 TOP 150 전체를 바로 상세 조사하지 않을 때 사용한다. 상위 1~30위 40%, 중위 31~75위 35%, 하위 76~150위 25%를 기본 배분하고 상품명·공급사 중복을 제한한다. 6개 대분류는 균등 배분을 목표로 하며 국내 45%, 국외 45%, 원산지 미확인 10%, 카테고리 TOP 150 80%, 도전! 베스트 20%를 기본 탐색 비중으로 둔다. 실제 풀에 없는 층의 몫은 존재하는 층으로 재배분한다. `coverage`에 실제 분포를 기록한다. `exploration_score`는 조사 우선순위일 뿐 판매 적합성 점수가 아니며 최종 SHORTLIST 점수에 더하지 않는다.

## `price-recommendations.json`

각 후보에 다음을 포함한다.

- 광고·제외 표본을 제거한 검증 현재가 수와 판매 근거 가격 수
- `price_basis=demand_backed_current_sale_price`, `demand_evidence_rule`, `review_evidence_is_proxy`
- 판매 근거가 없어 중앙값에서 제외한 등록가 수
- `min`, `p10`, `p25`, `p50`, `p75`, `max`
- 정상가 40%를 만족하는 `base_floor_price`
- 10% 하락 후 30%를 만족하는 `stress_floor_price`
- 정상가 35%를 만족하는 `conditional_base_floor_price`
- 10% 하락 후 25%를 만족하는 `conditional_stress_floor_price`
- 적용 등급의 두 값 중 큰 `final_floor_price`와 `margin_tier`
- `entry`, `recommended`, `premium` 가격과 정상·스트레스 마진
- `PRICE_REVIEW`, `CONDITIONAL_TEST_PRICE_REVIEW`, `PRICE_REVIEW_BLOCKED`, `REJECT` 상태와 차단 사유

`CONDITIONAL_TEST_PRICE_REVIEW`는 표준 40%/30%에는 미달하지만 35%/25%를 충족한 결과에 상시 사용한다. 이 행은 사용자 선택 보고서에 조건부 후보로 포함할 수 있지만 표준 통과 수나 자동 `SHORTLIST`·핸드오프에는 합치지 않고, 동일상품 가격 유무·가격 수용성·실물·권리·규제·사용자 승인 게이트를 명시한다.

최종 가격은 이 파일만으로 확정하지 않는다. 사용자의 가격 승인 기록이 있어야 상세페이지 입력으로 승격한다.

## `qualified-candidates.html`과 `qualified-candidates.json`

표준 또는 조건부 마진과 나머지 필수 기준을 통과한 상품을 모아 사용자에게 선택권을 제공한다. 표준·조건부 수는 분리해 표시하고, 조건부 후보에는 사용자 승인 전 자동 승격 금지를 명시한다. 각 행에는 도매꾹 상품 URL, 쿠팡 근거 URL, 공급가, 추천가, 판매 근거 가격 중앙값, 정상 마진, 10% 가격 하락 후 마진, 수요·경쟁·운영 근거를 포함한다. 등록가 전체 중앙값은 표시할 수 있어도 마진 판정 기준으로 사용하지 않는다.

각 후보의 `coupang_retail_competition`은 `none`, `seller_rocket_only`, `coupang_retail_present`, `unknown` 중 하나다. 판매량순 TOP10 일반 로켓 0~3개와 판매자로켓은 통과 가능하고, 일반 로켓 4개 이상은 탈락하며, 미확인은 차단한다. HTML에는 `일반 로켓 TOP10` 수를 표시한다.

쿠팡 근거는 후보마다 실제 상품 URL 5개 이상을 기본으로 한다. 5개를 확보하지 못한 경우 `coupang_search_evidence`에 `keyword`, `search_url`, `observed_product_count`를 기록하고 관찰 상품 수가 5개 이상이어야 한다. HTML에는 검색어 증거와 최대 5개의 개별 상품 링크를 함께 표시한다.

HTML 보고서는 매 라운드 후 덮어 갱신하며 합격 후보와 제외 후보를 모두 포함한다. 제외 후보 표에는 `WATCH`, `REJECT`, `BLOCKED` 판정, 모든 차단 사유, 도매 URL, 쿠팡 검색·상품 근거를 표시한다. 접근 제한 라운드는 조사 대상, 제한 메시지, 미판정 상태와 재개 조건을 실행 이력에 남긴다.

- 5개 이상: `AWAITING_USER_SELECTION`
- 5개 미만이고 조사 풀이 남음: `RESEARCH_EXPANSION_REQUIRED`
- 최대 회차·풀 소진: `INSUFFICIENT_QUALIFIED_CANDIDATES`
- 사용자 선택 전: 상세페이지 핸드오프 금지
- 사용자 선택 후: 선택된 상품만 최대 5개의 `SHORTLIST`로 승격

## `candidate-table.csv`

다음 열을 UTF-8 BOM CSV로 쓴다.

- 순위, 판정, 상품명, 도매 URL
- 공급가, MOQ, 초기 매입액
- 쿠팡 예상 판매가, 공헌이익, 공헌이익률
- 수요 점수와 수준, 예상 점유율 범위, 월 기대이익 범위
- 경쟁기회 점수, 마진 점수, 운영위험 점수(높을수록 안전)
- 동일상품 수, 리뷰 중앙값
- 핵심 차별화 소구, 리스크·확인항목, 근거 URL

## `candidate-report.md`

맨 위에 조사명, 생성시각, 통화, 후보 수, SHORTLIST 수를 쓴다. 전체 후보표 뒤에 SHORTLIST 상세 근거와 WATCH/REJECT 핵심 사유를 둔다. 링크는 검색결과가 아니라 실제 도매·쿠팡 페이지를 우선한다.

## `handoff-shortlist.json`

`SHORTLIST`만 포함하며 최대 5개다. 각 상품에 다음을 포함한다.

- `candidate_id`, 상품명, 도매 URL
- 판정 점수와 경제성 요약
- 샘플 확인 항목
- 차별화 소구 정확히 3개
- 상세페이지에서 증명할 장면 정확히 3개
- GIF 아이디어 1개
- 근거 URL

이 파일 생성은 상세페이지·GIF 제작을 실행한다는 뜻이 아니다. 이후 파이프라인이 읽을 수 있는 검토 대기 입력일 뿐이다.
