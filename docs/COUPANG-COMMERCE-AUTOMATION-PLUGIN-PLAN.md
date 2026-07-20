# 쿠팡 커머스 자동화 플러그인 구현 계획

- 문서 상태: Active
- 기준 버전: `coupang-commerce-automation` v0.2.0
- 기준일: 2026-07-16

> 문서 탐색: [현재 상태](../STATUS.md) · [README](README.md) · [PRD](PRD.md) · [ADR](ADR.md) · [ROADMAP](ROADMAP.md)

## 1. 문서 역할

이 문서는 상품 소싱부터 상세페이지, 모션, HTML, 게시 전 QA까지 이어지는 구현 구조와 산출물 계약을 정의한다. 제품 범위와 수용 기준은 [PRD](PRD.md), 채택된 기술 결정은 [ADR](ADR.md), 현재 위치와 구현 순서는 [ROADMAP](ROADMAP.md)을 기준으로 한다.

## 2. 현재 기준선

| 구성요소 | 상태 | 근거 |
|---|---|---|
| 플러그인 골격·매니페스트 | Implemented | v0.2.0 플러그인 검증 통과 |
| 오케스트레이터·단계 스킬 | Implemented | 현재 단계·AC·한 질문 UX, 상품기획·콘텐츠·게시 QA 스킬 검증 통과 |
| React 프로젝트 UI·작업공간 | Implemented | 9단계 대시보드, 인라인 후보 선택·승인·단계 이동, 실패 이유·현재 도매꾹 샘플 표시, VS Code형 파일 탐색·HTML/이미지 미리보기·이미지 드롭 업로드, Codex 자동 실행·내장 콘솔 테스트 통과 |
| `coupang-product-sourcing` | Implemented | 단위 테스트 37개 통과, 3회차·28개 조사·10개 통과 HTML 생성 |
| `coupang-best-high-markup-sourcing` | Implemented | Best 층화 표본·사용자 공급가 상한·최소 가격 배수·리뷰/만족 라벨 기반 쿠팡 동일 1개 pair 존재성 게이트와 회귀 테스트 |
| `coupang-detail-page-generator` | Partial | 5.3 분리 승인, 시각 스토리보드, 하이브리드 HTML·2층 좌표 QA와 `concept_only` 대표 프로토타입 구현, 실제 SKU 회귀 필요 |
| 소싱→상세페이지 자동 승격 | Partial | 프로젝트 상태·폴더 계약 구현, 후보 전체 필드 자동 승격 미구현 |
| 모션·채널 패키징·게시 QA | Partial | 3초 GIF 빌더·정적 대체·반응형 HTML 프로토타입 검증, 독립 스킬·채널 패키지 미구현 |

기준 통과와 재검증 이력은 `reports/deprecated/`에 보관한다. 사용자는 [동일상품 우선 재소싱 결과](../reports/deprecated/2026/2026-07-16/resourcing-exact-identity-relaxed/report.html)의 조건부 후보 중 HDB-1 스포츠 마스크·판매가 9,900원안을 선택하고 [1차 제품기획](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/product-plan-draft.md)과 별도 [1차 콘텐츠기획](../reports/deprecated/2026/2026-07-16/hdb1-product-planning-phase1/content-plan-draft.md)을 승인했다. 실제 제품 단독 원본이 없는 상태에서 제작 방식의 품질을 확인하도록 `concept_only` 예외를 허용해 10모듈 HTML·3초 GIF·2층 QA 프로토타입을 완성했다. 실제 SKU 자산·간이 QA가 잠기기 전에는 이를 최종 승격하지 않는다.

## 3. 목표 파이프라인

