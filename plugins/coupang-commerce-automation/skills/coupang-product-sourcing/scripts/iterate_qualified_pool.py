#!/usr/bin/env python3
"""Accumulate category research rounds until five candidates qualify."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_qualified_report import qualified


def key(row: dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("wholesale_url") or "").strip()


def load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def merge(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = {key(row): row for row in existing if isinstance(row, dict) and key(row)}
    for row in incoming:
        if isinstance(row, dict) and key(row):
            merged[key(row)] = row
    return list(merged.values())


def count_qualified(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if qualified(row)[0])


def run_collector(command: str, category: str, round_number: int, output: Path) -> int:
    env = os.environ.copy()
    env.update({
        "SOURCING_CATEGORY": category,
        "SOURCING_ROUND": str(round_number),
        "SOURCING_ROUND_OUTPUT": str(output.resolve()),
    })
    return subprocess.run(shlex.split(command), env=env, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--categories", nargs="+", required=True)
    parser.add_argument("--collector-command")
    parser.add_argument("--goal", type=int, default=5)
    parser.add_argument("--max-rounds", type=int, default=30)
    args = parser.parse_args()

    goal = max(args.goal, 5)
    state_path = args.run_dir / "run-state.json"
    cumulative_path = args.run_dir / "qualified-input.json"
    state = load(state_path, {
        "schema_version": "1.0", "status": "RUNNING", "round": 0,
        "category_cursor": 0, "investigated_ids": [], "history": [],
    })
    cumulative = load(cumulative_path, {"candidates": []})
    rows = cumulative.get("candidates") or []

    while count_qualified(rows) < goal and state["round"] < args.max_rounds:
        category = args.categories[state["category_cursor"] % len(args.categories)]
        round_number = state["round"] + 1
        round_path = args.run_dir / "rounds" / f"round-{round_number:02d}.json"

        if not round_path.exists():
            if not args.collector_command:
                state["status"] = "WAITING_FOR_ROUND_INPUT"
                state["next_category"] = category
                save_atomic(state_path, state)
                break
            code = run_collector(args.collector_command, category, round_number, round_path)
            if code != 0 or not round_path.exists():
                state["status"] = "BLOCKED"
                state["blocked_reason"] = "collector_failed_or_no_output"
                state["next_category"] = category
                save_atomic(state_path, state)
                break

        payload = load(round_path, {})
        incoming = payload.get("candidates")
        if not isinstance(incoming, list):
            state["status"] = "BLOCKED"
            state["blocked_reason"] = "invalid_round_input"
            save_atomic(state_path, state)
            break

        before = count_qualified(rows)
        rows = merge(rows, incoming)
        after = count_qualified(rows)
        state["round"] = round_number
        state["category_cursor"] = (state["category_cursor"] + 1) % len(args.categories)
        state["investigated_ids"] = sorted({key(row) for row in rows if key(row)})
        state["history"].append({
            "round": round_number, "category": category,
            "new_candidates": len(incoming), "new_qualified": after - before,
            "qualified_total": after,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        })
        state["status"] = "COMPLETE" if after >= goal else "RUNNING"
        cumulative = {"schema_version": "1.0", "candidates": rows}
        save_atomic(cumulative_path, cumulative)
        save_atomic(state_path, state)

    total = count_qualified(rows)
    if total >= goal:
        state["status"] = "COMPLETE"
    elif state["round"] >= args.max_rounds and state.get("status") == "RUNNING":
        state["status"] = "EXHAUSTED"
    state["qualified_count"] = total
    state["goal"] = goal
    save_atomic(state_path, state)
    print(json.dumps({"status": state["status"], "qualified": total, "goal": goal}, ensure_ascii=False))
    return 0 if state["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
