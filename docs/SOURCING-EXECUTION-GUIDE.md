# 소싱 자동화 실행 가이드

> 문서 탐색: [현재 상태](../STATUS.md) · [소싱 프로세스](SOURCING-PROCESS.md) · [HDB-1 제품기획 기록](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/product-plan-draft.md) · [보고서 규칙](REPORTS.md)

이 가이드는 플러그인의 첫 번째 단계인 소싱을 현재 구현 상태에서 재실행하는 방법이다. 프로젝트 루트에서 PowerShell을 사용한다.

## 1. 환경과 기준선 확인

```powershell
browser-harness --version
python coupang-product-sourcing\scripts\run_headless_browser_harness.py --help
python -c "import nodriver; print('nodriver ready')"
python -m pytest coupang-product-sourcing\tests -q
python C:\Users\csm81\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py `
  plugins\coupang-commerce-automation
```

현재 기준선은 소싱 테스트 `54 passed`와 플러그인 검증 통과다. CAPTCHA 또는 로그인이 나오면 자동 입력하거나 우회하지 말고 실행을 중단하고 재개 지점을 기록한다.

## 2. 도매꾹 Best 후보 수집 — 로컬 headless Browser Harness

1. `run_headless_browser_harness.py`로 사용자 Chrome과 분리된 임시 로컬 headless Chrome을 시작하고 Browser Harness로 `https://domeggook.com/main/item/itemPopular.php`를 연다.
2. 카테고리는 선택 입력으로 받는다. 비워 두면 `전체`, `패션잡화/화장품`, `의류/언더웨어`, `출산/유아동/완구`, `가구/생활/취미`, `스포츠/건강/식품`, `가전/휴대폰/산업`의 TOP 150에서 상·중·하 순위, 국내·국외·미확인 원산지를 분산 표본화한다.
3. 상품명, 도매꾹 URL, 단가, MOQ, 구매단위, 주문 배송비, 판매 묶음 수량, 실제 매입 수량, 조사시각, 카테고리와 검색 키워드를 JSON으로 저장한다.
4. 상품마다 새 브라우저를 만들지 않고 한 조사 회차에서 같은 정상 세션을 유지해 직렬 확인한다.
5. 실행 중 연 탭의 target ID를 기록하고, 회차 수집을 끝내면 실행기가 자신이 시작한 headless Chrome과 임시 프로필만 정리한다. 사용자가 원래 열어 둔 탭이나 다른 세션은 건드리지 않는다.
6. 중단·타임아웃·예외가 발생해도 `finally`에서 같은 정리를 수행하고 종료 결과를 실행 기록에 남긴다.

최소 연결 확인은 다음처럼 수행한다. 실제 수집 스크립트도 같은 실행기에 표준입력으로 전달한다.

```powershell
@'
recording_dir = start_recording("domeggook-headless-smoke", title="도매꾹 headless 연결 확인")
try:
    new_tab("https://domeggook.com/main/item/itemPopular.php")
    wait_for_load()
    print(page_info())
finally:
    stop_recording()
'@ | python coupang-product-sourcing\scripts\run_headless_browser_harness.py
```

headless 연결이나 접근이 실패하면 표시형 브라우저로 자동 전환하지 않는다. 차단 상태와 재개 지점을 기록하고 종료한다. 유료 원격 Browser Use는 사용자가 비용 발생을 명시적으로 승인한 경우에만 별도 실행한다.

회차 입력의 최소 형태는 다음과 같다.

```json
{
  "candidates": [
    {
      "candidate_id": "7215172",
      "name": "여행용 접이식 백팩",
      "search_keyword": "여행용 접이식 백팩",
      "url": "https://domeggook.com/7215172",
      "supply_price": 2600,
      "moq": 2,
      "sale_bundle_quantity": 1,
      "procurement_quantity": 2,
      "supplier_terms": {
        "verified": true,
        "unit_supply_price": 2600,
        "minimum_order_qty": 2,
        "order_increment": 1,
        "wholesale_shipping_total": 3000,
        "observed_at": "2026-07-16T10:00:00+09:00",
        "source_url": "https://domeggook.com/7215172"
      },
      "category": "패션"
    }
  ]
}
```

공급조건을 가격 계산 전에 검사한다.

```powershell
python coupang-product-sourcing\scripts\evidence_contract.py `
  --input tmp\domeggook-round-01.json `
  --output tmp\supplier-evidence-round-01.json
```

단가·MOQ·구매단위·배송비·판매/매입 수량·원문 URL·조사시각이 충돌하거나 빠지면 종료 코드 2로 중단한다.

