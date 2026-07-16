#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / "harness" / "stages.json").is_file():
            return candidate
    raise SystemExit("프로젝트 루트를 찾지 못했습니다.")


root = project_root()
sys.path.insert(0, str(root))

from scripts.codex_hooks.pre_tool_guard import main


if __name__ == "__main__":
    raise SystemExit(main())
