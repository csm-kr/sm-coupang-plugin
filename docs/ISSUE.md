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

- 반복 횟수: 2
- 상태: 두 번째 발생 회귀 수정 완료 · 실전 재수집은 쿠팡 접근 차단으로 재개 대기
- 원인: 2026-07-16 쿠팡 검색 카드가 정상가를 `<del>`, 현재가를 CSS 유틸리티 굵은 요소로 표시해 `price` 클래스명만 찾는 수집기가 가격 의미를 확보하지 못했다. `5개세트`, `5종세트`, `3장세트`처럼 붙여 쓴 구성 수도 1개로 해석했다.
- 영향: 잘못된 가격을 통과시키지는 않았지만 60개 카드가 모두 `price_verified=false`로 차단되어 #8 재검증을 진행할 수 없었다.
- 2회 발생: 2026-07-17 팔토시 고배수 소싱에서 현재 카드의 `15,290원`이 굵은 가격 요소에 정상 노출됐지만, 수집기 생성 JavaScript의 숫자·공백 정규식이 raw string 안에서 이중 이스케이프되어 후보 10개 × 20개 카드의 가격 노드가 모두 비었다.
- 방지: `<del>`을 정상가, 가격 영역의 굵은 금액을 현재 실판매가 역할로 수집하고, 붙여 쓴 개·장·매·종 세트 수량과 생성 JavaScript 숫자·공백 정규식의 단일 이스케이프를 회귀 테스트로 고정했다.
- 회귀 테스트: `coupang-product-sourcing/tests/test_evidence_contract.py`

## COUPANG-CANDIDATE-ID-PRECEDENCE-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: 수집기의 조건식 우선순위가 `candidate_id` 보존보다 URL 정규식 분기를 먼저 적용해 `wholesale_url`만 있는 입력의 명시적 후보 ID를 검색어로 덮어썼다.
- 1회 발생: 동일성 재소싱 입력의 `43946300-m` 등 명시적 후보 ID가 결과에서 검색 키워드로 변경됨.
- 방지: 명시적 `candidate_id`를 최우선 보존하고, 없을 때만 `wholesale_url` 또는 `url`에서 숫자 ID를 추출한다.
- 회귀 테스트: `coupang-product-sourcing/tests/test_evidence_contract.py`

## PROJECT-ID-LENGTH-VALIDATION-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: 프로젝트 ID 안내와 JSON Schema는 3~64자를 요구했지만 초기 Python·React 정규식의 반복 그룹이 선택 사항이라 한 글자 ID도 통과했다.
- 1회 발생: `commerce-project` 관리자와 React 새 프로젝트 폼의 초기 구현에서 `a`가 유효한 프로젝트 경로로 판정됨.
- 방지: Python·React·JSON Schema의 정규식을 같은 3~64자 계약으로 고정하고 알 수 없는 소싱 모드도 생성 전에 차단한다.
- 회귀 테스트: `tests/handoff/test_project_store.py`, `coupang-workflow-ui/assets/react-app/src/workflow.test.js`

## REPORT-STDIN-UTF8-001

- 반복 횟수: 1
- 상태: 실행 절차 수정 및 최종 보고서 새 실행 경로 재생성
- 원인: PowerShell here-string을 Python stdin으로 전달해 보고서를 생성하면서 고정 한글 리터럴이 `?`로 손상됐고, 육안 QA 후 같은 활성 실행 파일을 교정본으로 덮어써 보고서 보존 규칙도 위반했다.
- 1회 발생: 2026-07-17 `paltosi-001-high-markup-sourcing` HTML·JSON의 고정 한글 문구 손상 및 같은 실행 경로 교체.
- 방지: 한글 보고서 생성 코드는 UTF-8 파일로 저장해 실행하고, 생성 후 브라우저 육안 QA가 실패하면 같은 파일을 덮어쓰지 말고 `report-path --create`로 새 실행명을 준비한다.
- 검증: `python scripts/tdd.py check-reports`, 브라우저 DOM의 `???` 0건·후보 행 10건·링크 70건 확인.