```text
탐색 조건 입력
→ 도매 후보 표본화
→ 쿠팡 시장·가격·경쟁 조사
→ 비용·마진·운영 위험 평가
→ 기준 통과 후보 5개 이상 보고
→ AWAITING_USER_SELECTION
→ 사용자 상품 선택 또는 공급처 상세 URL 접수
→ 공급처 사실·옵션·후기 조사
→ 쿠팡 경쟁상품·별점 1~3점 리뷰 조사
→ 조사 결과 보고 → 사용자 오퍼 결정
→ 제품 사실·자산 계보 잠금
→ 제품기획 작성 → 사용자 해시 승인
→ 콘텐츠기획 작성 → 사용자 승인
→ 주장-근거-장면 시각 스토리보드·수치형 AC
→ 이미지·실사진·GIF·영상 소재 제작
→ 소재별 자동 QA + 육안 QA
→ 이미지+HTML 조립
→ 통합 자동 QA + 육안 QA
→ 채널 패키징
→ 최종 산출물 승격
→ 판매 성과 피드백
```

### 3.1 첫 번째 표준 프로세스: 소싱

1. 사용자 시작 모드는 `도매꾹 Best 고배수 탐색` 하나로 고정한다. 선택 카테고리를 우선하되 비워 두면 `전체`와 실제 6개 대분류를 순환해 TOP 150을 층화 표본화하고 도매 URL·공급가를 확보한다.
2. 도매꾹은 임시 로컬 headless Chrome에 Browser Harness를 연결하고, 쿠팡은 `nodriver`의 임시 headless Chrome으로 홈에 먼저 접속한 뒤 후보 검색을 직렬 처리한다. 어느 쪽도 사용자 창 포커스를 가져가거나 표시형 브라우저로 자동 전환하지 않는다.
3. 판매량순 상위 10개에서 유사상품 가격, 리뷰 근거, 일반 로켓과 판매자로켓을 수집한다.
4. 도매 배송비·로켓그로스 비용·수수료·부가세를 반영해 표준 40%/30%와 조건부 35%/25% 마진을 함께 검증한다.
5. 일반 로켓은 상위 10개 중 3개 이하만 허용하고, 판매자로켓은 진입 가능으로 본다.
6. 통과 후보가 5개가 될 때까지 다음 카테고리·순위·원산지 표본으로 반복한다.
7. 후보별 도매꾹↔쿠팡 pair URL, 공급가, 현재가, 배수와 판매 근거를 HTML·JSON으로 먼저 제공하고, 전체 검증의 추천가와 마진을 별도로 제시한 뒤 사용자 선택을 기다린다.

현재 탐색 가정은 도매 배송비 3,000원/개, 로켓그로스 비용 3,000원/개, 판매 수수료 10.8%다. 이 값은 후보 비교용이며 선택 후 실제 크기·무게·묶음배송 조건으로 다시 확정한다. 광고비는 판매 반응이 확인된 상품의 확장 단계에서만 별도 평가한다.

## 4. 플러그인 경계

### 포함 범위

- 도매꾹·도매매 등 허용된 공급처 후보 조사
- 쿠팡 공개 시장·가격·경쟁·리뷰 근거 조사
- 공급가, 수수료, 로켓그로스 비용, 부가세 기반 수익성 평가
- 사용자 후보·가격 선택 및 승인 기록
- 실제 제품 사실, 시각적 불변 특성과 자산 계보 관리
- 제품별 브랜드·오퍼의 제품기획과 장별 콘텐츠기획
- 두 계획의 사용자 승인 해시
- 이미지·GIF·영상 외부 자산과 편집 가능한 HTML·CSS 조립
- 소재별 QA와 조립 후 통합 QA
- 채널별 정적 이미지 렌더링·패키징의 후속 확장

### 제외 범위

- 공급처 자동 연락·발주·결제
- 판매 채널 계정 로그인과 자동 상품 등록
- 광고비 집행
- CAPTCHA 및 접근 통제 우회
- 확인되지 않은 인증·성능·판매량·후기 생성
- 사용자 승인 없는 상품·가격·브랜드 확정

## 5. 스킬 구성

### 5.0 단계 스킬 토폴로지 — v0.2.0

