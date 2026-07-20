# 워크플로 UI 계약

## 상태 원칙

- 스키마 버전은 `1.0.0`이다.
- 프로젝트 정본은 `<workspace>/commerce-project/projects/<project-id>/project.json`이다.
- 상태는 `project`, `workflow`, `stageData`, `folderMap`, `links`로 구성한다.
- UI의 `completed`는 사용자 진행 메모이며 전문 스킬의 테스트·QA 결과를 대체하지 않는다.
- 상품기획의 `priorStageConfirmed`는 사용자가 UI 밖에서 상품·가격 선택을 마쳤다는 진입 확인이다. 앞 단계의 `completed`·`approved`를 변경하지 않으며 `coupang-product-planning`이 SKU·가격·공급처 근거를 다시 확인한다.
- 가져오기나 API 갱신 시 프로젝트 ID, 생성 시각과 스키마 버전을 바꾸지 않는다.

## 사용자 단계

| 순서 | UI 단계 | 전문 스킬 | 승인 게이트 |
|---:|---|---|---|
| 1 | 상품 소싱 | `coupang-best-high-markup-sourcing` 시작 → `coupang-product-sourcing` 전체 게이트 재검증 | 없음 |
| 2 | 상품·가격 선택 | `coupang-commerce-orchestrator` | 사용자 상품·가격 승인 |
| 3 | 상품기획 | `coupang-product-planning` | 사용자 상품기획 승인 |
| 4 | 콘텐츠기획 | `coupang-content-studio` | 사용자 콘텐츠기획 승인 |
| 5 | 상세페이지 제작 | `coupang-detail-page-generator` | 소재·통합 QA |
| 6 | 모션 제작 | `coupang-content-studio` | 현재 부분 지원 |
| 7 | 채널 HTML | `coupang-detail-page-generator` | 현재 부분 지원 |
| 8 | 게시 전 QA | `coupang-publish-qa` | 사용자 게시 승인 |
| 9 | 판매 피드백 | `coupang-commerce-orchestrator` | 현재 계획 단계 |

앞 단계가 완료되지 않으면 뒤 단계는 `locked`다. 필수 입력과 승인 게이트를 모두 충족한 단계만 완료로 표시할 수 있다.

예외적으로 사용자가 상품기획 화면의 `앞 단계 완료 확인`을 체크하면 상품기획을 현재 단계로 열 수 있다. 이때 미완료인 소싱·상품가격 단계는 `사용자 완료 확인`으로만 표시하고 실제 완료 단계 수에는 합산하지 않는다. 확인을 취소하면 원래의 가장 이른 미완료 단계로 돌아간다.

상품기획은 `공급처 상세 URL` 하나만으로 조사를 시작할 수 있다. 이후 완료에 필요한 사용자 입력은 `사이즈·실측`, `구성`, `소재`, `관리법` 네 항목이며 각각 필수다. `실제 SKU 사진·파일 경로`와 `경쟁사 저평점 리뷰 근거` 경로 입력은 두지 않는다. 실제 SKU·라벨 이미지는 `folderMap.sourceAssets` 드롭존과 기존 폴더 미리보기로 받고, 경쟁사 별점 1~3점 리뷰 URL·조사시각·표본 범위·반복 불만은 기존 `coupang-product-planning` 스킬이 Browser Harness로 직접 조사한다. 스킬은 공급처 상세 본문·옵션·상품정보·공개 후기·문의를 조사한 결과와 소구점 후보를 먼저 보고하고, 사용자가 판매가·묶음·판매 옵션과 소구점을 고르는 오퍼 결정 게이트 전에는 기획을 확정하지 않는다.

