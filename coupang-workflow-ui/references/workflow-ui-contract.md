# 워크플로 UI 계약

## 상태 원칙

- 스키마 버전은 `1.0.0`이다.
- 프로젝트 정본은 `<workspace>/commerce-project/projects/<project-id>/project.json`이다.
- 상태는 `project`, `workflow`, `stageData`, `folderMap`, `links`로 구성한다.
- UI의 `completed`는 사용자 진행 메모이며 전문 스킬의 테스트·QA 결과를 대체하지 않는다.
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

`상품·가격 선택`은 수기 후보 ID 입력을 기본 흐름으로 사용하지 않는다. 연결된 최신 소싱 JSON의 후보를 카드로 표시하고 공급가·MOQ·배송비·판매 근거 현재가·수익률·판정·차단 사유를 인라인으로 비교한다. 카드 클릭으로 선택할 수 있는 상태는 전체 소싱 검증의 `SHORTLIST`뿐이다. 판매가를 확인하고 `상품·가격 확정하고 상품기획으로`를 누르면 후보 스냅샷과 보고서 경로를 `stageData.handoff.selection`에 보존하고 승인·완료·다음 단계 이동을 한 상태 갱신으로 처리한다.

소싱의 사용자 선택 카테고리는 `전체`, `패션잡화/화장품`, `의류/언더웨어`, `출산/유아동/완구`, `가구/생활/취미`, `스포츠/건강/식품`, `가전/휴대폰/산업`이며 선택 입력이다. 미선택 시 `전체`와 6개 대분류를 순환한다. 탐색 방식은 `high-markup` 하나만 허용하고 일반 소싱은 고배수 탐색 일치의 내부 재검증 단계로만 사용한다.

## 폴더와 보고서

- 단계 산출물은 `folderMap`의 프로젝트 상대 경로를 사용한다.
- 날짜별 실행 보고서는 기존 `reports/YYYY/YYYY-MM-DD/<run-name>/`에 유지한다.
- 프로젝트에는 보고서 상대 경로만 연결해 중복 파일과 서로 다른 정본을 만들지 않는다.
- `detail-page/projects/`의 기존 작업은 읽기 전용 레거시 목록으로 노출하고 자동 이동·삭제하지 않는다.
- 프로젝트 탐색기는 프로젝트 폴더의 실제 파일과 `links.reportRuns`의 연결 파일을 구분해 표시한다. HTML·이미지·JSON·텍스트는 같은 UI의 샌드박스 미리보기로 열고 외부 탭 열기는 보조 수단으로만 둔다.
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
- 소싱 실행은 실제 HTML·JSON 보고서와 제품 또는 명확한 차단 결과를 생성해야 하며, 판매 근거 현재가·수익률 최저~최고와 최고가 판매 근거를 포함하고 프로젝트 `links.reportRuns`에 연결한다.
- 프롬프트는 64KB 이하로 제한하고 셸 문자열 결합 없이 `codex --ask-for-approval never --search exec --json --sandbox workspace-write --ephemeral --cd <workspace> -`의 표준입력으로 전달한다. 설치된 전문 스킬·Browser Use 도구를 사용할 수 있도록 사용자 구성을 읽되 샌드박스와 승인 정책은 명령행에서 고정하고 세션은 저장하지 않는다.
- 소싱 완료는 프로세스 종료 코드만으로 판정하지 않는다. 실행 전 `links.reportRuns` 기준선에 없던 `reports/` 내부 HTML 상대 경로와 같은 이름의 JSON 파일이 모두 존재해야 성공이며, 없으면 `artifact_validation.failed`로 기록한다.
- 실행 종료 뒤 프로젝트 상태를 다시 읽어 신규 보고서 경로를 화면에 반영하고, 해당 `reports/` 파일은 경로 이탈을 차단한 로컬 링크로 새 탭에서 연다.
- Windows에서는 활성 `PATH`가 선택한 Codex CLI를 먼저 사용하고, 없을 때만 데스크톱 `codex.exe`를 찾는다. 서로 다른 설치가 공존할 수 있으므로 파일 종류만 보고 우선순위를 뒤집지 않는다.
- 같은 프로젝트의 동시 실행은 한 개만 허용하고 실행 중지 시 해당 Codex 자식 프로세스만 종료한다.
- JSONL 이벤트는 최대 2,000개를 서버 메모리에 보관하고 브라우저가 폴링해 읽기 전용 콘솔로 표시한다. 프로젝트 상태 파일이나 보고서에는 자동 저장하지 않는다.
- 서버가 종료되면 서버가 시작한 활성 Codex 프로세스에 중지를 요청한다.
- 비대화형 실행은 승인 대기 없이 샌드박스 안의 명령을 수행하고, 허용되지 않는 작업은 실패 이벤트를 그대로 표시하며 샌드박스나 승인 정책을 자동 완화하지 않는다.
