# 보고서 보관 규칙

현재 보고서는 `reports/YYYY/YYYY-MM-DD/<run-name>/`, 이전 보고서는 `reports/deprecated/YYYY/YYYY-MM-DD/<run-name>/` 구조로 보관한다.

- `YYYY`는 실행일 연도, 날짜는 ISO `YYYY-MM-DD`, 실행명은 소문자 kebab-case다.
- 한 실행의 HTML, JSON, 이미지와 manifest는 같은 `<run-name>` 디렉터리에 둔다.
- 날짜별 현재 실행은 1개만 둔다. 새 실행을 시작할 때 `python scripts/tdd.py report-path <run-name> --date YYYY-MM-DD --create`를 먼저 실행해 기존 현재 실행을 `deprecated`로 자동 이동한다.
- 루트에는 이 `AGENTS.md` 외의 실행 파일을 두지 않는다.
- 임시 수집물은 `tmp/`에 두고 검증된 산출물만 보고서 디렉터리로 승격한다.
- 현재·과거 보고서를 덮어쓰거나 삭제하지 않는다. 같은 활성 실행명이나 보관 경로가 이미 있으면 실행명을 바꾸거나 충돌 원인을 확인한다.
- 보고서 내부 링크는 가능한 상대 경로로 만들고 외부 근거 URL과 관찰 상태를 보존한다.
- 모든 보고서 생성기는 출력 파일을 쓰기 전에 `report-path --create`로 디렉터리를 준비한다.
- 보고서 생성 후 `python scripts/tdd.py check-reports`를 실행한다.