`상품·가격 선택`은 수기 후보 ID 입력을 기본 흐름으로 사용하지 않는다. 연결된 최신 소싱 JSON의 후보를 `도매꾹 상품·개당 원가 ↔ 쿠팡 판매상품·현재가` pair 카드로 표시하고 가격 배수·리뷰 또는 만족 라벨·판정·차단 사유를 인라인으로 비교한다. 기준 배수 이상의 판매 근거 pair가 하나라도 있으면 발견으로 표시하며 낮은 가격의 다른 등록은 그 pair의 탈락 근거가 아니다. 카드 클릭으로 선택할 수 있는 상태는 전체 소싱 검증의 `SHORTLIST`뿐이다. 판매가를 확인하고 `상품·가격 확정하고 상품기획으로`를 누르면 후보 스냅샷과 보고서 경로를 `stageData.handoff.selection`에 보존하고 승인·완료·다음 단계 이동을 한 상태 갱신으로 처리한다.

소싱의 사용자 선택 카테고리는 `전체`, `패션잡화/화장품`, `의류/언더웨어`, `출산/유아동/완구`, `가구/생활/취미`, `스포츠/건강/식품`, `가전/휴대폰/산업`이며 선택 입력이다. 새 프로젝트는 카테고리 `전체`, `도매꾹 개당 공급가 상한` `5,000원`, `최소 가격 배수` `3배`를 실제 입력값으로 저장해 시작하고 사용자가 수정할 수 있다. 카테고리를 비우면 `전체`와 6개 대분류를 순환한다. 공급가 상한과 최소 가격 배수는 필수 양수 입력이며 3배·4배 같은 값을 직접 넣을 수 있다. 탐색 방식은 `high-markup` 하나만 허용하고 일반 소싱은 고배수 pair의 내부 재검증 단계로만 사용한다.

소싱 결과 영역은 실행 중 정확히 `진행중입니다.`만 표시한다. 실행 실패는 `run.error`, `turn.failed`, `error`, `artifact_validation.failed`, 종료 코드 순으로 실제 실패 이유를 찾는다. 실행이 종료 코드 0으로 끝났더라도 최신 보고서가 차단·검증 미완료이거나 실제 pair가 0건이면 보고서의 `failure_reason`, `full_sourcing_revalidation.reason`, `blocked_reason`, `final_gate_note` 순으로 원인을 표시한다. 두 경우 모두 실행 시작 이후 생성된 현재 보고서의 `candidates`·`sampled_items`에서 도매꾹 상품명·URL·카테고리·순위·확인 단가를 `도매꾹 확인 샘플`로 표시한다. 현재 실행 보고서임을 시각으로 확인하지 못하면 이전 실행 샘플을 대신 보여주지 않고 기록 없음으로 표시한다. 실제 pair가 있으면 도매꾹 URL·개당 원가와 쿠팡 URL·현재가·가격 배수가 모두 있는 카드와 HTML 보고서 링크를 제공한다. 소싱 단계의 정적 Acceptance Criteria 목록, 수기 `현재 차단 사유` 입력, `MISSING_REQUIRED_INPUTS_REQUEST_PROJECT_CONFLICT` 같은 내부 차단 코드는 주 결과 화면에 렌더링하지 않는다.

## 폴더와 보고서

- 단계 산출물은 `folderMap`의 프로젝트 상대 경로를 사용한다.
- 날짜별 실행 보고서는 기존 `reports/YYYY/YYYY-MM-DD/<run-name>/`에 유지한다.
- 프로젝트에는 보고서 상대 경로만 연결해 중복 파일과 서로 다른 정본을 만들지 않는다.
- `detail-page/projects/`의 기존 작업은 읽기 전용 레거시 목록으로 노출하고 자동 이동·삭제하지 않는다.
- 프로젝트 탐색기는 프로젝트 폴더의 실제 파일과 `links.reportRuns`의 연결 파일을 구분해 표시한다. HTML·이미지·JSON·텍스트는 같은 UI의 샌드박스 미리보기로 열고 외부 탭 열기는 보조 수단으로만 둔다. 이미지가 필요한 상품기획·상세페이지·모션 단계에는 같은 업로드 계약을 쓰는 인라인 드롭존과 `folderMap.sourceAssets` 기존 이미지 썸네일을 표시하며 이미지 폴더 경로 입력란을 두지 않는다.
- 이미지 드래그앤드롭은 `folderMap.sourceAssets`에 PNG·JPG·GIF·WEBP만 저장한다. 파일당 20MB 이하, 이미지 MIME·시그니처 일치, 안전한 단일 파일명, 중복 덮어쓰기 금지를 적용한다.