| 스킬 | 단일 책임 | 사용자 UX |
|---|---|---|
| `coupang-commerce-orchestrator` | 현재 단계·AC·차단·다음 스킬 라우팅 | 현재 상태를 먼저 보여주고 한 번에 하나의 질문 |
| `coupang-workflow-ui` | 프로젝트·단계·후보 승인·상품기획 직접 진입 확인·파일 탐색·미리보기·이미지 업로드의 브라우저 작업창과 단계 제한 Codex 실행기 | 후보 카드 클릭→가격 확정→다음 단계 또는 앞 단계 완료 사용자 확인, 파일 드롭→기존 폴더 썸네일 미리보기, Codex 진행·실패·중지 확인 |
| `coupang-product-sourcing` | 후보·시장·마진 근거 | 상품·가격 선택 대기 |
| `coupang-best-high-markup-sourcing` | Best 저단가·동일상품 고배수 탐색 일치 | 전체 소싱 검증 필요 상태 보고 |
| `coupang-product-planning` | 공급처 상세 URL 조사·Browser Harness 저평점 리뷰 직접 조사→SKU 해결 가능성→실측·라벨 근거·실험 | URL 하나로 조사 시작→결과·소구 후보 보고→사용자가 실제 SKU·타깃·판매가·묶음·판매 옵션을 결정→상품기획 해시 승인 |
| `coupang-content-studio` | 주장-근거-장면 스토리보드·ImageGen·소재 QA | 콘텐츠기획 승인 질문 |
| `coupang-detail-page-generator` | 이미지·GIF+HTML 조립과 브라우저 QA | 조립 결과와 수정 모듈 보고 |
| `coupang-publish-qa` | 순서·크롭·타이포·접근성·광고·채널 판정 | 게시 가능/차단 한 질문 |

오케스트레이터는 전문 스킬의 근거 판정이나 사용자 승인을 대신하지 않는다. 각 응답은 `현재 단계 → 완료 근거 → Acceptance Criteria → 차단 사유 → 다음 한 질문` 순서를 사용한다.

### 5.1 `coupang-product-sourcing` — 현재 구현

책임:

- TOP 150 후보 풀 층화 표본화
- 비용·시장·경쟁·운영 위험 조사
- 표준 40%/30%와 조건부 35%/25% 기여이익률 검증 및 등급 분리
- `SHORTLIST`, `WATCH`, `REJECT` 판정
- 통과 후보 5개 이상 HTML 보고서 생성
- `AWAITING_USER_SELECTION` 상태에서 중단
- 도매꾹 headless Browser Harness와 쿠팡 headless `nodriver` 역할 분리
- 쿠팡 홈 선진입, 직렬 검색, 결과 0개 시 1회 재시도와 안전 중단
- 판매량순 상위 10개 중 일반 로켓 3개 이하 허용, 판매자로켓 허용

#### `coupang-best-high-markup-sourcing` — 전용 탐색 프로필

- 도매꾹 Best 전체·카테고리 TOP 150을 일반 소싱과 같은 40%·35%·25% 순위 구간으로 층화 표본화
- 상세 원문의 개당 단가 5,000원 이하와 판매 묶음 1개를 선확정
- 쿠팡의 완전 동일 1개 상품 중 현재가가 사용자 최소 가격 배수 이상이고 리뷰 1개 이상 또는 만족 인원 100명 이상 라벨이 있는 pair가 하나라도 있으면 `HIGH_MARKUP_DISCOVERY`로 분류
- 카테고리 선택은 선택 입력으로 두고 `전체`와 도매꾹 실제 6개 대분류를 선택지로 제공
- 도매꾹 상품·개당 원가와 쿠팡 판매상품·현재가, 가격 배수, 리뷰·만족 라벨을 실제 pair 링크가 있는 HTML·JSON 보고서로 생성하고 더 싼 다른 등록은 pair 탈락 근거에서 제외
- 리뷰를 구매 발생 대리 신호로만 사용하고 정상가·다른 묶음·유사상품·미검증 동일성 오탐 차단
- 일반 가격 계산도 등록가 전체가 아니라 최근 구매 수 1건 이상 또는 리뷰 5개 이상인 동일상품 현재가 5건 이상의 중앙값을 사용하고, 판매 근거 없는 등록가는 제외
- `.agents/plugins/marketplace.json` repo marketplace와 비공개 GitHub 설치 명령을 제공해 다른 컴퓨터에서 `sm-coupang-plugin` 소스로 설치 가능
- 전체 마진·수요·경쟁·운영 검증과 사용자 승인 전 `SHORTLIST` 승격 금지

