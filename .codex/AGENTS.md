# Codex 훅 지침

- 공식 Codex `hooks.json` 이벤트와 출력 계약만 사용한다.
- 정책 로직은 `../scripts/codex_hooks/`에 두고 이 디렉터리의 파일은 얇은 실행 래퍼로 유지한다.
- 훅 변경 전 `../tests/harness/test_hooks.py`에 실패 테스트를 먼저 추가한다.
- `PreToolUse` deny는 공식 `permissionDecision: deny` 형식을 사용한다.
- `Stop`은 실패 단계의 구체적인 검증 메시지를 반환한다.
- 새 훅 또는 변경된 훅은 사용자가 `/hooks`에서 검토·신뢰해야 한다는 점을 문서에 유지한다.