## 로컬 API

정적 빌드는 `assets/dashboard/`에 둔다. 로컬 서버는 `127.0.0.1`에서 다음 경로만 제공한다.

- `GET /api/projects`
- `POST /api/projects`
- `GET|PUT /api/projects/<project-id>`
- `GET /api/projects/<project-id>/workspace`
- `POST /api/projects/<project-id>/assets?filename=<filename>`
- `GET /api/legacy-projects`
- `GET /api/runtime`
- `GET|POST /api/runs`
- `GET|DELETE /api/runs/<run-id>`
- `GET /project-files/<project-id>/<relative-path>`

상태 파일은 2MB 이하 JSON만 받고 프로젝트 루트 밖의 경로를 쓰지 않는다. 이미지 업로드는 20MB 이하의 허용 형식만 받고 프로젝트의 원본 자산 폴더 밖에 쓰지 않는다. 프로젝트·보고서 HTML은 스크립트를 차단한 CSP와 샌드박스 iframe으로 미리본다.

## Codex 자동 실행과 콘솔

- `POST /api/runs`는 현재 단계 또는 이미 완료된 단계만 실행하며 잠긴 미래 단계는 `409`로 차단한다.
- 소싱 실행은 실제 HTML·JSON 보고서와 제품 또는 명확한 차단 결과를 생성해야 하며, 설정 배수 이상의 도매꾹↔쿠팡 pair, 두 URL, 현재가, 배수와 판매 근거를 포함하고 프로젝트 `links.reportRuns`에 연결한다.
- 프롬프트는 64KB 이하로 제한하고 셸 문자열 결합 없이 `codex --ask-for-approval never --search exec --json --sandbox workspace-write --ephemeral --cd <workspace> -`의 표준입력으로 전달한다. 설치된 전문 스킬·Browser Use 도구를 사용할 수 있도록 사용자 구성을 읽되 샌드박스와 승인 정책은 명령행에서 고정하고 세션은 저장하지 않는다.
- 소싱 완료는 프로세스 종료 코드만으로 판정하지 않는다. 실행 전 `links.reportRuns` 기준선에 없던 `reports/` 내부 HTML 상대 경로와 같은 이름의 JSON 파일이 모두 존재해야 성공이며, 없으면 `artifact_validation.failed`로 기록한다.
- 실행 종료 뒤 프로젝트 상태를 다시 읽어 신규 보고서 경로를 화면에 반영하고, 해당 `reports/` 파일은 경로 이탈을 차단한 로컬 링크로 새 탭에서 연다.
- Windows에서는 활성 `PATH`가 선택한 Codex CLI를 먼저 사용하고, 없을 때만 데스크톱 `codex.exe`를 찾는다. 서로 다른 설치가 공존할 수 있으므로 파일 종류만 보고 우선순위를 뒤집지 않는다.
- 같은 프로젝트의 동시 실행은 한 개만 허용하고 실행 중지 시 서버가 시작한 해당 Codex 실행 래퍼와 자식 프로세스 트리만 종료한다. Windows의 npm `codex.CMD` 래퍼는 단일 `terminate()`로 하위 프로세스가 남을 수 있으므로 래퍼 PID 기준 트리 종료를 사용한다.
- JSONL 이벤트는 최대 2,000개를 서버 메모리에 보관하고 브라우저가 폴링해 읽기 전용 콘솔로 표시한다. 프로젝트 상태 파일이나 보고서에는 자동 저장하지 않는다.
- 서버가 종료되면 서버가 시작한 활성 Codex 프로세스에 중지를 요청한다.
- 비대화형 실행은 승인 대기 없이 샌드박스 안의 명령을 수행하고, 허용되지 않는 작업은 실패 이벤트를 그대로 표시하며 샌드박스나 승인 정책을 자동 완화하지 않는다.
