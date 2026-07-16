from __future__ import annotations

import json
from pathlib import Path

from scripts import tdd
from scripts.codex_hooks import post_tool_record, pre_tool_guard, stop_stage_guard


def config() -> dict:
    return {
        "schema_version": "1.0",
        "stages": [
            {
                "id": "sourcing",
                "order": 1,
                "paths": ["coupang-product-sourcing/**"],
                "test_paths": ["coupang-product-sourcing/tests/**"],
                "commands": [{"name": "unit", "argv": ["python", "-m", "pytest"]}],
            },
            {
                "id": "harness",
                "order": 0,
                "paths": ["scripts/tdd.py", ".codex/hooks/**"],
                "test_paths": ["tests/harness/**"],
                "commands": [{"name": "unit", "argv": ["python", "-m", "pytest"]}],
            },
        ],
    }


def patch_payload(path: str, *, session: str = "s1", turn: str = "t1") -> dict:
    return {
        "session_id": session,
        "turn_id": turn,
        "hook_event_name": "PreToolUse",
        "tool_name": "apply_patch",
        "tool_input": {"command": f"*** Begin Patch\n*** Update File: {path}\n@@\n-old\n+new\n*** End Patch"},
    }


def test_implementation_patch_is_denied_before_test_edit(tmp_path: Path):
    decision = pre_tool_guard.evaluate(
        patch_payload("coupang-product-sourcing/scripts/pricing.py"),
        root=tmp_path,
        config=config(),
    )
    assert decision.allowed is False
    assert "테스트를 먼저" in decision.reason


def test_test_patch_is_allowed(tmp_path: Path):
    decision = pre_tool_guard.evaluate(
        patch_payload("coupang-product-sourcing/tests/test_pricing.py"),
        root=tmp_path,
        config=config(),
    )
    assert decision.allowed is True


def test_post_tool_records_successful_test_edit(tmp_path: Path):
    payload = patch_payload("coupang-product-sourcing/tests/test_pricing.py")
    payload["hook_event_name"] = "PostToolUse"
    payload["tool_response"] = {"exit_code": 0}
    post_tool_record.record(payload, root=tmp_path, config=config())

    state = json.loads((tmp_path / ".codex" / "runtime" / "s1.json").read_text(encoding="utf-8"))
    assert state["tested_turns"]["t1"] == ["sourcing"]


def test_implementation_patch_allowed_after_test_edit(tmp_path: Path):
    test_payload = patch_payload("coupang-product-sourcing/tests/test_pricing.py")
    test_payload["hook_event_name"] = "PostToolUse"
    test_payload["tool_response"] = {"exit_code": 0}
    post_tool_record.record(test_payload, root=tmp_path, config=config())

    decision = pre_tool_guard.evaluate(
        patch_payload("coupang-product-sourcing/scripts/pricing.py"),
        root=tmp_path,
        config=config(),
    )
    assert decision.allowed is True


def test_docs_patch_does_not_require_test(tmp_path: Path):
    decision = pre_tool_guard.evaluate(patch_payload("docs/ROADMAP.md"), root=tmp_path, config=config())
    assert decision.allowed is True


def test_report_outside_date_layout_is_denied(tmp_path: Path):
    decision = pre_tool_guard.evaluate(
        patch_payload("reports/latest/result.html"), root=tmp_path, config=config()
    )
    assert decision.allowed is False
    assert "reports/YYYY/YYYY-MM-DD" in decision.reason


def test_env_patch_is_denied(tmp_path: Path):
    decision = pre_tool_guard.evaluate(patch_payload(".env"), root=tmp_path, config=config())
    assert decision.allowed is False
    assert ".env" in decision.reason


def test_destructive_shell_is_denied(tmp_path: Path):
    payload = {
        "session_id": "s1",
        "turn_id": "t1",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git reset --hard"},
    }
    decision = pre_tool_guard.evaluate(payload, root=tmp_path, config=config())
    assert decision.allowed is False
    assert "파괴적" in decision.reason


def test_stop_guard_blocks_when_stage_verification_fails(tmp_path: Path):
    runtime = tmp_path / ".codex" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "s1.json").write_text(
        json.dumps({"active_stage": "sourcing", "status": "running"}), encoding="utf-8"
    )
    payload = {"session_id": "s1", "stop_hook_active": False}

    decision = stop_stage_guard.evaluate(
        payload,
        root=tmp_path,
        config=config(),
        verifier=lambda *_args, **_kwargs: tdd.VerificationResult(False, 3, "tests failed"),
    )
    assert decision.allowed is False
    assert "tests failed" in decision.reason


def test_stop_guard_allows_after_verification(tmp_path: Path):
    runtime = tmp_path / ".codex" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "s1.json").write_text(
        json.dumps({"active_stage": "sourcing", "status": "running"}), encoding="utf-8"
    )
    payload = {"session_id": "s1", "stop_hook_active": False}

    decision = stop_stage_guard.evaluate(
        payload,
        root=tmp_path,
        config=config(),
        verifier=lambda *_args, **_kwargs: tdd.VerificationResult(True, 0, "ok"),
    )
    assert decision.allowed is True


def test_project_hooks_json_registers_tdd_and_completion_events():
    root = Path(__file__).resolve().parents[2]
    payload = json.loads((root / ".codex" / "hooks.json").read_text(encoding="utf-8-sig"))
    hooks = payload["hooks"]
    assert set(hooks) == {"PreToolUse", "PostToolUse", "Stop"}
    for event in hooks.values():
        for group in event:
            for handler in group["hooks"]:
                assert handler["type"] == "command"
                assert handler["commandWindows"]
