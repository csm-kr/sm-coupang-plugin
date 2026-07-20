from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ACTIVE_STATUSES = {"queued", "running", "stopping"}
MAX_PROMPT_BYTES = 64 * 1024
MAX_EVENTS = 2_000
MAX_EVENT_BYTES = 256 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def resolve_codex_command(
    *,
    which: Callable[[str], str | None] = shutil.which,
    platform: str = os.name,
) -> str | None:
    candidates = ("codex", "codex.exe") if platform == "nt" else ("codex",)
    for candidate in candidates:
        if resolved := which(candidate):
            return resolved
    return None


def terminate_process_tree(
    process: Any,
    *,
    platform: str = os.name,
    command_runner: Callable[..., Any] = subprocess.run,
) -> None:
    """Stop the launched Codex wrapper and every descendant it created."""
    if process.poll() is not None:
        return

    pid = getattr(process, "pid", None)
    if platform == "nt" and isinstance(pid, int) and pid > 0:
        try:
            result = command_runner(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
        except (OSError, ValueError):
            result = None
        if result is not None and result.returncode == 0:
            return

    try:
        process.terminate()
    except OSError:
        pass


class CodexRunManager:
    """Run one non-interactive Codex task per project and retain live events in memory."""

    def __init__(
        self,
        workspace: str | Path,
        *,
        codex_command: str | None = None,
        process_factory: Callable[..., Any] = subprocess.Popen,
        process_tree_terminator: Callable[[Any], None] | None = None,
    ):
        self.workspace = Path(workspace).resolve()
        self.codex_command = codex_command or resolve_codex_command()
        self.process_factory = process_factory
        self.process_tree_terminator = process_tree_terminator or terminate_process_tree
        self._lock = threading.RLock()
        self._runs: dict[str, dict[str, Any]] = {}
        self._active_by_project: dict[str, str] = {}

    def runtime_status(self) -> dict[str, Any]:
        return {
            "codexAvailable": bool(self.codex_command),
            "codexCommand": Path(self.codex_command).name if self.codex_command else None,
            "sandbox": "workspace-write",
            "approvalPolicy": "never",
            "userConfig": "loaded",
            "artifactValidation": True,
            "sessionPersistence": "ephemeral",
            "workspace": str(self.workspace),
        }

    def start_run(self, project_id: str, stage_id: str, prompt: str) -> dict[str, Any]:
        project_id = str(project_id).strip()
        stage_id = str(stage_id).strip()
        if not project_id or not stage_id:
            raise ValueError("프로젝트 ID와 단계 ID가 필요합니다.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Codex 실행 문장이 필요합니다.")
        if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError("Codex 실행 문장은 64KB 이하여야 합니다.")
        if not self.codex_command:
            raise FileNotFoundError("Codex CLI를 찾을 수 없습니다. codex 로그인을 확인해 주세요.")

        with self._lock:
            active_id = self._active_by_project.get(project_id)
            if active_id and self._runs[active_id]["status"] in ACTIVE_STATUSES:
                raise RuntimeError("이 프로젝트에서 Codex가 이미 실행 중입니다.")

            run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            record = {
                "runId": run_id,
                "projectId": project_id,
                "stageId": stage_id,
                "status": "queued",
                "startedAt": utc_now(),
                "finishedAt": None,
                "exitCode": None,
                "threadId": None,
                "error": None,
                "artifacts": [],
                "events": [],
                "_nextSequence": 0,
                "_process": None,
                "_baselineReportRuns": self._read_report_runs(project_id),
            }
            self._runs[run_id] = record
            self._active_by_project[project_id] = run_id

        worker = threading.Thread(
            target=self._execute,
            args=(run_id, prompt),
            name=f"codex-{run_id}",
            daemon=True,
        )
        worker.start()
        return self.get_run(run_id)

    def _execute(self, run_id: str, prompt: str) -> None:
        command = [
            str(self.codex_command),
            "--ask-for-approval",
            "never",
            "--search",
            "exec",
            "--json",
            "--sandbox",
            "workspace-write",
            "--ephemeral",
            "--cd",
            str(self.workspace),
            "-",
        ]
        options: dict[str, Any] = {
            "cwd": str(self.workspace),
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1,
            "shell": False,
        }
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            with self._lock:
                if self._runs[run_id]["status"] == "stopping":
                    self._finish(run_id, "stopped", None)
                    return

            process = self.process_factory(command, **options)
            stop_immediately = False
            with self._lock:
                record = self._runs[run_id]
                record["_process"] = process
                if record["status"] == "stopping":
                    stop_immediately = True
                else:
                    record["status"] = "running"

            if stop_immediately:
                self.process_tree_terminator(process)

            if process.stdin is None or process.stdout is None:
                raise RuntimeError("Codex 실행 스트림을 열지 못했습니다.")
            process.stdin.write(prompt)
            process.stdin.flush()
            process.stdin.close()

            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                self._append_event(run_id, line)

            exit_code = process.wait()
            with self._lock:
                stopping = self._runs[run_id]["status"] == "stopping"
            if stopping:
                status = "stopped"
            elif exit_code != 0:
                status = "failed"
            else:
                validation_error, artifacts = self._validate_artifacts(run_id)
                with self._lock:
                    self._runs[run_id]["artifacts"] = artifacts
                    self._runs[run_id]["error"] = validation_error
                if validation_error:
                    self._append_event(
                        run_id,
                        json.dumps(
                            {
                                "type": "artifact_validation.failed",
                                "message": validation_error,
                            },
                            ensure_ascii=False,
                        ),
                    )
                    status = "failed"
                else:
                    status = "succeeded"
            self._finish(run_id, status, exit_code)
        except Exception as error:
            self._append_event(
                run_id,
                json.dumps(
                    {"type": "error", "message": str(error)},
                    ensure_ascii=False,
                ),
            )
            with self._lock:
                stopping = self._runs[run_id]["status"] == "stopping"
                self._runs[run_id]["error"] = None if stopping else str(error)
            self._finish(run_id, "stopped" if stopping else "failed", None)

    def _append_event(self, run_id: str, line: str) -> None:
        encoded = line.encode("utf-8", errors="replace")
        if len(encoded) > MAX_EVENT_BYTES:
            line = encoded[:MAX_EVENT_BYTES].decode("utf-8", errors="replace") + "…"
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                event = {"type": "console", "text": line}
        except json.JSONDecodeError:
            event = {"type": "console", "text": line}

        with self._lock:
            record = self._runs[run_id]
            sequence = record["_nextSequence"]
            record["_nextSequence"] += 1
            event = {
                **event,
                "sequence": sequence,
                "receivedAt": utc_now(),
            }
            if event.get("type") == "thread.started" and event.get("thread_id"):
                record["threadId"] = event["thread_id"]
            record["events"].append(event)
            if len(record["events"]) > MAX_EVENTS:
                record["events"] = record["events"][-MAX_EVENTS:]

    def _finish(self, run_id: str, status: str, exit_code: int | None) -> None:
        with self._lock:
            record = self._runs[run_id]
            record["status"] = status
            record["exitCode"] = exit_code
            record["finishedAt"] = utc_now()
            record["_process"] = None
            if self._active_by_project.get(record["projectId"]) == run_id:
                self._active_by_project.pop(record["projectId"], None)

    def _project_path(self, project_id: str) -> Path | None:
        projects_root = (
            self.workspace / "commerce-project" / "projects"
        ).resolve()
        project_path = (projects_root / project_id / "project.json").resolve()
        if not project_path.is_relative_to(projects_root):
            return None
        return project_path

    def _read_report_runs(self, project_id: str) -> list[str]:
        project_path = self._project_path(project_id)
        if project_path is None or not project_path.is_file():
            return []
        try:
            payload = json.loads(project_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return []
        report_runs = payload.get("links", {}).get("reportRuns", [])
        if not isinstance(report_runs, list):
            return []
        return [value for value in report_runs if isinstance(value, str) and value.strip()]

    def _validate_artifacts(self, run_id: str) -> tuple[str | None, list[str]]:
        with self._lock:
            record = self._runs[run_id]
            if record["stageId"] != "sourcing":
                return None, []
            project_id = record["projectId"]
            baseline = set(record["_baselineReportRuns"])

        current = self._read_report_runs(project_id)
        new_reports = [path for path in current if path not in baseline]
        valid_reports: list[str] = []
        invalid_reasons: list[str] = []
        reports_root = (self.workspace / "reports").resolve()

        for relative_path in new_reports:
            candidate = Path(relative_path)
            if candidate.is_absolute() or candidate.suffix.lower() != ".html":
                invalid_reasons.append(f"HTML 상대 경로가 아님: {relative_path}")
                continue
            absolute_html = (self.workspace / candidate).resolve()
            if not absolute_html.is_relative_to(reports_root):
                invalid_reasons.append(f"reports 밖의 경로: {relative_path}")
                continue
            absolute_json = absolute_html.with_suffix(".json")
            if not absolute_html.is_file() or absolute_html.stat().st_size == 0:
                invalid_reasons.append(f"HTML 없음: {relative_path}")
                continue
            if not absolute_json.is_file() or absolute_json.stat().st_size == 0:
                invalid_reasons.append(f"JSON 없음: {absolute_json.relative_to(self.workspace).as_posix()}")
                continue
            valid_reports.append(relative_path)

        if valid_reports:
            return None, valid_reports

        detail = f" ({'; '.join(invalid_reasons)})" if invalid_reasons else ""
        return (
            "소싱 실행은 신규 HTML·JSON 보고서를 생성하고 project.json의 "
            f"links.reportRuns에 등록해야 완료됩니다.{detail}",
            [],
        )

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            if run_id not in self._runs:
                raise FileNotFoundError(f"Codex 실행을 찾을 수 없습니다: {run_id}")
            return self._snapshot(self._runs[run_id])

    def list_runs(self, project_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            records = [
                record
                for record in self._runs.values()
                if project_id is None or record["projectId"] == project_id
            ]
            records.sort(key=lambda record: (record["startedAt"], record["runId"]), reverse=True)
            return [self._snapshot(record) for record in records[:20]]

    def stop_run(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            if run_id not in self._runs:
                raise FileNotFoundError(f"Codex 실행을 찾을 수 없습니다: {run_id}")
            record = self._runs[run_id]
            if record["status"] not in ACTIVE_STATUSES:
                return self._snapshot(record)
            record["status"] = "stopping"
            process = record["_process"]

        if process is not None and process.poll() is None:
            self.process_tree_terminator(process)
            threading.Thread(target=self._kill_later, args=(process,), daemon=True).start()
        return self.get_run(run_id)

    def _kill_later(self, process: Any) -> None:
        try:
            return_code = process.wait(timeout=3)
        except (subprocess.TimeoutExpired, TypeError):
            if process.poll() is None:
                process.kill()
        else:
            if return_code is None and process.poll() is None:
                process.kill()

    def stop_all(self) -> None:
        with self._lock:
            run_ids = [run_id for run_id, record in self._runs.items() if record["status"] in ACTIVE_STATUSES]
        for run_id in run_ids:
            self.stop_run(run_id)

    @staticmethod
    def _snapshot(record: dict[str, Any]) -> dict[str, Any]:
        return deepcopy({key: value for key, value in record.items() if not key.startswith("_")})
