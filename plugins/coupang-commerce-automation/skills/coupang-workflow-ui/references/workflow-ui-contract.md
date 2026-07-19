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
| 1 | 상품 소싱 | `coupang-product-sourcing` 또는 `coupang-best-high-markup-sourcing` | 없음 |
| 2 | 상품·가격 선택 | `coupang-commerce-orchestrator` | 사용자 상품·가격 승인 |
| 3 | 상품기획 | `coupang-product-planning` | 사용자 상품기획 승인 |
| 4 | 콘텐츠기획 | `coupang-content-studio` | 사용자 콘텐츠기획 승인 |
| 5 | 상세페이지 제작 | `coupang-detail-page-generator` | 소재·통합 QA |
| 6 | 모션 제작 | `coupang-content-studio` | 현재 부분 지원 |
| 7 | 채널 HTML | `coupang-detail-page-generator` | 현재 부분 지원 |
| 8 | 게시 전 QA | `coupang-publish-qa` | 사용자 게시 승인 |
| 9 | 판매 피드백 | `coupang-commerce-orchestrator` | 현재 계획 단계 |

앞 단계가 완료되지 않으면 뒤 단계는 `locked`다. 필수 입력과 승인 게이트를 모두 충족한 단계만 완료로 표시할 수 있다.

## 폴더와 보고서

- 단계 산출물은 `folderMap`의 프로젝트 상대 경로를 사용한다.
- 날짜별 실행 보고서는 기존 `reports/YYYY/YYYY-MM-DD/<run-name>/`에 유지한다.
- 프로젝트에는 보고서 상대 경로만 연결해 중복 파일과 서로 다른 정본을 만들지 않는다.
- `detail-page/projects/`의 기존 작업은 읽기 전용 레거시 목록으로 노출하고 자동 이동·삭제하지 않는다.

## 로컬 API

정적 빌드는 `assets/dashboard/`에 둔다. 로컬 서버는 `127.0.0.1`에서 다음 경로만 제공한다.

- `GET /api/projects`
- `POST /api/projects`
- `GET|PUT /api/projects/<project-id>`
- `GET /api/legacy-projects`
- `GET /api/runtime`
- `GET|POST /api/runs`
- `GET|DELETE /api/runs/<run-id>`

상태 파일은 2MB 이하 JSON만 받고 프로젝트 루트 밖의 경로를 쓰지 않는다.

## Codex 자동 실행과 콘솔

- `POST /api/runs`는 현재 단계 또는 이미 완료된 단계만 실행하며 잠긴 미래 단계는 `409`로 차단한다.
- 프롬프트는 64KB 이하로 제한하고 셸 문자열 결합 없이 `codex exec --json --sandbox workspace-write --ignore-user-config --ephemeral --cd <workspace> -`의 표준입력으로 전달한다. Codex 인증은 유지하지만 자동 실행과 무관한 전역 모델·MCP 설정 및 세션 저장은 격리한다.
- Windows에서는 활성 `PATH`가 선택한 Codex CLI를 먼저 사용하고, 없을 때만 데스크톱 `codex.exe`를 찾는다. 서로 다른 설치가 공존할 수 있으므로 파일 종류만 보고 우선순위를 뒤집지 않는다.
- 같은 프로젝트의 동시 실행은 한 개만 허용하고 실행 중지 시 해당 Codex 자식 프로세스만 종료한다.
- JSONL 이벤트는 최대 2,000개를 서버 메모리에 보관하고 브라우저가 폴링해 읽기 전용 콘솔로 표시한다. 프로젝트 상태 파일이나 보고서에는 자동 저장하지 않는다.
- 서버가 종료되면 서버가 시작한 활성 Codex 프로세스에 중지를 요청한다.
- 비대화형 실행에서 추가 승인 요청은 사용자에게 팝업되지 않으므로 실패 이벤트를 그대로 표시하며 샌드박스나 승인 정책을 자동 완화하지 않는다.
