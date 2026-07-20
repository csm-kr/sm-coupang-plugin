#!/usr/bin/env python3
"""Run Browser Harness against a temporary local headless Chrome session."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def chrome_candidates() -> list[Path]:
    candidates: list[Path] = []
    if os.environ.get("CHROME_PATH"):
        candidates.append(Path(os.environ["CHROME_PATH"]))
    for base, suffix in (
        (os.environ.get("PROGRAMFILES"), "Google/Chrome/Application/chrome.exe"),
        (os.environ.get("PROGRAMFILES(X86)"), "Google/Chrome/Application/chrome.exe"),
        (os.environ.get("LOCALAPPDATA"), "Google/Chrome/Application/chrome.exe"),
        (os.environ.get("PROGRAMFILES"), "Microsoft/Edge/Application/msedge.exe"),
    ):
        if base:
            candidates.append(Path(base) / suffix)
    return candidates


def resolve_chrome(explicit: Path | None = None) -> Path:
    candidates = [explicit] if explicit else chrome_candidates()
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("로컬 Chrome/Edge 실행 파일을 찾지 못했습니다. CHROME_PATH를 지정하세요.")


def reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_chrome_args(*, port: int, profile_dir: Path) -> list[str]:
    return [
        "--headless=new",
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={profile_dir}",
        "--window-size=1440,1200",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-mode",
        "--disable-component-update",
        "about:blank",
    ]


def build_harness_env(endpoint: str, base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env.pop("BU_NAME", None)
    env.pop("BU_CDP_WS", None)
    env["BU_CDP_URL"] = endpoint
    return env


def read_script_bytes(stream) -> bytes:
    raw = stream.read()
    if not raw.strip():
        raise ValueError("Browser Harness Python 스크립트를 표준입력으로 전달해야 합니다.")
    try:
        source = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            source = raw.decode("cp949")
        except UnicodeDecodeError as exc:
            raise ValueError("표준입력 스크립트는 UTF-8 또는 CP949여야 합니다.") from exc
    return source.encode("utf-8")


def run_harness(executable: str, script: bytes, env: dict[str, str]) -> int:
    child_env = dict(env)
    child_env["PYTHONUTF8"] = "1"
    child_env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [executable],
        input=script,
        text=False,
        env=child_env,
        check=False,
    )
    return int(result.returncode)


def wait_for_cdp(endpoint: str, process: subprocess.Popen, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "응답 없음"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"headless Chrome이 시작 중 종료되었습니다: exit={process.returncode}")
        try:
            with urlopen(f"{endpoint}/json/version", timeout=1) as response:
                payload = json.load(response)
            if payload.get("webSocketDebuggerUrl"):
                return
        except (OSError, URLError, ValueError) as exc:
            last_error = str(exc)
        time.sleep(0.1)
    raise TimeoutError(f"headless Chrome CDP 준비 시간 초과: {last_error}")


def stop_owned_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="사용자 Chrome과 분리된 로컬 headless Chrome에서 Browser Harness 스크립트를 실행합니다."
    )
    parser.add_argument("--chrome", type=Path)
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    args = parser.parse_args()

    try:
        script = read_script_bytes(sys.stdin.buffer)
    except ValueError as exc:
        parser.error(str(exc))

    harness = shutil.which("browser-harness")
    if not harness:
        raise FileNotFoundError("browser-harness 실행 파일을 찾지 못했습니다.")

    chrome = resolve_chrome(args.chrome)
    port = reserve_local_port()
    endpoint = f"http://127.0.0.1:{port}"

    with tempfile.TemporaryDirectory(prefix="domeggook-headless-") as profile_dir:
        process = subprocess.Popen(
            [str(chrome), *build_chrome_args(port=port, profile_dir=Path(profile_dir))],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            wait_for_cdp(endpoint, process, args.startup_timeout)
            return run_harness(harness, script, build_harness_env(endpoint))
        finally:
            stop_owned_process(process)


if __name__ == "__main__":
    raise SystemExit(main())
