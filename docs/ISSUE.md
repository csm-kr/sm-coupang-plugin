# 반복 이슈 원장

확인된 오류만 안정적인 이슈 ID로 누적한다. 같은 원인의 독립적인 실제 발생만 반복 횟수에 포함하며, 세 번째 발생부터는 같은 ID의 규칙을 `RULE.md`에 먼저 승격한 뒤 작업을 계속한다.

## SOURCING-OFFER-EVIDENCE-001

- 반복 횟수: 3
- 상태: `RULE.md` 승격 및 회귀 방지 구현
- 원인: 공급처 목록의 단가를 판매 묶음 원가로 오인하고 MOQ를 1로 저장했으며, 쿠팡 카드에서 첫 번째 `원` 금액을 정상가·할인가 구분 없이 사용했다.
- 1회 발생: 트위스트 머리끈 — 공급처 단가 55원, MOQ 100개, 판매 묶음 100개인데 MOQ 1·원가 55원으로 계산. 공급처 배송비 포함 실제 100개 묶음 원가는 8,500원.
- 2회 발생: 아이스 쿨링 스카프 — 공급처 MOQ 4개를 1개로 기록하고 쿠팡 정상가 또는 과거 표시가를 현재 할인 후 실판매가로 사용.
- 3회 발생: 여행용 접이식 백팩 — 실시간 공급처 MOQ가 2개인데 `docs/SOURCING-EXECUTION-GUIDE.md` 예시가 MOQ·실제 매입 수량을 1개로 기록해 배송비 배분과 가격 계산을 잘못 유도.
- 방지: 공급처 원문 URL·조사시각·단가·MOQ·구매단위·배송비와 판매/매입 수량을 검증하고, 쿠팡의 의미가 확인된 현재 실판매가와 동일 묶음 수량만 마진 계산에 사용한다. 하나라도 모호하면 `PRICE_REVIEW_BLOCKED`.
- 회귀 테스트: `coupang-product-sourcing/tests/test_evidence_contract.py`, `coupang-product-sourcing/tests/test_qualified_report.py`
- 승격 규칙: `docs/RULE.md#sourcing-offer-evidence-001`

## COUPANG-PRICE-DOM-COMPAT-001

- 반복 횟수: 1
- 상태: 수정 및 실전 재수집 검증 완료
- 원인: 2026-07-16 쿠팡 검색 카드가 정상가를 `<del>`, 현재가를 CSS 유틸리티 굵은 요소로 표시해 `price` 클래스명만 찾는 수집기가 가격 의미를 확보하지 못했다. `5개세트`, `5종세트`, `3장세트`처럼 붙여 쓴 구성 수도 1개로 해석했다.
- 영향: 잘못된 가격을 통과시키지는 않았지만 60개 카드가 모두 `price_verified=false`로 차단되어 #8 재검증을 진행할 수 없었다.
- 방지: `<del>`을 정상가, 가격 영역의 굵은 금액을 현재 실판매가 역할로 수집하고, 붙여 쓴 개·장·매·종 세트 수량을 회귀 테스트로 고정했다.
- 회귀 테스트: `coupang-product-sourcing/tests/test_evidence_contract.py`

## COUPANG-CANDIDATE-ID-PRECEDENCE-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: 수집기의 조건식 우선순위가 `candidate_id` 보존보다 URL 정규식 분기를 먼저 적용해 `wholesale_url`만 있는 입력의 명시적 후보 ID를 검색어로 덮어썼다.
- 1회 발생: 동일성 재소싱 입력의 `43946300-m` 등 명시적 후보 ID가 결과에서 검색 키워드로 변경됨.
- 방지: 명시적 `candidate_id`를 최우선 보존하고, 없을 때만 `wholesale_url` 또는 `url`에서 숫자 ID를 추출한다.
- 회귀 테스트: `coupang-product-sourcing/tests/test_evidence_contract.py`
