from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from scripts import tdd
from scripts.codex_hooks.common import HookDecision, extract_patch_paths, find_root, load_state


DESTRUCTIVE = re.compile(
    r"(?:git\s+reset\s+--hard|git\s+push\s+--force|rm\s+-rf|remove-item\b[^\r\n]*-recurse|"
    r"\brd\s+/s\b|drop\s+table|truncate\s+table|format-volume|clear-disk)",
    re.IGNORECASE,
)
ENV_ACCESS = re.compile(r"(?:^|[\\/\s'\"])(?:\.env)(?:[.\\/\s'\"]|$)", re.IGNORECASE)
SHELL_WRITE = re.compile(r"(?:set-content|add-content|out-file|>>?)", re.IGNORECASE)


def evaluate(payload: dict, *, root: Path, config: dict) -> HookDecision:
    tool_name = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}
    command = str(tool_input.get("command") or "")
    if tool_name == "Bash":
        if DESTRUCTIVE.search(command):
            return HookDecision(False, "파괴적 명령은 저장소 훅 정책상 실행할 수 없습니다.")
        if ENV_ACCESS.search(command):
            return HookDecision(False, ".env 파일의 셸 접근은 저장소 훅 정책상 차단됩니다.")
        if SHELL_WRITE.search(command) and re.search(
            r"coupang-product-sourcing|coupang-detail-page-generator|scripts[\\/]", command, re.IGNORECASE
        ):
            return HookDecision(False, "구현 파일의 셸 직접 쓰기는 금지합니다. 테스트를 먼저 편집한 뒤 apply_patch를 사용하세요.")
        return HookDecision(True)

    if tool_name != "apply_patch":
        return HookDecision(True)
    paths = extract_patch_paths(command, root)
    env_paths = [
        path for path in paths
        if any(part == ".env" or part.startswith(".env.") for part in path.split("/"))
    ]
    if env_paths:
        return HookDecision(False, ".env 파일의 읽기·쓰기는 저장소 훅 정책상 차단됩니다: " + ", ".join(env_paths))
    invalid_reports = [path for path in paths if path.startswith("reports/") and not tdd.valid_report_path(path)]
    if invalid_reports:
        return HookDecision(
            False,
            "보고서는 reports/YYYY/YYYY-MM-DD/<run-name>/ 또는 reports/deprecated/YYYY/YYYY-MM-DD/<run-name>/ 아래에만 저장하세요: " + ", ".join(invalid_reports),
        )
    routed = [(path, tdd.route_stage(config, path)) for path in paths]
    stage_ids = {stage_id for _, stage_id in routed if stage_id}
    if len(stage_ids) > 1:
        return HookDecision(False, "한 번의 패치에서 여러 개발 단계를 섞지 마세요: " + ", ".join(sorted(stage_ids)))
    if not stage_ids:
        return HookDecision(True)
    stage_id = next(iter(stage_ids))
    implementation_paths = [
        path for path, routed_stage in routed
        if routed_stage == stage_id and not tdd.is_test_path(config, stage_id, path)
    ]
    if not implementation_paths:
        return HookDecision(True)
    state = load_state(root, payload.get("session_id"))
    tested = set((state.get("tested_turns") or {}).get(str(payload.get("turn_id") or "unknown"), []))
    if stage_id not in tested:
        return HookDecision(
            False,
            f"TDD GUARD: {stage_id} 구현을 바꾸기 전에 같은 turn에서 대응 테스트를 먼저 편집하세요. "
            f"대상: {', '.join(implementation_paths)}",
        )
    return HookDecision(True)


def main() -> int:
    payload = json.load(sys.stdin)
    root = find_root(Path(str(payload.get("cwd") or Path.cwd())))
    config = tdd.load_config(root / "harness" / "stages.json")
    decision = evaluate(payload, root=root, config=config)
    if decision.allowed:
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": decision.reason,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
