# 쿠팡 커머스 자동화 에이전트 라우터

이 저장소는 도매 상품 소싱부터 쿠팡 시장·마진 검증, 사용자 선택, 상세페이지·GIF·영상·HTML 제작과 게시 전 QA까지 연결하는 Codex 플러그인을 개발한다. 일반 소싱 외에 도매꾹 Best의 개당 5,000원 이하·쿠팡 동일 1개 상품 현재가 4배 이상·리뷰 5개 이상 탐색 프로필을 제공하며, 탐색 일치는 전체 소싱 검증 전 자동 승격하지 않는다.

이 파일은 얇은 라우터다. 상세 요구와 결정의 정본은 `docs/`이며, 작업 경로에 더 가까운 `AGENTS.md`가 이 파일을 보완한다.

사용자 응답과 새 문서는 사용자가 다른 언어를 명시하지 않는 한 한국어로 작성한다.

## 읽기 순서

1. 이 `AGENTS.md`
2. [승격 규칙](docs/RULE.md)과 관련 [반복 이슈](docs/ISSUE.md)
3. [현재 상태](STATUS.md)
4. [문서 인덱스](docs/README.md)와 [로드맵](docs/ROADMAP.md)
5. [단계 레지스트리](harness/stages.json)
6. 작업 경로의 하위 `AGENTS.md`
7. 관련 PRD·ADR·프로세스 문서와 테스트

## ISSUE → RULE 피드백 루프

- 작업 시작 전 `docs/RULE.md`와 현재 작업에 관련된 `docs/ISSUE.md` 항목을 확인한다.
- 확인된 오류는 원인이 같은 안정적인 이슈 ID에 기록한다. 같은 원인의 독립적인 실제 발생만 반복 횟수를 1 올린다.
- 반복 횟수가 3회가 되는 즉시 같은 ID의 강제 규칙을 `docs/RULE.md`에 추가한 뒤 작업을 계속한다.
- 3회 이상 이슈가 RULE에 승격되지 않았으면 진행을 중단한다.
- 문서 갱신 후와 작업 종료 전 `python scripts/tdd.py check-issues`를 실행한다.

## 경로 라우팅

| 작업 | 경로 | 추가 지침 | 주요 정본 |
|---|---|---|---|
| 소싱 | `coupang-product-sourcing/` | [소싱 AGENTS](coupang-product-sourcing/AGENTS.md) | `docs/SOURCING-PROCESS.md` |
| 고배수 소싱 | `coupang-best-high-markup-sourcing/` | [고배수 소싱 AGENTS](coupang-best-high-markup-sourcing/AGENTS.md) | 해당 스킬 `SKILL.md`·`references/` |
| 상세페이지 스킬 | `coupang-detail-page-generator/` | [상세페이지 AGENTS](coupang-detail-page-generator/AGENTS.md) | 해당 스킬 `SKILL.md`·`references/` |
| 상세페이지 실행 결과 | `detail-page/` | [작업 영역 AGENTS](detail-page/AGENTS.md) | 프로젝트 manifest·사실 원장 |
| 프로젝트 상태·핸드오프 | `commerce-project/` | [프로젝트 AGENTS](commerce-project/AGENTS.md) | 공통 `project.json`·프로젝트 폴더 계약 |
| 플러그인 패키지 | `plugins/coupang-commerce-automation/` | [플러그인 AGENTS](plugins/coupang-commerce-automation/AGENTS.md) | `docs/COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md` |
| 보고서 | `reports/` | [보고서 AGENTS](reports/AGENTS.md) | `docs/REPORTS.md` |
| 문서 | `docs/` | [문서 AGENTS](docs/AGENTS.md) | `docs/README.md` |
| TDD·훅 | `scripts/`, `.codex/`, `harness/`, `tests/` | [테스트 AGENTS](tests/AGENTS.md) | `docs/DEVELOPMENT-HARNESS.md` |