주요 산출물:

- 표본 계획 JSON
- 후보 평가 JSON
- 가격 추천 JSON
- `qualified-candidates.html`
- `handoff-shortlist.json`

### 5.2 `coupang-detail-page-generator` — 현재 부분 구현

책임:

- 제품 사실 및 정체성 잠금
- 실제 브라우저 기반 경쟁상품·리뷰 조사
- 제품별 브랜드·오퍼 제품기획과 사용자 승인
- 장별 카피·근거·자산 콘텐츠기획과 사용자 승인
- 이미지·GIF·영상 외부 자산과 편집 가능한 HTML 조립
- 실사진 교체와 GIF 실행안
- 소재별 제품 동일성·주장 근거 QA와 조립 후 반응형·접근성·광고 표현 QA

상세 게이트:

| 게이트 | 목적 | 핵심 산출물 |
|---|---|---|
| A | 제품 사실·정체성 잠금 | 사실 원장, 불변 특성, 자산 계보 |
| B | 경쟁상품·리뷰 조사 | 출처, 고객 불안 지도, 기획 원칙 |
| C | 제품기획·사용자 승인 | 타깃·문제·오퍼·주장, 브랜드, 승인 해시 |
| D | 콘텐츠기획·사용자 승인 | 장별 HTML 카피·근거·자산·QA, 승인 해시 |
| E | UI·자산 전략 | UI 가이드, 장별 제작 방식 |
| F | 제품 보존 파일럿·소재 제작 | 이미지·GIF·영상 자산, 재생성 로그 |
| G | 소재별 QA | 기술·동일성·주장·카피·시각 품질 QA |
| H | 하이브리드 조립 | HTML·CSS·패키지 manifest |
| I | 통합 QA | 흐름·브랜드·반응형·접근성·광고·채널 QA |

### 5.3 `commerce-motion-maker` — 계획

- 장별 구매 질문과 증거 유형을 GIF·짧은 영상 명세로 변환
- GIF 기본 길이 3~6초, 짧은 영상 6~15초
- 실촬영 필수 장면과 생성 가능한 보조 장면 분리
- 제품 구조·색상·사용 방식 변경 금지
- 모션 실패 시 정적 대체 이미지 제공
- 두 장 이상의 정적 프레임을 3~6초 GIF로 조립하는 빌더와 회귀 테스트는 상세페이지 스킬 내부에서 먼저 검증했다.

### 5.4 `commerce-html-builder` — 기반 구현, 독립 스킬 계획

- 상세페이지 스킬 5.3의 공통 콘텐츠 명세로 모바일 우선 반응형 미리보기 생성 완료
- 360px에서 가로 스크롤 없는 레이아웃
- 이미지 대체 텍스트, 영상 재생 제어, 모션 감소 설정 지원
- 채널 기능 제한 시 정적 이미지로 안전하게 대체
- 쿠팡 업로드용 정적 이미지와 오픈마켓용 HTML·미디어 분리
- HDB-1 `concept_only` 대표 프로젝트에서 10개 모듈, 360·800px, GIF 정지·정적 대체, 접근성·가로 넘침 검사를 통과했다.
- 공통 제작·QA 입력은 [콘텐츠 생성·조립 QA 체크리스트](CONTENT-PRODUCTION-CHECKLIST.md)로 축적한다.

### 5.5 `coupang-publish-qa` — 기본 스킬 구현, 채널 계약 확장 계획

