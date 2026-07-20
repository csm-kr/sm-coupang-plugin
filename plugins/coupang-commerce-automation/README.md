# Coupang Commerce Automation Plugin

도매 상품 소싱부터 상품기획, 콘텐츠 스토리보드, 상세페이지 조립과 게시 전 QA까지 연결하는 로컬 Codex 플러그인이다. React 로컬 대시보드는 소싱 후보를 인라인으로 비교·클릭해 상품·가격을 승인하고 다음 단계로 이동하며, 프로젝트 파일 탐색·HTML/이미지 미리보기·이미지 드래그앤드롭과 현재 Codex 실행 콘솔을 한 작업창에 제공한다. 오케스트레이터는 매 응답에서 현재 단계·완료 조건·차단 사유를 먼저 보여주며 사용자에게 한 번에 하나의 질문만 한다.

## 단계별 스킬

- `coupang-product-sourcing`: 로컬 headless Browser Harness의 도매꾹·도매매 후보 조사, headless `nodriver`의 쿠팡 동일상품·동일 묶음 판매 근거 현재가 5개, 로켓 경쟁 판정, 로켓그로스 마진, HTML 보고서
- `coupang-best-high-markup-sourcing`: 도매꾹 Best 층화 표본에서 사용자 공급가 상한·최소 가격 배수를 받고, 리뷰 또는 만족 라벨이 있는 쿠팡 동일 1개 상품 pair를 찾아 HTML·JSON으로 보고한 뒤 전체 소싱 게이트로 재검증
- `coupang-commerce-orchestrator`: 현재 단계 카드, 승인 게이트, 다음 전문 스킬 라우팅과 재개 지점을 관리
- `coupang-workflow-ui`: 프로젝트 생성·목록·현재 단계, 소싱 후보 클릭 승인, 파일 탐색·HTML/이미지 미리보기·이미지 드롭 업로드, Codex 자동 실행과 읽기 전용 실시간 콘솔을 React 로컬 작업창으로 제공
- `coupang-product-planning`: 공급처 상세 URL만으로 제품 사실과 쿠팡 저평점 리뷰를 먼저 조사하고, 결과를 바탕으로 사용자와 오퍼를 결정해 1차·2차 제품기획을 분리
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

## 브라우저 프로젝트 대시보드

저장소 루트에서 다음 명령으로 정적 빌드를 검사하고 대시보드를 연다.

```powershell
python plugins\coupang-commerce-automation\skills\coupang-workflow-ui\scripts\serve_workflow_ui.py --check --no-open
python plugins\coupang-commerce-automation\skills\coupang-workflow-ui\scripts\serve_workflow_ui.py --workspace .
```

대시보드에서 새 프로젝트를 만들면 `commerce-project/projects/<project-id>/` 아래에 `project.json`, 입력, 소싱, 상품기획, 콘텐츠기획, 원본·생성·모션 자산, 상세페이지, QA, 피드백 폴더가 생성된다. `reports/`의 날짜별 실행 보고서는 복사하지 않고 프로젝트 상태의 `links.reportRuns`에 경로만 등록한다. 기존 `detail-page/projects/`는 자동 이동·삭제하지 않고 읽기 전용 레거시 목록으로 표시한다.

소싱 뒤 `상품·가격 선택`에서는 연결된 JSON 후보를 도매꾹 상품·개당 원가와 쿠팡 판매상품·현재가, 가격 배수, 리뷰·만족 라벨의 pair 카드로 비교한다. 기준 배수 이상의 판매 근거 pair가 있으면 더 싼 다른 등록은 탐색 탈락 근거로 표시하지 않는다. `SHORTLIST` 카드 한 건을 클릭하고 판매가를 확인한 뒤 `상품·가격 확정하고 상품기획으로`를 누르면 프로젝트 상태 저장, 사용자 승인, 다음 단계 이동이 한 번에 처리된다. 차단·탐색 일치·조건부·탈락 후보는 근거와 차단 사유만 확인할 수 있고 다음 단계로 넘길 수 없다.

오른쪽 `PROJECT EXPLORER`는 프로젝트 실제 파일과 연결 보고서를 폴더별로 보여주며 HTML·이미지·JSON·텍스트를 UI 안에서 미리본다. PNG·JPG·GIF·WEBP는 드래그앤드롭하거나 클릭해 `40-assets/source`에 저장한다. 파일당 20MB 이하만 허용하며 경로 포함 파일명, 이미지 형식 불일치와 기존 파일 덮어쓰기는 차단한다.

UI 밖에서는 `coupang-product-planning`에 공급처 상세 URL 하나만 전달해 검색을 시작할 수 있다. 스킬이 상세 본문·옵션·상품정보·공개 후기·문의를 읽어 색상·사이즈·구성·소재·관리법을 먼저 찾고, 쿠팡 경쟁상품 5개 이상과 접근 가능한 별점 1~3점 리뷰를 조사한다. 결과를 먼저 보고한 뒤 실제 SKU·타깃·소구·판매가·묶음·판매 옵션을 사용자와 결정하며, 실물 대조가 필요한 값만 사진·라벨·측정으로 요청한다. 현재 UI의 기존 선입력 폼은 호환용으로 남아 있어 검색 결과 기반 후속 결정 UI로의 정렬이 필요하다.

