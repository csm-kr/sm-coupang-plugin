#!/usr/bin/env python3
"""Merge priced sourcing rounds by candidate id or wholesale URL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    merged = {}
    for path in args.inputs:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        for row in payload.get("candidates") or []:
            key = str(row.get("candidate_id") or row.get("wholesale_url") or "").strip()
            if key:
                merged[key] = row
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version":"1.0","candidates":list(merged.values())}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates":len(merged)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
