from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HookDecision:
    allowed: bool
    reason: str = ""


def safe_id(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(value or "unknown"))


def state_path(root: Path, session_id: object) -> Path:
    return root / ".codex" / "runtime" / f"{safe_id(session_id)}.json"


def load_state(root: Path, session_id: object) -> dict:
    path = state_path(root, session_id)
    if not path.exists():
        return {"schema_version": "1.0", "tested_turns": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_state(root: Path, session_id: object, state: dict) -> None:
    path = state_path(root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def extract_patch_paths(command: str, root: Path) -> list[str]:
    from scripts.tdd import normalize_path

    paths: list[str] = []
    pattern = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
    for match in pattern.finditer(command or ""):
        raw = match.group(1).strip()
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                raw = str(candidate.resolve().relative_to(root.resolve()))
            except ValueError:
                raw = str(candidate)
        paths.append(normalize_path(raw))
    return paths


def tool_succeeded(payload: dict) -> bool:
    response = payload.get("tool_response")
    if isinstance(response, dict):
        if response.get("is_error") is True:
            return False
        code = response.get("exit_code", response.get("returncode"))
        if code is not None and code != 0:
            return False
    return True


def find_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "harness" / "stages.json").is_file():
            return candidate
    raise FileNotFoundError("harness/stages.json을 포함한 프로젝트 루트를 찾지 못했습니다.")