## WORKFLOW-UI-PROJECT-CREATE-DISABLED-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: 새 프로젝트 폼이 영문 프로젝트 ID를 필수로 요구하면서 기본값을 비워 두고, ID가 없을 때 생성 버튼을 설명 없이 비활성화해 초보 사용자가 프로젝트 이름만 입력하면 생성 요청 자체가 전송되지 않았다.
- 1회 발생: 실제 UI 프로젝트 생성 테스트에서 서버·정적 자산·API는 정상이었지만 프로젝트 목록이 비어 있었고, 폼의 빈 ID 때문에 POST 요청 전에 중단됨.
- 방지: 폼을 열 때 충돌 가능성이 낮은 `project-YYYYMMDD-HHMMSS-mmm` ID를 자동 생성하고 사용자는 프로젝트 이름만 입력해도 생성할 수 있게 한다.
- 회귀 테스트: `tests/plugin/test_plugin_contract.py`, `coupang-workflow-ui/assets/react-app/src/workflow.test.js`

## WORKFLOW-UI-MOBILE-CASCADE-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: 쿠팡 무드 시각 개편의 데스크톱 `.project-rail` 고정 폭과 `.workspace` 왼쪽 여백 규칙을 기존 모바일 미디어 쿼리 뒤에 추가하면서, 850px 이하에서도 뒤쪽 데스크톱 선언이 모바일 초기화를 다시 덮어썼다.
- 1회 발생: 2026-07-20 360px 브라우저 QA에서 문서 폭이 594px로 늘어나고 프로젝트 열 오른쪽에 본문이 잘린 채 배치됨.
- 방지: 시각 개편 블록의 850px 미디어 쿼리에서 프로젝트 열 `position: static`·`width: auto`와 본문 `margin-left: 0`을 명시적으로 재선언한다.
- 회귀 테스트: `tests/plugin/test_plugin_contract.py::test_workflow_ui_refresh_resets_fixed_desktop_layout_on_mobile`

## WORKFLOW-UI-CODEX-PATH-PRECEDENCE-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: Windows에 npm `codex.CMD`와 Codex 데스크톱 `codex.exe`가 함께 설치된 상태에서 실행기가 파일 종류만 보고 데스크톱 실행 파일을 우선해, 활성 `PATH`가 선택한 최신 CLI보다 오래된 바이너리를 실행했다.
- 1회 발생: 자동 실행 스모크 테스트에서 활성 `codex.CMD`는 `0.144.5`였지만 우선 선택된 데스크톱 `codex.exe`는 `0.129.0-alpha.15`여서 현재 설정 모델 `gpt-5.6-sol`을 지원하지 못하고 400으로 실패했다.
- 방지: Windows 자동 실행기는 `shutil.which("codex")`로 활성 `PATH` CLI를 먼저 사용하고, 없을 때만 `codex.exe`로 폴백한다.
- 회귀 테스트: `tests/plugin/test_codex_runner.py`

## WORKFLOW-UI-CODEX-GLOBAL-CONFIG-STARTUP-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: 비대화형 UI 실행이 사용자 전역 모델·MCP 설정을 그대로 불러 자동화와 무관한 MCP 서버 초기화에서 첫 JSON 이벤트 전 장시간 대기했다.
- 1회 발생: 호환 CLI로 실행한 한 줄 스모크 테스트가 60초 동안 이벤트를 내지 않고 전역 MCP 자식 프로세스를 유지해 제한 시간 후 해당 프로세스 트리만 종료했다.
- 방지: 자동 실행은 Codex 인증을 유지하면서 `--ignore-user-config --ephemeral`로 전역 모델·MCP 설정과 세션 저장을 격리한다. 같은 한 줄 스모크 테스트는 6.1초에 JSONL 완료 이벤트를 반환했다.
- 회귀 테스트: `tests/plugin/test_codex_runner.py`

## WORKFLOW-UI-NULL-METRIC-ZERO-001

- 반복 횟수: 1
- 상태: 수정 및 회귀 방지 구현
- 원인: 후보 카드의 선택적 가격·마진 포매터가 `Number(null)`과 `Number("")`을 0으로 변환해 미검증 값을 실제 0원·0.0%처럼 표시했다.
- 1회 발생: 2026-07-19 깔창 프로젝트 상품·가격 선택 화면의 브라우저 QA에서 판매가·수익률이 `null`인 `PRICE_REVIEW_BLOCKED` 후보가 `0원`, `0.0%`로 노출됐다.
- 방지: 선택적 숫자 포매터는 `null`, `undefined`, 빈 문자열을 숫자 변환 전에 차단하고 `확인 대기`로 표시한다. 실제 숫자 0만 `0원`·`0.0%`로 표시한다.
- 회귀 테스트: `coupang-workflow-ui/assets/react-app/src/workflow.test.js`