- 제품 사실 및 자산 계보 재검증
- 한글 OCR과 승인 문구 비교
- 제품 외형·색상·구성품 일치 검사
- 과장 광고·인증·성능·비교 표현 검사
- 리뷰·평점·구매 수 출처와 최신성 검사
- 깨진 링크, 파일 누락, 용량, 접근성과 채널 규격 검사
- 실패 모듈만 이전 게이트로 롤백

### 5.6 개발 하니스와 강제 훅 — 현재 구현

- 루트와 단계별 `AGENTS.md`로 작업 경로·정본·검증 명령 라우팅
- `harness/stages.json`으로 소싱→핸드오프→상세페이지→모션→HTML→게시 QA→피드백 순서 고정
- `scripts/tdd.py`로 단계별 테스트·검증과 보고서 날짜 경로 검사
- Codex `PreToolUse`에서 테스트 선행, 위험 명령, `.env`, 보고서 경로 정책 강제
- `PostToolUse`에서 성공한 테스트 편집을 세션·turn별 기록
- `Stop`에서 현재 단계 필수 검증이 실패하면 종료 차단
- `.githooks/pre-commit`에서 변경 단계와 보고서 구조 재검증

## 6. 목표 디렉터리

```text
coupang-commerce-automation/
├─ .codex-plugin/
│  └─ plugin.json
├─ skills/
│  ├─ coupang-commerce-orchestrator/
│  ├─ coupang-workflow-ui/
│  ├─ coupang-product-sourcing/
│  ├─ coupang-best-high-markup-sourcing/
│  ├─ coupang-product-planning/
│  ├─ coupang-content-studio/
│  ├─ coupang-detail-page-generator/
│  └─ coupang-publish-qa/
├─ scripts/
│  ├─ initialize_campaign.py
│  ├─ promote_shortlist.py
│  ├─ validate_shared_contract.py
│  ├─ build_channel_package.py
│  └─ run_pipeline.py
├─ references/
│  ├─ shared-data-contract.md
│  ├─ channel-capabilities.md
│  └─ claims-and-social-proof-policy.md
└─ README.md
```

저장소의 런타임 프로젝트는 플러그인 배포 폴더와 분리해 다음 구조를 사용한다.

```text
commerce-project/
├─ schema/project-state.schema.json
├─ templates/project.json
├─ scripts/project_store.py
└─ projects/<project-id>/
   ├─ project.json
   ├─ 00-intake/
   ├─ 10-sourcing/
   ├─ 20-product-planning/
   ├─ 30-content-planning/
   ├─ 40-assets/{source,generated,motion}/
   ├─ 50-detail-page/{html,channel-packages}/
   ├─ 60-qa/
   ├─ 70-feedback/
   └─ links/
```

`reports/`는 날짜별 실행 이력 정본으로 유지하고 프로젝트에는 링크만 둔다. 기존 `detail-page/projects/`는 자동 이동하지 않는다.

`SKILL.md`에는 핵심 실행 순서만 두고, 스키마·정책·채널 규격은 `references/`, 반복 계산과 검증은 `scripts/`로 분리한다.

## 7. 공통 프로젝트 계약

Phase 2에서 `commerce-project.json`을 단일 전달 계약으로 도입한다.

```json
{
  "schema_version": "1.0.0",
  "project_id": "example-product-001",
  "workflow_status": "awaiting_user_selection",
  "product": {
    "candidate_id": "C-001",
    "supplier_url": "https://example.com/product",
    "identity_status": "pending_sample_verification"
  },
  "economics": {
    "currency": "KRW",
    "supply_cost": null,
    "target_price": null,
    "contribution_margin": null
  },
  "evidence": [],
  "claims": [],
  "assets": [],
  "approvals": [],
  "channels": {},
  "gates": {}
}
```

### 계약 원칙

- 모든 참조는 안정적인 ID를 사용한다.
- 숫자와 주장은 출처 및 검증 상태를 갖는다.
- 사용자의 후보·가격·브랜드 승인을 별도 기록한다.
- 소싱의 차별화 포인트와 증명 장면은 `hypothesis`로 전달한다.
- 실제 제품 자산과 생성 자산의 계보를 분리한다.
- 스키마 변경은 버전과 마이그레이션 규칙을 동반한다.