기존 표본 JSON을 다시 층화할 때는 다음 명령을 쓴다.

```powershell
python coupang-product-sourcing\scripts\sample_top150.py `
  --input tmp\domeggook-pool.json `
  --output tmp\domeggook-round-01.json `
  --target 12
```

## 3. 쿠팡 근거 수집 — nodriver

쿠팡 수집은 Browser Use가 아니라 임시 프로필의 로컬 headless Chrome을 여는 `nodriver`를 사용한다. 수집기는 쿠팡 홈에 먼저 들어가 세션을 준비하고, 후보별 판매량순 검색을 직렬로 실행한 뒤 자신이 시작한 브라우저를 종료한다.

```powershell
python coupang-product-sourcing\scripts\collect_coupang_nodriver.py `
  --input tmp\domeggook-round-01.json `
  --output tmp\nodriver-round-01.json `
  --top-n 10 `
  --delay 4
```

운영 규칙은 다음과 같다.

- `headless=True`인 새 임시 Chrome 세션을 사용한다.
- 쿠팡 홈을 먼저 방문한 뒤 검색한다.
- 후보마다 브라우저·프로필을 다시 만들지 않고 한 회차의 임시 Chrome에서 여러 검색을 직렬 처리한다.
- 상품 카드가 0개이면 기다렸다가 한 번만 다시 시도한다.
- 재시도 후에도 0개이면 `coupang_blocked=true`로 남기고 다음 실행에서 재개한다.
- 정상 완료·빈 결과·접근 차단·예외 여부와 관계없이 `finally`에서 `browser.stop()`을 호출하고 소유 프로세스 종료를 기다린다. Windows 파일 잠금이 풀릴 때까지 임시 프로필 정리를 제한 횟수 재시도한다.
- 사용자가 이미 열어 둔 Chrome 또는 다른 실행의 Chrome 프로세스는 종료하지 않는다.
- headless 시작 또는 수집이 실패해도 화면이 보이는 Chrome으로 자동 전환하지 않는다.
- 종료 후 현재 실행의 임시 Chrome이 남지 않았는지 확인하고 정리 결과를 실행 기록에 남긴다.
- 가격 카드에서는 정상가·취소선 가격과 할인 후 현재 실판매가를 분리한다. 현재 가격의 의미를 특정할 수 없는 카드는 가격 표본에서 제외한다.
- 가격 분포를 만들기 전에 공급처·쿠팡 썸네일과 구조·규격·모델·고유 문구를 대조한다. 완전 동일 상품과 같은 묶음만 직접 가격 제약으로 쓰고, 다른 상품은 맥락 표본으로 분리해 단독 탈락 근거로 쓰지 않는다.
- 동일상품 현재가 중 최근 구매 수 1건 이상 또는 리뷰 5개 이상인 행만 마진 판정 중앙값에 넣는다. 리뷰는 구매 발생 대리 신호일 뿐 현재 가격의 판매량 확정값이 아니다. 판매 근거 없는 등록가는 제외하고, 판매 근거 가격 5건 미만이면 `PRICE_REVIEW_BLOCKED`로 둔다.

이 방식은 Akamai나 CAPTCHA를 무력화하는 절차가 아니다. `Access Denied`, CAPTCHA, 로그인 요구가 지속되면 안전하게 중단한다.

### 브라우저 정리 기록

Browser Harness와 `nodriver` 실행 기록에는 최소한 다음 정리 정보를 남긴다.

```yaml
browser_tool: browser-harness-headless | nodriver-headless
opened_target_count:
closed_target_count:
owned_session_or_process:
browser_cleanup_status: PASS | FAIL
cleanup_completed_at:
cleanup_error:
```

`browser_cleanup_status=FAIL`이면 수집 데이터가 있더라도 브라우저 정리 실패를 함께 보고하며 실행을 정상 완료로 표시하지 않는다.

### 3.1 도매꾹 Best 고배수 탐색 프로필

전용 `coupang-best-high-markup-sourcing`을 사용할 때는 공급처 상세 원문의 개당 단가가 사용자가 입력한 상한 이하이고 판매 묶음이 1개인 후보만 쿠팡 심화 조사한다. 쿠팡 수집 후 공급처와 쿠팡의 이미지·구조·규격·모델·고유 문구를 대조해 완전 동일한 1개 구성에만 `similarity=identical`, `identity_verified=true`를 기록한다.

```powershell
python coupang-best-high-markup-sourcing\scripts\filter_high_markup_candidates.py `
  --input tmp\best-high-markup\enriched-candidates.json `
  --output tmp\best-high-markup\high-markup-discoveries.json `
  --html-output <report-dir>\high-markup-report.html `
  --max-supply-price <사용자 개당 공급가 상한> `
  --min-markup-multiple <사용자 최소 가격 배수> `
  --min-reviews 1 `
  --min-satisfaction 100
```