## 단계 순서와 승인 게이트

1. `sourcing`: 도매·쿠팡 근거와 마진을 검증해 통과 후보 5개 이상을 보고한다.
2. `handoff`: 사용자가 상품과 가격안을 승인한 한 후보만 공통 프로젝트 계약으로 승격한다.
3. `detail-page`: 샘플·SKU·사실·권리 확인 후 정적 상세페이지를 제작하고 QA한다.
4. `motion`: 실촬영 또는 허용된 자산으로 GIF·짧은 영상을 만들고 정적 대체안을 둔다.
5. `html`: 모바일 우선 HTML 미리보기와 채널별 패키지를 만든다.
6. `publish-qa`: 출처·링크·접근성·광고 표현·채널 규격을 검사한다.
7. `feedback`: 판매 성과를 다음 소싱과 콘텐츠 개선에 연결한다.

앞 단계가 통과하지 않았으면 다음 단계의 제작 코드를 구현하거나 산출물을 최종 승격하지 않는다. 특히 사용자 상품·가격 승인 전 상세페이지 제작, 제품 사실 확인 전 이미지 생성, 자동·육안 QA 전 게시 패키지 승격은 금지한다.

## CRITICAL 개발 규칙

- 새 기능과 버그 수정은 반드시 실패하는 테스트를 먼저 추가한 뒤 구현한다.
- 같은 Codex turn에서 해당 단계 테스트 편집이 기록되지 않으면 구현 파일 편집 훅이 차단한다.
- 한 패치에 여러 개발 단계를 섞지 않는다.
- 단계 작업 종료 전 `python scripts/tdd.py verify <stage>`가 통과해야 한다.
- 계획 단계의 테스트 디렉터리가 아직 없으면 먼저 테스트와 검증 도구부터 만든다. 빈 검증 명령으로 단계를 완료하지 않는다.
- 기존 테스트를 삭제·완화해 통과시키지 않는다. 정책 변경이면 PRD·ADR·테스트를 함께 갱신한다.
- 파괴적 명령, `.env` 셸 접근, 구현 파일 셸 직접 쓰기를 사용하지 않는다.
- 공급처 연락·발주·결제, 쿠팡 상품 등록, 광고 집행은 사용자 명시적 승인 없이 수행하지 않는다.
- CAPTCHA·로그인·접근 통제를 우회하지 않는다.

## TDD 명령

```powershell
python scripts\tdd.py list
python scripts\tdd.py route coupang-product-sourcing\scripts\recommend_prices.py
python scripts\tdd.py verify harness
python scripts\tdd.py verify sourcing
python scripts\tdd.py verify plugin
python scripts\tdd.py verify-all --implemented-only
```

Codex 훅은 `.codex/hooks.json`에 있다. 새 훅이나 변경된 훅은 Codex CLI의 `/hooks`에서 내용을 검토하고 신뢰해야 실행된다. Git 저장소가 준비된 환경에서는 `git config core.hooksPath .githooks`로 pre-commit 게이트도 활성화한다.

## 보고서 경로

모든 실행 보고서는 현재 실행과 보관 실행을 아래 구조로 분리한다.

```text
reports/YYYY/YYYY-MM-DD/<run-name>/                       # 날짜별 현재 실행 1개
reports/deprecated/YYYY/YYYY-MM-DD/<run-name>/            # 이전 실행 보관
```

`run-name`은 소문자 kebab-case를 사용한다. 새 경로는 다음 명령으로 계산한다.

```powershell
python scripts\tdd.py report-path sourcing-qualified-5 --create
```

