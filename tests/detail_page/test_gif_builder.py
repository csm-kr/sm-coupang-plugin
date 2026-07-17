from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "coupang-detail-page-generator" / "scripts" / "build_gif.py"


def run_builder(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def test_builds_looping_crossfade_gif_with_normalized_canvas(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    output = tmp_path / "focus-loop.gif"
    Image.new("RGB", (40, 20), "#102a43").save(first)
    Image.new("RGB", (20, 40), "#4cb7b0").save(second)

    result = run_builder(
        "--frames",
        first,
        second,
        first,
        "--output",
        output,
        "--width",
        64,
        "--height",
        96,
        "--fit",
        "contain",
        "--transition-frames",
        3,
        "--hold-ms",
        300,
        "--transition-ms",
        80,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()
    with Image.open(output) as gif:
        assert gif.format == "GIF"
        assert gif.size == (64, 96)
        assert gif.n_frames == 9
        assert gif.info["loop"] == 0


def test_requires_two_or_more_input_frames(tmp_path: Path) -> None:
    only = tmp_path / "only.png"
    Image.new("RGB", (10, 10), "black").save(only)

    result = run_builder("--frames", only, "--output", tmp_path / "bad.gif")

    assert result.returncode == 2
    assert "at least two" in result.stderr.casefold()