필터는 정상가·취소선 가격이 아니라 의미가 확인된 할인 후 현재 실판매가만 사용한다. 같은 판매상품의 리뷰 1개 이상 또는 만족 인원 100명 이상 라벨은 구매 발생 대리 신호이며 판매량 확정값이 아니다. JSON과 HTML 보고서에는 도매꾹↔쿠팡 실제 pair URL, 개당 원가, 현재가, 가격 배수와 판매 근거를 기록한다. 실패·차단 시에도 `failure_reason`과 이번 실행의 `sampled_items`를 기록해 실제 표본 상품명·도매꾹 URL·카테고리·순위·원문 확인 단가를 UI에서 확인할 수 있게 한다. 설정 배수 이상인 pair가 하나라도 있으면 탐색 일치이며 더 싼 등록은 탈락 근거로 사용하지 않는다. 출력의 `HIGH_MARKUP_DISCOVERY`는 일반 소싱의 전체 마진·수요·경쟁·운영 검증으로 넘길 조사 우선순위이고 자동 `SHORTLIST`가 아니다.

## 4. 로켓그로스 가격과 마진 계산

도매 원가는 검증된 공급처 조건으로 판매 묶음 단위에 맞춰 계산한다. 도매 배송비 명령행 기본값은 사용하지 않는다. 현재 탐색 시나리오는 로켓그로스 비용 3,000원/판매 묶음, 판매 수수료 10.8%이며 지옥캠프 마진계산기의 단순화 VAT 방식을 적용한다.

```powershell
python coupang-product-sourcing\scripts\price_nodriver_candidates.py `
  --input tmp\nodriver-round-01.json `
  --output tmp\priced-round-01.json `
  --rocket-growth-cost 3000 `
  --fee-rate 10.8
```

표준 통과 기준은 공급조건 검증 완료, 할인 후 현재 실판매가가 확인된 동일 묶음 중 최근 구매 1건 이상 또는 같은 판매상품 리뷰 5개 이상인 가격 표본 5개 이상, 정상가 마진 40% 이상, 판매가 10% 하락 후 마진 30% 이상이다. 현재가는 확인됐지만 판매 근거가 없는 행은 가격 분포에서 제외하고 수량을 기록한다. 판매량순 상위 10개의 일반 로켓이 3개 이하면 허용하고 4개 이상이면 경쟁 과다로 제외한다. 판매자로켓은 진입 가능하다.

표준 기준에 미달해도 정상 35% 이상, 판매가 10% 하락 후 25% 이상이면 `CONDITIONAL_TEST_PRICE_REVIEW`로 상시 분류한다. 이 후보는 사용자 선택 보고서에 조건부로 포함하되 표준 통과 수와 자동 `SHORTLIST`·핸드오프에 넣지 않는다. 완전 동일품이 없으면 유사품 가격은 직접 제약이 아니지만 가격 수용성도 입증되지 않은 것이므로 실물·권리·주장 근거와 사용자 가격 승인을 다음 게이트로 둔다.

## 5. 누적 통과 5개까지 반복

한 회차가 5개를 만들지 못하면 다음 카테고리·순위 구간·원산지 표본으로 2~4단계를 반복한다. 회차별 가격 결과를 합친다.

```powershell
python coupang-product-sourcing\scripts\merge_candidate_rounds.py `
  --inputs tmp\priced-round-01.json tmp\priced-round-02.json tmp\priced-round-03.json `
  --output reports\2026\2026-07-16\sourcing-qualified-5\qualified-input.json
```

상태·카테고리 커서·조사 ID를 지속 저장하는 반복 실행기는 다음처럼 시작한다. 회차 파일이 아직 없으면 `WAITING_FOR_ROUND_INPUT`에서 멈추고 다음 카테고리를 알려 준다.

```powershell
python coupang-product-sourcing\scripts\iterate_qualified_pool.py `
  --run-dir tmp\sourcing-run-state `
  --goal 5 `
  --max-rounds 30