`--create`는 같은 날짜의 기존 현재 실행을 `reports/deprecated/` 아래로 자동 이동한 뒤 새 실행 디렉터리를 만든다. 같은 활성 실행명이나 보관 경로가 이미 있으면 덮어쓰지 않고 중단한다. 보고서 생성기는 파일을 쓰기 전에 반드시 이 명령으로 경로를 준비해야 하며, 한 날짜에는 현재 실행을 1개만 남긴다. 날짜 없는 `reports/latest`, `reports/sourcing-*` 같은 루트 산출물은 만들지 않는다. 실행 중 임시 파일은 `tmp/`에 두고, 검증된 최종 보고서만 날짜 디렉터리로 승격한다.

## 현재 소싱 운영 기준

- 도매꾹 Best는 Browser Use로 표본화하고 수집이 끝나면 탭을 닫는다.
- 쿠팡은 표시형 `nodriver` Chrome으로 홈 선진입 후 판매량순 검색을 직렬 처리하고 종료한다.
- 정상가 마진 40% 이상, 판매가 10% 하락 후 30% 이상은 `STANDARD` 기준으로 사용한다.
- 판매량순 상위 10개의 일반 로켓은 3개 이하 허용하고 판매자로켓은 허용한다.
- 공급처 단가·MOQ·구매단위·배송비·판매 묶음 수량은 원문과 조사시각으로 검증한다. 기본값으로 자격을 통과시키지 않는다.
- 쿠팡 가격은 정상가가 아니라 의미가 확인된 할인 후 현재 실판매가만 사용하고, 판매 묶음 수량이 같은 표본끼리 비교한다. 시장 중앙값은 최근 구매 수 1건 이상 또는 같은 판매상품 리뷰 5개 이상인 판매 근거 가격만으로 계산하며, 근거 없는 등록가는 제외한다. 판매 근거 가격이 5건 미만이면 `PRICE_REVIEW_BLOCKED`로 두고 리뷰가 판매량 확정값이 아닌 대리 신호임을 표시한다.
- 가격 비교 전에 공급처와 쿠팡 상품의 이미지·구조·규격·모델·고유 문구를 확인해 완전 동일 여부를 먼저 잠근다. 완전 동일 상품 가격은 직접 제약으로 사용하지만 다른 상품 가격은 시장 맥락일 뿐 단독 탈락 근거로 사용하지 않는다.
- 표준 기준을 충족하지 못했더라도 정상가 35% 이상이고 판매가 10% 하락 후 25% 이상이면 `CONDITIONAL_TEST_PRICE_REVIEW`로 허용한다. 조건부 후보는 표준 통과와 구분하고 자동 `SHORTLIST`·핸드오프에 합치지 않으며, 실물·권리·가격 수용성 확인과 사용자 승인을 받기 전 진행하지 않는다.
- 로켓그로스 비용 3,000원/묶음과 수수료 10.8%는 탐색 시나리오일 뿐이며, 공급조건·실판매가가 검증되지 않으면 `PRICE_REVIEW_BLOCKED`다.

## 문서 갱신 라우팅

| 변경 | 함께 갱신할 문서 |
|---|---|
| 현재 진행 상태·실행 결과 | `STATUS.md`, `docs/ROADMAP.md` |
| 제품 범위·수용 기준 | `docs/PRD.md` |
| 장기 기술·운영 결정 | `docs/ADR.md` |
| 플러그인·스킬 구성 | `docs/COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md` |
| 소싱 판정·도구·명령 | `docs/SOURCING-PROCESS.md`, `docs/SOURCING-EXECUTION-GUIDE.md` |
| TDD·훅·라우팅 | `docs/DEVELOPMENT-HARNESS.md`, `harness/stages.json` |
| 반복 오류·강제 규칙 | `docs/ISSUE.md`, `docs/RULE.md` |
| 보고서 경로·보존 | `docs/REPORTS.md` |

## 완료 정의

작업 종료 보고에는 변경한 파일, 읽고 갱신한 정본, 실행한 검증, 남은 위험과 사용자 승인 대기를 포함한다. 코드가 존재한다는 이유만으로 완료 처리하지 말고 테스트·구조 검증·대표 산출물 중 하나 이상의 근거를 남긴다.
