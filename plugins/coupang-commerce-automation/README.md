# Coupang Commerce Automation Plugin

도매 상품 소싱부터 쿠팡 경쟁·마진 검증, 사용자 선택, 상세페이지 제작까지 연결하는 로컬 Codex 플러그인이다.

## 현재 포함된 스킬

- `coupang-product-sourcing`: 도매꾹·도매매 후보 조사, 쿠팡 근거 5개, 로켓 경쟁 판정, 로켓그로스 마진, HTML 보고서
- `coupang-detail-page-generator`: 선택 상품의 사실 잠금, 상품·콘텐츠기획 사용자 승인, 하이브리드 HTML 제작, 소재·통합 QA

## 현재 상태

- 플러그인 스캐폴드와 manifest 검증 완료
- 두 기존 스킬 포함 완료
- 1단계 소싱은 도매꾹 Browser Use + 쿠팡 `nodriver` 조합으로 실제 실행 완료
- 3회차에서 28개 후보를 조사해 10개가 기준을 통과했고, 아이스 쿨링 스카프 선택 후 가격·샘플 재검증 중
- [현재 사용자 검토 보고서](../../reports/2026/2026-07-16/resourcing-exact-identity-relaxed/report.html) 지원
- 단계별 AGENTS 라우팅, TDD 실행기와 필수 Codex 훅은 저장소 루트에서 관리
- 하이브리드 HTML 기반은 상세페이지 스킬에 구현됐고 모션, 채널별 정적 렌더링·패키징, 게시 QA는 로드맵 단계

## 개발 중 동기화

현재 원본 스킬은 저장소 루트에도 유지된다. 원본 스킬을 수정한 뒤 플러그인 사본으로 동기화하고 플러그인 검증을 다시 실행한다.

```powershell
$src = (Resolve-Path 'coupang-product-sourcing').Path
$dst = (Resolve-Path 'plugins\coupang-commerce-automation\skills\coupang-product-sourcing').Path
Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force

$src = (Resolve-Path 'coupang-detail-page-generator').Path
$dst = (Resolve-Path 'plugins\coupang-commerce-automation\skills\coupang-detail-page-generator').Path
Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force

python C:\Users\csm81\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\coupang-commerce-automation
```

현재 작업 상태는 [STATUS](../../STATUS.md), 전체 구현 순서는 [플러그인 구현 계획](../../docs/COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md)에서 관리한다.
