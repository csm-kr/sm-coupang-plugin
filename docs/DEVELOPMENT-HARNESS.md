# 단계형 TDD 하니스와 필수 훅

> 문서 탐색: [에이전트 라우터](../AGENTS.md) · [현재 상태](../STATUS.md) · [로드맵](ROADMAP.md) · [보고서 규칙](REPORTS.md)

## 목적

모든 개발을 단계별로 분리하고, 테스트를 먼저 작성하지 않은 구현 편집과 검증하지 않은 단계 종료를 기계적으로 차단한다. 문서는 정본, `AGENTS.md`는 얇은 라우터, `harness/stages.json`은 기계 판독 가능한 단계 계약이다.

이 구조는 [csm-kr/harness-framework](https://github.com/csm-kr/harness-framework)의 다음 원칙을 Codex에 맞게 적용했다.

- 문서를 source of truth로 사용하고 루트 지침은 라우터로 유지
- 작업을 독립 단계로 나누고 각 단계에 실행 가능한 Acceptance Criteria 배치
- 테스트·검증 도구를 기능 구현보다 먼저 준비
- 실행 전 가드와 단계 완료 검증의 2계층 게이트

Claude 전용 `.claude/settings.json`은 복사하지 않았다. Codex가 공식 지원하는 프로젝트 `.codex/hooks.json`의 `PreToolUse`, `PostToolUse`, `Stop` 이벤트를 사용한다. Codex 프로젝트 훅은 신뢰된 프로젝트에서만 로드되며, 새 훅 또는 변경된 훅은 `/hooks`에서 검토·신뢰해야 한다. 자세한 형식은 [Codex Hooks](https://learn.chatgpt.com/docs/hooks)와 [AGENTS.md 안내](https://learn.chatgpt.com/docs/agent-configuration/agents-md)를 따른다.

## 구성

| 구성 | 역할 |
|---|---|
| `AGENTS.md`와 하위 `AGENTS.md` | 작업 경로·정본·명령·금지선 라우팅 |
| `harness/stages.json` | 단계 순서, 적용 경로, 테스트 경로, 필수 검증 명령 |
| `scripts/tdd.py` | 단계 조회·검증·변경 파일·보고서 경로·ISSUE→RULE 승격 검사 |
| `.codex/hooks.json` | Codex 수명주기 훅 연결 |
| `scripts/codex_hooks/` | 실제 훅 정책과 테스트 가능한 함수 |
| `.githooks/pre-commit` | Git이 있는 환경의 커밋 전 보조 게이트 |
| `tests/harness/` | 하니스와 훅 자체의 TDD 회귀 테스트 |

## 단계 레지스트리

| 순서 | 단계 | 현재 상태 | 구현 경로 | 테스트 경로 |
|---:|---|---|---|---|
| 0 | `harness` | Implemented | `scripts/`, `.codex/`, `harness/` | `tests/harness/` |
| 1 | `sourcing` | Implemented | `coupang-product-sourcing/` | 해당 스킬 `tests/` |
| 2 | `handoff` | Planned | `commerce-project/` | `tests/handoff/` |
| 3 | `detail-page` | Partial | `coupang-detail-page-generator/` | `tests/detail_page/` |
| 4 | `motion` | Planned | `commerce-motion-maker/` | `tests/motion/` |
| 5 | `html` | Planned | `commerce-html-builder/` | `tests/html/` |
| 6 | `publish-qa` | Planned | `commerce-publish-qa/` | `tests/publish_qa/` |
| 7 | `feedback` | Planned | `commerce-feedback/` | `tests/feedback/` |
| 8 | `plugin` | Implemented | 플러그인 패키지 | `tests/harness/` + 플러그인 검증기 |

계획 단계의 테스트 디렉터리가 없으면 검증이 실패한다. 해당 단계의 첫 작업은 검증 도구와 실패 테스트를 만드는 것이다.

## 개발 순서

```text
관련 AGENTS·정본 읽기
→ RULE과 관련 ISSUE 확인
→ 실패 테스트 추가(RED)
→ 해당 테스트 실패 확인
→ 최소 구현(GREEN)
→ 리팩터링
→ python scripts/tdd.py verify <stage>
→ 문서·STATUS 갱신
→ 단계 종료 훅 통과
```

한 Codex turn에서 테스트 편집이 `PostToolUse`에 기록된 뒤에만 같은 단계의 구현 파일을 수정할 수 있다. 테스트와 구현을 한 패치에 같이 넣어 순서를 감추는 방식은 허용하지 않는다.

## 훅 정책

### `PreToolUse`

- 테스트 편집 기록 없는 구현 패치 차단
- 한 패치에 여러 단계가 섞이면 차단
- `git reset --hard`, 강제 push, 재귀 삭제, DB 파괴 명령 차단
- `.env` 셸 접근 차단
- 구현 파일의 셸 직접 쓰기 차단
- `reports/YYYY/YYYY-MM-DD/<run-name>/`와 `reports/deprecated/YYYY/YYYY-MM-DD/<run-name>/` 밖의 보고서 쓰기 차단

### `PostToolUse`

- 성공한 테스트 패치의 세션·turn·단계를 `.codex/runtime/`에 기록
- 현재 작업 단계를 `running`으로 표시

### `Stop`

- 현재 단계의 `harness/stages.json` 검증 명령을 실행
- 하나라도 실패하면 종료를 중단하고 실패 이유를 다음 작업 컨텍스트로 반환
- 모두 통과하면 세션 단계를 `verified`로 표시

Codex 문서가 설명하듯 `PreToolUse`는 모든 가능한 파일 변경 경로를 가로채는 완전한 보안 경계가 아니다. 그래서 AGENTS 규칙, Stop 검증과 Git pre-commit을 함께 사용한다.

## 명령

```powershell
python scripts\tdd.py list
python scripts\tdd.py route <변경할-파일>
python scripts\tdd.py verify harness
python scripts\tdd.py verify sourcing
python scripts\tdd.py verify plugin
python scripts\tdd.py verify-all --implemented-only
python scripts\tdd.py check-routing
python scripts\tdd.py check-reports
python scripts\tdd.py check-issues
```

새 보고서 실행은 출력 전에 `python scripts\tdd.py report-path <run-name> --date YYYY-MM-DD --create`로 준비한다. 이 명령은 같은 날짜의 기존 현재 실행을 `deprecated`로 보관하며, `check-reports`는 날짜별 현재 실행이 1개인지 함께 확인한다.

Git 저장소가 준비된 환경에서는 다음을 한 번 실행한다.

```powershell
git config core.hooksPath .githooks
```

현재 작업 폴더가 Git 저장소가 아니면 이 명령은 나중으로 미룬다. Codex 프로젝트 훅은 `.git` 훅과 별개이며, Codex CLI `/hooks`에서 신뢰 후 사용한다.

## 변경 규칙

- 새 단계나 디렉터리를 추가하면 `harness/stages.json`, 루트·하위 `AGENTS.md`, ROADMAP을 함께 갱신한다.
- 검증 명령을 바꾸면 먼저 `tests/harness/`의 기대 계약을 수정한다.
- 같은 원인의 독립적인 실제 실패는 `ISSUE.md`의 같은 ID에 누적한다. 3회가 되면 같은 ID를 `RULE.md`의 강제 규칙으로 승격해야 하며 `check-issues`가 누락을 차단한다.
- 훅을 완화하는 변경은 실패 사례, 대체 검증과 위험을 ADR에 기록한다.
