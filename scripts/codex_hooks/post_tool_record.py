from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import tdd
from scripts.codex_hooks.common import extract_patch_paths, find_root, load_state, save_state, tool_succeeded


def record(payload: dict, *, root: Path, config: dict) -> None:
    if str(payload.get("tool_name") or "") != "apply_patch" or not tool_succeeded(payload):
        return
    command = str((payload.get("tool_input") or {}).get("command") or "")
    paths = extract_patch_paths(command, root)
    session_id = payload.get("session_id")
    turn_id = str(payload.get("turn_id") or "unknown")
    state = load_state(root, session_id)
    tested_turns = state.setdefault("tested_turns", {})
    tested = set(tested_turns.get(turn_id) or [])
    touched_stages: list[str] = []
    for path in paths:
        stage_id = tdd.route_stage(config, path)
        if not stage_id:
            continue
        touched_stages.append(stage_id)
        if tdd.is_test_path(config, stage_id, path):
            tested.add(stage_id)
    if not touched_stages:
        return
    tested_turns[turn_id] = sorted(tested)
    state["active_stage"] = touched_stages[0]
    state["status"] = "running"
    save_state(root, session_id, state)


def main() -> int:
    payload = json.load(sys.stdin)
    root = find_root(Path(str(payload.get("cwd") or Path.cwd())))
    config = tdd.load_config(root / "harness" / "stages.json")
    record(payload, root=root, config=config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
