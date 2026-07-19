from __future__ import annotations

import importlib.util
import io
import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "coupang-workflow-ui" / "scripts" / "codex_runner.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("codex_runner", RUNNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingInput:
    def __init__(self):
        self.text = ""
        self.closed = False

    def write(self, value: str):
        self.text += value

    def flush(self):
        return None

    def close(self):
        self.closed = True


class CompletedProcess:
    def __init__(self, lines: list[dict]):
        self.stdin = RecordingInput()
        self.stdout = io.StringIO("".join(f"{json.dumps(line)}\n" for line in lines))
        self.returncode = None
        self.terminated = False

    def wait(self):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.returncode = -9


def wait_for_run(manager, run_id: str, timeout: float = 2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = manager.get_run(run_id)
        if snapshot["status"] not in {"queued", "running", "stopping"}:
            return snapshot
        time.sleep(0.01)
    raise AssertionError("Codex 실행이 제한 시간 안에 끝나지 않았습니다.")


def test_codex_runner_streams_json_events_and_never_uses_a_shell(tmp_path: Path):
    module = load_runner_module()
    calls = []
    process = CompletedProcess(
        [
            {"type": "thread.started", "thread_id": "thread-123"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "완료했습니다."}},
            {"type": "turn.completed", "usage": {"output_tokens": 12}},
        ]
    )

    def process_factory(command, **kwargs):
        calls.append((command, kwargs))
        return process

    manager = module.CodexRunManager(
        tmp_path,
        codex_command="codex-test",
        process_factory=process_factory,
    )
    started = manager.start_run("project-001", "sourcing", "소싱을 시작해줘.")
    finished = wait_for_run(manager, started["runId"])

    command, options = calls[0]
    assert command == [
        "codex-test",
        "exec",
        "--json",
        "--sandbox",
        "workspace-write",
        "--ignore-user-config",
        "--ephemeral",
        "--cd",
        str(tmp_path.resolve()),
        "-",
    ]
    assert options["shell"] is False
    assert options["cwd"] == str(tmp_path.resolve())
    assert process.stdin.text == "소싱을 시작해줘."
    assert process.stdin.closed is True
    assert finished["status"] == "succeeded"
    assert finished["threadId"] == "thread-123"
    assert [event["type"] for event in finished["events"]] == [
        "thread.started",
        "item.completed",
        "turn.completed",
    ]


def test_codex_runner_rejects_a_second_active_run_for_the_same_project(tmp_path: Path):
    module = load_runner_module()

    class BlockingOutput:
        def __iter__(self):
            return self

        def __next__(self):
            time.sleep(0.2)
            raise StopIteration

    process = CompletedProcess([])
    process.stdout = BlockingOutput()
    manager = module.CodexRunManager(
        tmp_path,
        codex_command="codex-test",
        process_factory=lambda *_args, **_kwargs: process,
    )

    first = manager.start_run("project-001", "sourcing", "첫 실행")
    try:
        try:
            manager.start_run("project-001", "sourcing", "중복 실행")
        except RuntimeError as error:
            assert "이미 실행 중" in str(error)
        else:
            raise AssertionError("같은 프로젝트의 동시 실행이 허용됐습니다.")
    finally:
        manager.stop_run(first["runId"])


def test_windows_codex_resolution_prefers_the_active_path_cli_over_an_older_desktop_binary():
    module = load_runner_module()
    calls = []

    def which(name: str):
        calls.append(name)
        return {
            "codex.exe": r"C:\Users\tester\AppData\Local\OpenAI\Codex\bin\codex.exe",
            "codex": r"C:\Users\tester\AppData\Roaming\npm\codex.CMD",
        }.get(name)

    assert module.resolve_codex_command(which=which, platform="nt").endswith("codex.CMD")
    assert calls == ["codex"]