### 증거 상태

`CONFIRMED_USER`, `CONFIRMED_SOURCE`, `OBSERVED_IMAGE`, `OBSERVED_MARKET`, `INFERRED`, `CONFLICT`, `UNKNOWN`, `FORBIDDEN`을 사용한다. 최종 카피에는 게시 가능한 상태만 사용한다.

### 워크플로 상태

```text
initialized
→ sourced
→ awaiting_user_selection
→ shortlist_approved
→ product_verified
→ researched
→ brand_approved
→ planned
→ produced
→ qa_passed
→ packaged
```

상태는 파일 존재가 아니라 해당 게이트 검증 통과로만 변경한다.

## 8. 소싱→상세페이지 승격 계약

`promote_shortlist.py`는 사용자 승인 후보 한 건을 다음 규칙으로 승격한다.

1. 후보 ID, 상품명, 공급처 URL, 시장 근거와 가격 시나리오를 보존한다.
2. 차별화 포인트를 확정 사실이 아닌 가설로 전달한다.
3. 샘플·실물 검증 요구와 증명 장면을 미완료 상태로 전달한다.
4. 상세페이지 프로젝트의 `raw/`, `reference/`, `output/`을 초기화한다.
5. 실물 또는 사용자 확인이 없으면 제품 생성 게이트를 차단한다.
6. 공급처 가격이나 구성이 바뀌면 수익성 평가로 롤백한다.

## 9. 승인 게이트

사용자 승인이 필요한 지점은 세 곳이다.

1. 소싱 보고서에서 상품과 가격안을 선택할 때
2. 고객·문제·포지셔닝·가격·묶음·주장을 포함한 제품기획을 확정할 때
3. 카피·순서·근거·자산·QA 기준을 포함한 콘텐츠기획을 확정할 때

각 기획 승인은 현재 JSON의 SHA-256에 묶인 `actor_type: user` 기록이어야 한다. 승인 전에는 시각 소재 제작을 시작하지 않으며 승인 뒤 계획이 바뀌면 재승인을 요구한다. 일괄 제작 요청이나 에이전트 추천은 승인으로 대체하지 않는다.

## 10. QA 계약

### 소재 자동·육안 QA

- 파일·해시·형식·자산 계보
- 제품 동일성과 주장·근거 연결
- 승인 카피와 시각 증거 일치
- 크롭·생성 오류·상업적 품질

### 조립 후 통합 자동·육안 QA

- 제품기획·콘텐츠기획 정렬과 구매 흐름
- HTML·CSS·외부 자산 참조 완결성
- 모바일 반응형, 접근성, 브랜드 일관성
- 전체 문맥의 과장 광고·인증·성능·사회적 증거 위험
- 스토리보드 모듈 순서와 HTML 순서 100% 일치
- 모듈 주장-미디어 자산 연결 100%, 핵심 주장 직접 시각화 100%
- 주 피사체 가시율 95% 이상, 핵심 영역 가시율 100%
- 모듈별 주장-이미지 연관성 육안 점수 80/100 이상
- 360px·800px 한글 타이포 오류와 strict 경고 0건

두 QA가 모두 통과해야 최종본으로 승격한다. 실패는 전체 재생성이 아니라 실패 페이지와 원인 단계로 롤백한다.

`concept_only`는 조립 품질을 통과해도 실제 제품 동일성은 `blocked`다. 실제 canonical product master로 교체한 뒤 소재 QA와 통합 QA를 모두 다시 실행해야 한다.

## 11. 구현 순서

### P0. 문서·검증 기준선 — 진행 중