필수 입력을 채운 뒤 `Codex 작업 시작`을 누르면 UI 서버가 현재 단계의 전문 스킬을 `codex --ask-for-approval never --search exec --json --sandbox workspace-write --ephemeral`로 실행한다. 소싱의 카테고리는 `전체`와 도매꾹 실제 6개 대분류 중 선택할 수 있고 비워 두어도 되며, 개당 공급가 상한과 최소 가격 배수는 필수로 입력한다. 시작 방식은 `도매꾹 Best 고배수 pair 탐색` 하나로 고정된다. 소싱 실행은 설명만 반환하지 않고 실제 제품 또는 명확한 차단 결과가 담긴 신규 HTML·JSON 보고서를 만들고 프로젝트 보고서 링크에 등록해야 성공한다. 설치된 플러그인·Browser Use 도구는 읽되 샌드박스와 승인 대기 없음 정책은 명령행에서 고정하고 세션은 저장하지 않는다. 진행 이벤트와 최종 응답은 같은 화면의 `Codex 실행 콘솔`에 표시되며 실행 중지 버튼을 제공한다. 실행 실패뿐 아니라 완료 후 검증 차단·pair 0건도 실제 실패 이유와 현재 실행에서 확인한 도매꾹 샘플을 상품명·원문 링크·카테고리·순위·확인 단가로 표시하고, 새 보고서 링크를 자동 갱신해 브라우저에서 열 수 있다. Codex CLI 설치와 로그인이 필요하다.

콘솔은 일반 셸 입력을 받지 않는다. 같은 프로젝트의 Codex 작업은 한 번에 하나만 실행하고 잠긴 미래 단계는 차단한다. 샌드박스에서 허용되지 않은 작업은 실패 상태를 표시하며 `danger-full-access`나 승인·샌드박스 우회로 자동 전환하지 않는다. 콘솔 로그는 서버 메모리에만 있어 UI 서버를 다시 시작하면 복구되지 않는다.

UI의 완료 체크는 사용자의 진행 메모다. 실제 단계 통과는 각 전문 스킬의 근거·테스트·자동 및 육안 QA 결과로만 확정한다.

## 현재 상태

- 플러그인 스캐폴드와 manifest 검증 완료
- 오케스트레이터·브라우저 프로젝트 UI와 일반·고배수 소싱·상품기획·콘텐츠·상세페이지·게시 QA의 8개 스킬 구성
- React 19·Vite 정적 대시보드, `127.0.0.1` 프로젝트·Codex 실행 API, 읽기 전용 내장 콘솔과 `commerce-project` 단계별 폴더 관리자 구현
- 고배수 소싱은 `HIGH_MARKUP_DISCOVERY`까지만 자동 판정하며 전체 마진·수요·경쟁 검증 전 `SHORTLIST`로 승격하지 않음
- 소싱 UI는 고배수 탐색 단일 모드이며 카테고리는 선택 입력. 미선택 시 `전체`와 실제 6개 대분류 순환
- 고배수 결과는 실제 도매꾹↔쿠팡 pair URL, 공급가, 현재가, 가격 배수와 리뷰·만족 판매 근거를 HTML·JSON으로 생성
- 고배수 실패·차단 결과는 사람이 읽을 수 있는 실패 이유와 이번 실행의 `sampled_items`를 보존하고 UI에 도매꾹 샘플 목록으로 표시
- 일반 가격 계산은 최근 구매 수 1건 이상 또는 리뷰 5개 이상인 현재가만 중앙값에 포함하고 판매 근거 없는 등록가를 제외하며, 근거 표본 5건 미만은 `PRICE_REVIEW_BLOCKED` 처리
- 1단계 소싱은 도매꾹 headless Browser Harness + 쿠팡 headless `nodriver` 조합으로 구현되며 사용자 Chrome·활성 창·키보드 포커스와 격리
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

Push-Location 'coupang-workflow-ui\assets\react-app'
npm ci
npm test
npm run build
Pop-Location

$src = (Resolve-Path 'coupang-workflow-ui').Path
$dst = Join-Path (Resolve-Path 'plugins\coupang-commerce-automation\skills').Path 'coupang-workflow-ui'
robocopy $src $dst /E /XD node_modules | Out-Null

python C:\Users\csm81\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py plugins\coupang-commerce-automation
```

## 다른 컴퓨터에 설치

이 비공개 저장소에 접근할 수 있는 GitHub 계정으로 인증한 뒤 repo marketplace를 등록한다.

```powershell
gh auth login
codex plugin marketplace add csm-kr/sm-coupang-plugin --ref main
codex plugin add coupang-commerce-automation@sm-coupang-plugin
codex plugin list
```

로컬 복제본을 마켓플레이스로 사용할 때는 저장소 루트에서 `codex plugin marketplace add .`를 실행해도 된다. 설치 또는 업데이트 후에는 Codex 앱을 다시 열고 새 대화에서 플러그인을 사용한다. 저장소가 비공개이므로 GitHub 접근 권한이 없는 컴퓨터나 계정에서는 설치할 수 없다.

현재 작업 상태는 [STATUS](../../STATUS.md), 전체 구현 순서는 [플러그인 구현 계획](../../docs/COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md)에서 관리한다.
