# 보고서 보관 규칙

> 문서 탐색: [에이전트 라우터](../AGENTS.md) · [현재 상태](../STATUS.md) · [실행 가이드](SOURCING-EXECUTION-GUIDE.md) · [TDD 하니스](DEVELOPMENT-HARNESS.md)

## 표준 경로

```text
reports/
├─ YYYY/
│  └─ YYYY-MM-DD/
│     └─ <run-name>/              # 날짜별 현재 실행 1개
│        ├─ *.html
│        ├─ *.json
│        └─ 실행별 추가 자산
└─ deprecated/
   └─ YYYY/
      └─ YYYY-MM-DD/
         └─ <run-name>/           # 이전 실행 보관
```

- 연도와 날짜는 실제 실행일을 사용한다.
- 날짜는 ISO `YYYY-MM-DD`다.
- `<run-name>`은 소문자 kebab-case다.
- 한 실행의 HTML·JSON·이미지·manifest는 같은 실행 디렉터리에 둔다.
- 임시 수집물은 `tmp/`, 검증된 최종 결과만 `reports/`에 둔다.
- 날짜별 현재 실행은 1개만 유지하고, 이전 실행은 `deprecated`에 보존한다.
- 현재·이전 실행을 덮어쓰거나 삭제하지 않는다.

## 경로 생성

```powershell
python scripts\tdd.py report-path sourcing-qualified-5
python scripts\tdd.py report-path sourcing-qualified-5 --date 2026-07-16 --create
```

`--create`를 실행하면 같은 날짜의 다른 현재 실행 디렉터리를 `reports/deprecated/YYYY/YYYY-MM-DD/`로 먼저 이동하고 새 경로를 만든다. 이동 전 모든 목적지 충돌을 사전 검사하며, 같은 활성 실행명이나 보관 목적지가 이미 존재하면 아무것도 이동하거나 덮어쓰지 않고 실패한다. 앞으로 모든 보고서 생성기는 출력 파일을 쓰기 전에 이 명령을 호출해야 한다.

구조 검증:

```powershell
python scripts\tdd.py check-reports
```

Codex `PreToolUse` 훅과 Git pre-commit은 현재·보관 경로 밖의 보고서 파일을 차단한다. `check-reports`는 경로 형식뿐 아니라 날짜별 현재 실행이 1개를 넘는지도 검사한다.

## 2026-07-16 정리 결과

| 실행 | 보관 경로 |
|---|---|
| `sourcing-initial` | `reports/deprecated/2026/2026-07-16/sourcing-initial/` |
| `nodriver-round-01` | `reports/deprecated/2026/2026-07-16/nodriver-round-01/` |
| `sourcing-qualified-5` | `reports/deprecated/2026/2026-07-16/sourcing-qualified-5/` |
| `sourcing-selection-cooling-scarf` | `reports/deprecated/2026/2026-07-16/sourcing-selection-cooling-scarf/` |
| `sourcing-recheck-cooling-scarf-v2` | `reports/deprecated/2026/2026-07-16/sourcing-recheck-cooling-scarf-v2/` |
| `sourcing-recheck-cotton-scarf-8` | `reports/deprecated/2026/2026-07-16/sourcing-recheck-cotton-scarf-8/` |

현재 보고서는 [동일상품 우선 재소싱 결과](../reports/2026/2026-07-16/resourcing-exact-identity-relaxed/report.html)다. 이전 실행은 삭제하지 않고 위 보관 경로에 남긴다.
