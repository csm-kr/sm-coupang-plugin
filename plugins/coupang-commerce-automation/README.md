# Coupang Commerce Automation Plugin

도매 상품 소싱부터 상품기획, 콘텐츠 스토리보드, 상세페이지 조립과 게시 전 QA까지 연결하는 로컬 Codex 플러그인이다. 오케스트레이터는 매 응답에서 현재 단계·완료 조건·차단 사유를 먼저 보여주고, 사용자에게는 한 번에 하나의 질문만 한다.

## 단계별 스킬

- `coupang-product-sourcing`: 도매꾹·도매매 후보 조사, 동일상품·동일 묶음 중 판매 근거가 있는 쿠팡 현재가 5개, 로켓 경쟁 판정, 로켓그로스 마진, HTML 보고서
- `coupang-best-high-markup-sourcing`: 도매꾹 Best 층화 표본에서 개당 5,000원 이하·쿠팡 동일 1개 상품 현재가 4배 이상·리뷰 5개 이상인 탐색 후보를 찾고 전체 소싱 게이트로 재검증
- `coupang-commerce-orchestrator`: 현재 단계 카드, 승인 게이트, 다음 전문 스킬 라우팅과 재개 지점을 관리
- `coupang-product-planning`: 경쟁사 저평점 리뷰를 선택 SKU가 해결 가능한 문제로 변환하고 1차·2차 검증 계획과 상품기획을 분리
- `coupang-content-studio`: 주장-근거-장면 스토리보드, ImageGen 구조화 프롬프트, 모델·치수 장면, 이미지·GIF 소재 QA를 관리
- `coupang-detail-page-generator`: 승인된 스토리보드와 외부 자산을 편집 가능한 HTML·CSS로 조립하고 소재·통합 QA를 수행
- `coupang-publish-qa`: 모듈 순서, 크롭, 주장-이미지 연관성, 한글 줄바꿈, 접근성, 광고 표현과 채널 규격을 수치로 판정

## 기본 UX

```text
현재 단계 → 완료된 근거 → Acceptance Criteria → 차단 사유 → 다음 한 질문
```

- 사용자가 상품·가격, 상품기획, 콘텐츠기획을 각각 승인한다.
- 제품기획·콘텐츠기획 사용자 승인 기록은 각 JSON의 SHA-256과 묶는다.
- 승인 전 다음 단계의 최종 산출물을 승격하지 않는다.
- 스토리보드는 모듈마다 주장 ID, 근거 ID, 이미지 ID, 필수 장면, 크롭 안전영역과 QA 수치를 가진다.
- HTML은 모듈 순서와 `data-claim-ids`·`data-asset-id`를 보존해 주장과 이미지가 실제로 같은 장면에 있는지 검사한다.
- 수정은 실패 모듈만 이전 단계로 되돌리고, 승인된 다른 모듈은 유지한다.

## 현재 상태

- 플러그인 스캐폴드와 manifest 검증 완료
- 오케스트레이터와 일반·고배수 소싱·상품기획·콘텐츠·상세페이지·게시 QA의 7개 스킬 구성
- 고배수 소싱은 `HIGH_MARKUP_DISCOVERY`까지만 자동 판정하며 전체 마진·수요·경쟁 검증 전 `SHORTLIST`로 승격하지 않음
- 일반 가격 계산은 최근 구매 수 1건 이상 또는 리뷰 5개 이상인 현재가만 중앙값에 포함하고 판매 근거 없는 등록가를 제외하며, 근거 표본 5건 미만은 `PRICE_REVIEW_BLOCKED` 처리
- 1단계 소싱은 도매꾹 Browser Use + 쿠팡 `nodriver` 조합으로 실제 실행 완료
- 3회차에서 28개 후보를 조사해 10개가 기준을 통과했고, HDB-1 `숨트임` 1개·9,900원 조건부 안을 선택
- 제품기획·콘텐츠기획 승인과 UI·자산 전략 완료
- `concept_only` 프로토타입은 10/10 통합 QA까지 통과했지만 판매용 승격은 금지
- 360·800px 실제 문자 좌표 기반 한글 줄바꿈·고아행·행수·잘림, 모듈 순서, 이미지 크롭과 주장-이미지 연결 검증을 상세페이지 스킬에 포함
- 판매용 분기는 6/10에서 실제 SKU 단독 원본·실측·라벨을 기다리는 `BLOCKED_IDENTITY_ASSETS`
- [현재 HDB-1 실행 보고서](../../reports/2026/2026-07-16/hdb1-visual-storyboard-qa/report.md) 지원
- 단계별 AGENTS 라우팅, TDD 실행기와 필수 Codex 훅은 저장소 루트에서 관리
- 하이브리드 HTML·3초 GIF 프로토타입 기반은 상세페이지 스킬에 구현됐고 독립 모션, 채널별 정적 렌더링·패키징, 게시 QA는 로드맵 단계

## 개발 중 동기화

현재 원본 스킬은 저장소 루트에도 유지된다. 원본 스킬을 수정한 뒤 플러그인 사본으로 동기화하고 플러그인 검증을 다시 실행한다.

```powershell
$src = (Resolve-Path 'coupang-product-sourcing').Path
$dst = (Resolve-Path 'plugins\coupang-commerce-automation\skills\coupang-product-sourcing').Path
Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force

$src = (Resolve-Path 'coupang-detail-page-generator').Path
$dst = (Resolve-Path 'plugins\coupang-commerce-automation\skills\coupang-detail-page-generator').Path
Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force

$stageSkills = @('coupang-best-high-markup-sourcing','coupang-commerce-orchestrator','coupang-product-planning','coupang-content-studio','coupang-publish-qa')
foreach ($name in $stageSkills) {
  $src = (Resolve-Path $name).Path
  $dst = Join-Path (Resolve-Path 'plugins\coupang-commerce-automation\skills').Path $name
  New-Item -ItemType Directory -Path $dst -Force | Out-Null
  Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force
}

python C:\Users\csm81\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\coupang-commerce-automation
```

현재 작업 상태는 [STATUS](../../STATUS.md), 전체 구현 순서는 [플러그인 구현 계획](../../docs/COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md)에서 관리한다.
