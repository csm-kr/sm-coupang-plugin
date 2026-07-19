# 공통 프로젝트 작업 영역 지침

이 디렉터리는 소싱부터 판매 피드백까지 한 상품의 상태와 산출물 위치를 연결하는 프로젝트 정본이다.

- 새 프로젝트는 `scripts/project_store.py create`로 만들고 기존 폴더를 덮어쓰지 않는다.
- `projects/<project-id>/project.json`을 현재 단계·입력·승인·차단·링크의 기계 판독 가능한 정본으로 사용한다.
- 프로젝트 ID는 소문자 영문·숫자·하이픈만 사용한다.
- 실행 보고서는 복사하지 않고 `reports/YYYY/YYYY-MM-DD/<run-name>/` 경로를 `links.reportRuns`에 등록한다.
- `detail-page/projects/`의 기존 작업은 자동 이동·삭제하지 않는다. 읽기 전용 레거시 항목으로 발견한 뒤 명시적으로 새 프로젝트에 연결한다.
- 프로젝트 상태 변경은 원자적으로 저장하고 `project.id`, `schemaVersion`, `createdAt`을 임의 변경하지 않는다.
- 구현 변경 전 `tests/handoff/`에 실패 테스트를 먼저 추가하고 종료 전 `python ../scripts/tdd.py verify handoff`를 실행한다.
