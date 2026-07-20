# 쿠팡 커머스 자동화 문서

이 디렉터리는 `coupang-commerce-automation` 플러그인의 제품 요구사항, 기술 결정, 구현 순서와 실행 근거를 관리한다.

## 문서 지도

| 문서 | 역할 | 변경 시점 |
|---|---|---|
| [현재 상태](../STATUS.md) | 지금까지 완료된 작업, 실제 실행 결과와 다음 행동 | 작업 완료·차단·사용자 결정 시 |
| [개발 하니스](DEVELOPMENT-HARNESS.md) | AGENTS 라우팅, 단계형 TDD와 필수 Codex·Git 훅 | 단계·검증·훅 변경 시 |
| [보고서 규칙](REPORTS.md) | 연도·날짜별 보고서 경로, 이름과 보존 정책 | 산출물 경로·보존 정책 변경 시 |
| [반복 이슈](ISSUE.md) | 실제 오류, 원인, 반복 횟수와 회귀 방지 근거 | 확인된 오류 발생·재발 시 |
| [승격 규칙](RULE.md) | 3회 이상 반복된 이슈의 강제 규칙 | 이슈 반복 횟수가 3회가 될 때 |
| [PRD](PRD.md) | 사용자 문제, 제품 목표, 요구사항과 수용 기준 | 제품 범위 또는 성공 기준 변경 시 |
| [ADR](ADR.md) | 장기 영향을 주는 아키텍처 결정과 결과 | 기술 결정 채택·대체 시 |
| [ROADMAP](ROADMAP.md) | 현재 위치, 단계별 목표와 완료 조건 | 구현 상태 또는 우선순위 변경 시 |
| [구현 계획](COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md) | 상세 파이프라인, 스킬 구성과 산출물 계약 | 구현 절차·계약 변경 시 |
| [콘텐츠 생성·조립 QA 체크리스트](CONTENT-PRODUCTION-CHECKLIST.md) | 이미지·GIF·HTML 소재 QA, 통합 QA와 실제 원본 교체 게이트 | 제작·QA·스킬 계약 변경 시 |
| [소싱 프로세스](SOURCING-PROCESS.md) | 소싱 판단 원칙과 전체 흐름 | 평가 정책 변경 시 |
| [소싱 실행 가이드](SOURCING-EXECUTION-GUIDE.md) | 로컬 실행 명령과 안전 중단 조건 | 명령·도구·경로 변경 시 |
| [소싱 파일럿 001](SOURCING-PILOT-001-TUMBLER.md) | 첫 실증 조사와 판정 기록 | 원칙적으로 고정, 정정 시 이력 기록 |

## 문서 우선순위

문서가 충돌하면 아래 순서로 판단한다.

1. `ADR.md`: 이미 채택된 기술·운영 결정
2. `PRD.md`: 제품 범위와 수용 기준
3. `ROADMAP.md`: 구현 순서와 현재 상태
4. `COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md`: 상세 구현안
5. 소싱 프로세스·실행 가이드·파일럿 기록

충돌을 발견하면 하위 문서를 임의로 해석하지 말고 상위 문서에 맞춰 갱신한다. 실제 코드가 문서와 다르면 `ROADMAP.md`에 차이를 기록하고 구현 또는 문서 중 하나를 정정한다.

## 파일명 규칙

- `docs/`의 관리 대상 Markdown 파일명은 대문자 영문과 하이픈을 사용한다.
- 예: `SOURCING-EXECUTION-GUIDE.md`
- 프로젝트 표준 문서는 `README.md`, `PRD.md`, `ADR.md`, `ROADMAP.md` 이름을 유지한다.
- 파일럿·실행 기록에는 의미 있는 식별자나 날짜를 포함한다.
- `legacy/`는 참고용 원문 보관소이며 신규 기준 문서로 사용하지 않는다.

## 상태 표기 규칙

- `Implemented`: 코드와 검증 근거가 존재한다.
- `Partial`: 일부 코드가 있으나 통합 계약 또는 수용 기준이 미완료다.
- `Planned`: 결정 또는 계획만 있고 아직 구현되지 않았다.
- `Blocked`: 필요한 자료, 사용자 결정 또는 외부 상태가 없어 진행할 수 없다.

완료 체크는 코드 존재만으로 표시하지 않는다. 테스트, 검증 명령 또는 대표 산출물 중 하나 이상의 근거가 있어야 한다.

## 현재 기준선

- 플러그인 버전: `0.2.0+codex.20260719101427`
- 첫 번째 자동화 단계: **소싱**
- 현재 상태: HDB-1 `숨트임` `concept_only` 합성 모델 2장·10모듈 스토리보드·3초 GIF·반응형 HTML의 수치형 QA 완료; 실제 제작은 사람 없는 실제 SKU 원본 대기
- 조사 도구: 도매꾹은 Browser Use, 쿠팡은 실제 Chrome을 여는 `nodriver` 수집기
- 플러그인 검증: 통과
- 프로젝트 UI: 독립 `Commerce Flow` 토큰·가로 9단계 내비게이션·현재 할 일 단일 CTA, 로컬 API·공통 프로젝트 폴더 관리자·Codex 자동 실행과 읽기 전용 내장 콘솔 구현, 360px·800px Browser Harness QA와 JSONL 런타임 스모크 통과
- 소싱 테스트: 44개 통과, 공급조건·할인 후 실판매가·판매 근거 가격 표본·쿠팡 DOM·묶음 수량, 실제 카테고리 기본 순환과 Best 고배수 현재가·수익률 범위 회귀 테스트 포함
- 하니스 테스트: 46개 통과, 공통 프로젝트 AGENTS 라우팅과 ISSUE 3회 → RULE 승격 검사 포함
- 핸드오프 프로젝트 저장소 테스트: 6개 통과
- 플러그인 계약 테스트: 31개 통과, React 단계·실행·보고서 링크·단일 행동·접근성 로직 18개 통과, 선택 카테고리·고배수 단일 모드·신규 보고서 성공 게이트·초보 사용자용 프로젝트 ID 자동 생성 포함
- 상세페이지 계약 테스트: 19개 통과, GIF·한글 타이포·시각 스토리보드·크롭 검증 포함
- 대표 산출물: [승인된 HDB-1 제품기획](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/product-plan-draft.md) · [승인된 콘텐츠기획](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/content-plan-draft.md) · [11개 자산 기반 콘텐츠기획 v2](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/asset-backed-content-plan-v2.md) · [실제 자산·근거 인입](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/asset-evidence-intake.md) · [콘셉트 HTML·GIF 품질 프로토타입](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/concept-only-prototype-report.md) · [시각 스토리보드·수치형 QA](../reports/2026/2026-07-16/hdb1-visual-storyboard-qa/report.md)
- 개발 기준: 단계별 TDD 실행기와 `PreToolUse`·`PostToolUse`·`Stop` 훅 적용
- 보고서 기준: `reports/YYYY/YYYY-MM-DD/<run-name>/`
- 다음 작업: 자산 기반 콘텐츠기획 v2 해시 승인과 실제 HDB-1 제품 단독 정·후·좌우·펼침·타공·실측·4색·라벨 확보 후 콘셉트 자산을 교체하고 소재·통합 QA 재실행; 제품명 `숨트임`은 승인, `에어베일`은 미승인
