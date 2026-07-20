# 도매꾹 Best 고배수 소싱 지침

이 디렉터리는 1단계 소싱의 전용 탐색 프로필이다. 일반 소싱의 계약과 승인 게이트를 완화하지 않는다.

- 작업 전 `SKILL.md`, `references/input-output-contract.md`, `../coupang-product-sourcing/AGENTS.md`, `../docs/RULE.md`, 관련 `../docs/ISSUE.md`를 읽는다.
- 구현 변경 전 `../coupang-product-sourcing/tests/test_best_high_markup_filter.py`에 실패 테스트를 먼저 추가한다.
- 도매꾹 목록 단가가 아니라 상세 원문의 개당 단가만 5,000원 필터에 사용한다.
- 쿠팡의 할인 후 현재 실판매가, 1개 구성, 완전 동일성이 검증된 행만 사용자 지정 최소 가격 배수 조건에 사용한다.
- 리뷰 1개 이상 또는 만족 인원 100명 이상 라벨은 구매 발생 대리 신호이며 최근 수요·판매량 확정값으로 표현하지 않는다.
- 기준 배수 이상의 판매 근거 pair가 하나라도 있으면 탐색 일치이며 더 낮은 가격의 다른 등록으로 탈락시키지 않는다.
- `HIGH_MARKUP_DISCOVERY`를 `SHORTLIST`로 자동 승격하지 않는다.
- 완료 전 `python ../scripts/tdd.py verify sourcing`을 실행한다.
