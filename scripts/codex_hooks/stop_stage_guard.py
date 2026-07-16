from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from scripts import tdd
from scripts.codex_hooks.common import HookDecision, find_root, load_state, save_state


def evaluate(
    payload: dict,
    *,
    root: Path,
    config: dict,
    verifier: Callable[..., tdd.VerificationResult] = tdd.verify_stage,
) -> HookDecision:
    session_id = payload.get("session_id")
    state = load_state(root, session_id)
    stage_id = state.get("active_stage")
    if not stage_id or state.get("status") == "verified":
        return HookDecision(True)
    result = verifier(config, stage_id, root=root)
    if result.ok:
        state["status"] = "verified"
        state["verification_message"] = result.message
        save_state(root, session_id, state)
        return HookDecision(True)
    return HookDecision(
        False,
        f"단계 종료 게이트 실패({stage_id}): {result.message}. 실패한 테스트를 수정하고 다시 검증하세요.",
    )


def main() -> int:
    payload = json.load(sys.stdin)
    root = find_root(Path(str(payload.get("cwd") or Path.cwd())))
    config = tdd.load_config(root / "harness" / "stages.json")
    decision = evaluate(payload, root=root, config=config)
    if decision.allowed:
        print(json.dumps({"continue": True}, ensure_ascii=False))
        return 0
    print(json.dumps({"decision": "block", "reason": decision.reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
