from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from test_qualified_report import valid_row


ROOT = Path(__file__).resolve().parents[1]


def test_accumulates_rounds_and_rotates_categories(tmp_path):
    rounds = tmp_path / "rounds"
    rounds.mkdir()
    (rounds / "round-01.json").write_text(json.dumps({"candidates": [valid_row(1), valid_row(2)]}), encoding="utf-8")
    (rounds / "round-02.json").write_text(json.dumps({"candidates": [valid_row(2), valid_row(3)]}), encoding="utf-8")
    (rounds / "round-03.json").write_text(json.dumps({"candidates": [valid_row(4), valid_row(5)]}), encoding="utf-8")
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "iterate_qualified_pool.py"),
        "--run-dir", str(tmp_path), "--categories", "패션", "생활", "디지털",
        "--goal", "5", "--max-rounds", "6",
    ], check=False)
    assert result.returncode == 0
    state = json.loads((tmp_path / "run-state.json").read_text(encoding="utf-8"))
    assert state["status"] == "COMPLETE"
    assert state["qualified_count"] == 5
    assert [row["category"] for row in state["history"]] == ["패션", "생활", "디지털"]
    cumulative = json.loads((tmp_path / "qualified-input.json").read_text(encoding="utf-8"))
    assert len(cumulative["candidates"]) == 5


def test_waits_for_next_category_input(tmp_path):
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts" / "iterate_qualified_pool.py"),
        "--run-dir", str(tmp_path), "--categories", "패션", "생활", "--goal", "5",
    ], check=False)
    assert result.returncode == 2
    state = json.loads((tmp_path / "run-state.json").read_text(encoding="utf-8"))
    assert state["status"] == "WAITING_FOR_ROUND_INPUT"
    assert state["next_category"] == "패션"