- [x] 플러그인 검증 통과
- [x] 소싱 테스트 37개 통과
- [x] 도매꾹 Best 사용자 공급가 상한·최소 가격 배수·리뷰/만족 라벨 기반 동일 1개 고배수 pair 탐색 스킬과 플러그인 사본 구현
- [x] 도매꾹 Best 3회차·28개 실제 조사
- [x] 기준 통과 10개 HTML 보고서와 사용자 선택 대기 상태 생성
- [x] Browser Use + `nodriver` 수집 조합 실증
- [x] PRD·ADR·ROADMAP 정리
- [x] 상세페이지 5.3 계약·GIF 빌더 대표 회귀 테스트 8개
- [x] HDB-1 `concept_only` 10모듈·3초 GIF·HTML 대표 프로토타입과 소재/통합 QA
- [x] React 프로젝트 대시보드와 9단계 필수 입력·승인·차단 UI
- [x] 공통 프로젝트 폴더·상태·목록·보고서 링크와 레거시 발견 API
- [x] 소싱 JSON 후보 카드 비교, `SHORTLIST` 클릭 선택과 상품·가격 원클릭 승인·상품기획 이동
- [x] 프로젝트 파일 탐색, HTML·이미지 인라인 미리보기와 PNG·JPG·GIF·WEBP 드래그앤드롭 업로드
- [x] 앞 단계 완료 사용자 확인으로 상품기획 직접 진입, 실측·라벨 4개 필수 입력, 저평점 리뷰 Codex 조사 역할 분리
- [x] 상품기획·상세페이지·모션의 이미지 경로 필드를 제거하고 단계 드롭존·기존 원본 자산 썸네일 미리보기로 통일
- [x] `workspace-write` Codex 자동 실행, JSONL 내장 콘솔, 프로젝트별 동시 실행 제한·중지 API와 소싱 신규 HTML·JSON 산출물 성공 게이트
- [x] 소싱 실패 이유와 현재 실행 보고서의 도매꾹 `sampled_items` 인라인 표시
- [ ] 승인된 실제 SKU 시각 대표 회귀 픽스처
- [ ] 통합 회귀 명령

### P1. 공통 계약과 연결

- [x] 프로젝트 상태·폴더 스키마 `1.0.0`
- [x] 프로젝트 생성·목록·갱신과 원자적 저장
- [ ] `promote_shortlist.py`
- [ ] 공통 계약 검증기
- [ ] 상태 전이·마이그레이션 테스트

### P2. 모션·채널 패키징·게시 QA

- [ ] 모션 제작 스킬
- [x] 하이브리드 HTML 빌더와 소재·통합 QA 기반
- [ ] 쿠팡용 정적 렌더링과 채널별 대체
- [ ] 채널 패키지 빌더
- [ ] 게시 전 통합 QA

### P3. 성과 피드백과 확장

- [ ] 판매·리뷰·반품 성과 계약
- [ ] 소싱·콘텐츠 개선 루프
- [ ] 공급처·채널 어댑터

단계별 상세 완료 조건은 [ROADMAP](ROADMAP.md)을 따른다.

## 12. 검증 순서

1. 플러그인 매니페스트·8개 스킬 검증
2. React 단계 로직·정적 빌드·프로젝트 API 검증
3. 소싱 단위 테스트
4. 공통 계약 스키마 검증
5. 소싱→상세페이지 승격 통합 테스트
6. 상세페이지 대표 프로젝트 자동 QA
7. 접촉 시트 기반 육안 QA
8. 채널 패키지 QA

## 13. 완료 산출물

- 소싱: 후보 평가, 가격 시나리오, 근거 URL, 선택 보고서
- 프로젝트: 공통 계약, 상태·승인·게이트 기록
- 제품: 사실 원장, 불변 특성, 실제·생성 자산 계보
- 조사: 경쟁상품·리뷰 출처, 고객 불안 지도
- 브랜드·기획: 브랜드 시스템, 페이지 명세, 승인 카피, UI 가이드
- 제작: 10장 이미지, 생성·수정 이력, 실사진·GIF 계획
- 출고: HTML 미리보기, 채널별 패키지, 자동·육안 QA 보고서