```

카테고리를 비워 두면 `전체`와 실제 6개 대분류를 자동 순환한다. 특정 범위만 조사하려면 `--categories "스포츠/건강/식품"`처럼 지정한다.

## 6. 사용자 선택용 HTML 생성

먼저 실행일 기준 보고서 디렉터리를 만든다. 같은 날짜의 이전 현재 실행은 이 명령에서 `deprecated`로 자동 보관된다.

```powershell
$reportDir = python scripts\tdd.py report-path sourcing-new-run --create
```

```powershell
python coupang-product-sourcing\scripts\build_qualified_report.py `
  --input tmp\qualified-input.json `
  --output-dir $reportDir `
  --minimum 5 `
  --round 3 `
  --max-rounds 30
```

- 5개 이상이면 종료 코드 0과 `AWAITING_USER_SELECTION`
- 5개 미만이고 다음 회차가 남으면 종료 코드 2와 `RESEARCH_EXPANSION_REQUIRED`
- 최대 회차·풀 소진·접근 차단이면 중단 상태와 재개 위치 저장
- 사용자가 상품과 가격안을 승인하기 전에는 상세페이지로 전달하지 않음

HTML에는 후보별 도매꾹 URL, 쿠팡 URL 5개 이상 또는 검색 근거, 추천가, 정상·스트레스 마진, 일반 로켓 수, 판매자로켓 수, 비교 가격과 탈락 사유가 표시된다.

## 7. 2026-07-16 실제 실행 기록

| 항목 | 값 |
|---|---|
| 반복 회차 | 3회 |
| 전체 후보 | 28개 |
| 기준 통과 | 10개 |
| 최소 목표 | 5개, 달성 |
| 현재 상태 | `AWAITING_USER_SELECTION` |
| HTML | [기준 통과 후보 보고서](../reports/deprecated/2026/2026-07-16/sourcing-qualified-5/qualified-candidates.html) |
| JSON | [기계 판독 결과](../reports/deprecated/2026/2026-07-16/sourcing-qualified-5/qualified-candidates.json) |

후속 선택에서는 아이스 쿨링 스카프가 MOQ와 현재 실판매가 차이로 `PRICE_REVIEW_BLOCKED`가 됐고, 이후 [동일상품 우선 재소싱 결과](../reports/deprecated/2026/2026-07-16/resourcing-exact-identity-relaxed/report.html)에서 조건부 후보를 다시 검토했다. 사용자가 HDB-1 스포츠 마스크·판매가 9,900원안을 선택했으며, 판단 기록은 [HDB-1 1차 제품기획 초안](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/product-plan-draft.md)을 기준으로 한다.

## 8. 사용자 선택 후

보고서의 추천가는 탐색용 가정이다. 사용자가 후보와 `entry`·`recommended`·`premium` 가격안을 선택하면 다음 항목을 먼저 재확인한다.

1. 실제 공급가, 옵션별 원가와 MOQ
2. 도매 배송비와 묶음배송 가능 수량
3. 포장 후 크기·무게에 따른 실제 로켓그로스 비용
4. 해당 쿠팡 카테고리 수수료와 부가세 처리
5. KC·식품·화장품 등 규제, 상표와 공급처 이미지 사용권
6. 샘플과 공급처 페이지의 SKU 동일성

이 검증을 통과한 한 후보만 `SHORTLIST`로 승격하고 상세페이지 자동화에 전달한다.

## 9. 문제 해결

| 증상 | 처리 |
|---|---|
| 도매꾹 URL 또는 공급가 누락 | 로컬 headless Browser Harness로 해당 상품을 다시 확인하고 후보 입력을 보완 |
| MOQ·구매단위·판매 묶음 충돌 | 공급처 원문에서 다시 확인하고 `supplier_terms`를 고침. 기본값으로 통과 금지 |
| 정상가와 할인가가 함께 수집됨 | 의미가 확인된 현재 실판매가만 사용. 구분 불가 카드는 제외 |
| 쿠팡 `Access Denied` | 새 headless `nodriver` 임시 세션에서 홈 선진입 후 직렬 재시도 1회 |
| 쿠팡 결과가 재시도 후에도 0개 | `BLOCKED` 저장, 결과를 만들지 말고 다음 실행에서 재개 |
| CAPTCHA 또는 로그인 요구 | 자동 우회 금지, 사람이 완료하거나 중단 |
| 배송비·로켓그로스 비용 미확정 | 탐색 가정임을 표시하고 사용자 선택 후 실제 비용 재계산 |
| 통과 후보 5개 미만 | 다음 카테고리·원산지·순위 구간으로 확장 |
| 동일 상품 여부 불명확 | 실제 이미지·모델·구성을 확인할 때까지 `WATCH` |
