from __future__ import annotations

import argparse
import functools
import json
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
DASHBOARD_ROOT = SKILL_ROOT / "assets" / "dashboard"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from project_store import ProjectStore  # noqa: E402
from codex_runner import CodexRunManager  # noqa: E402


MAX_JSON_BYTES = 2 * 1024 * 1024


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: Any,
        project_store: ProjectStore,
        run_manager: CodexRunManager,
        directory: str,
        **kwargs: Any,
    ):
        self.project_store = project_store
        self.run_manager = run_manager
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args: object) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length가 올바르지 않습니다.") from exc
        if length <= 0 or length > MAX_JSON_BYTES:
            raise ValueError("JSON 본문은 1바이트 이상 2MB 이하여야 합니다.")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON 객체가 필요합니다.")
        return payload

    def _project_id(self, path: str) -> str | None:
        prefix = "/api/projects/"
        if not path.startswith(prefix):
            return None
        project_id = unquote(path[len(prefix):]).strip("/")
        return project_id if project_id and "/" not in project_id else None

    def _run_id(self, path: str) -> str | None:
        prefix = "/api/runs/"
        if not path.startswith(prefix):
            return None
        run_id = unquote(path[len(prefix):]).strip("/")
        return run_id if run_id and "/" not in run_id else None

    def _handle_error(self, error: Exception) -> None:
        if isinstance(error, FileNotFoundError):
            status = HTTPStatus.NOT_FOUND
        elif isinstance(error, FileExistsError):
            status = HTTPStatus.CONFLICT
        elif isinstance(error, (RuntimeError, PermissionError)):
            status = HTTPStatus.CONFLICT
        elif isinstance(error, (ValueError, json.JSONDecodeError, UnicodeDecodeError)):
            status = HTTPStatus.BAD_REQUEST
        else:
            status = HTTPStatus.INTERNAL_SERVER_ERROR
        self._send_json({"error": str(error)}, status)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/projects":
                self._send_json({"projects": self.project_store.list_projects()})
                return
            if path == "/api/legacy-projects":
                self._send_json({"projects": self.project_store.discover_legacy_projects()})
                return
            if path == "/api/runtime":
                self._send_json(self.run_manager.runtime_status())
                return
            if path == "/api/runs":
                project_id = parse_qs(parsed.query).get("projectId", [None])[0]
                self._send_json({"runs": self.run_manager.list_runs(project_id)})
                return
            if run_id := self._run_id(path):
                self._send_json(self.run_manager.get_run(run_id))
                return
            if project_id := self._project_id(path):
                self._send_json(self.project_store.get_project(project_id))
                return
            if path.startswith("/api/"):
                self._send_json({"error": "API 경로를 찾을 수 없습니다."}, HTTPStatus.NOT_FOUND)
                return
        except Exception as error:
            self._handle_error(error)
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/projects", "/api/runs"}:
            self._send_json({"error": "API 경로를 찾을 수 없습니다."}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            if path == "/api/runs":
                project_id = payload.get("projectId", "")
                stage_id = payload.get("stageId", "")
                project = self.project_store.get_project(project_id)
                if stage_id not in project.get("stageData", {}):
                    raise ValueError("알 수 없는 프로젝트 단계입니다.")
                allowed_stages = set(project["workflow"].get("completedStages", []))
                allowed_stages.add(project["workflow"].get("currentStage"))
                if stage_id not in allowed_stages:
                    raise PermissionError("앞 단계가 완료되지 않은 미래 단계는 실행할 수 없습니다.")
                created = self.run_manager.start_run(project_id, stage_id, payload.get("prompt", ""))
            else:
                created = self.project_store.create_project(
                    payload.get("projectId", ""),
                    payload.get("name", ""),
                    payload.get("channel", "coupang"),
                    payload.get("sourcingMode", "standard"),
                )
            self._send_json(created, HTTPStatus.CREATED)
        except Exception as error:
            self._handle_error(error)

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        project_id = self._project_id(path)
        if not project_id:
            self._send_json({"error": "프로젝트 API 경로가 올바르지 않습니다."}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json()
            self._send_json(self.project_store.update_project(project_id, payload))
        except Exception as error:
            self._handle_error(error)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        run_id = self._run_id(path)
        if not run_id:
            self._send_json({"error": "Codex 실행 API 경로가 올바르지 않습니다."}, HTTPStatus.NOT_FOUND)
            return
        try:
            self._send_json(self.run_manager.stop_run(run_id))
        except Exception as error:
            self._handle_error(error)


class DashboardServer(ThreadingHTTPServer):
    def __init__(self, *args: Any, run_manager: CodexRunManager, **kwargs: Any):
        self.run_manager = run_manager
        super().__init__(*args, **kwargs)

    def server_close(self) -> None:
        self.run_manager.stop_all()
        super().server_close()


def validate_dashboard(root: Path = DASHBOARD_ROOT) -> list[Path]:
    assets = root / "assets"
    required = [root / "index.html", SCRIPT_ROOT / "project_store.py"]
    javascript = sorted(assets.glob("*.js"))
    stylesheets = sorted(assets.glob("*.css"))
    if javascript:
        required.append(javascript[0])
    if stylesheets:
        required.append(stylesheets[0])
    missing = [path for path in required if not path.is_file()]
    if missing or not javascript or not stylesheets:
        details = ", ".join(str(path) for path in missing) or str(assets)
        raise FileNotFoundError(f"dashboard assets are incomplete: {details}")
    return required


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="쿠팡 워크플로 React 대시보드를 로컬 브라우저로 엽니다.")
    parser.add_argument("--workspace", default=".", help="commerce-project와 reports가 있는 저장소 루트")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument("--no-open", action="store_true", help="기본 브라우저를 자동으로 열지 않습니다.")
    parser.add_argument("--check", action="store_true", help="정적 빌드 자산만 확인하고 종료합니다.")
    return parser


def create_server(
    port: int,
    workspace: str | Path,
    root: Path = DASHBOARD_ROOT,
    run_manager: CodexRunManager | None = None,
) -> ThreadingHTTPServer:
    store = ProjectStore(workspace)
    runs = run_manager or CodexRunManager(store.workspace)
    handler = functools.partial(
        DashboardHandler,
        project_store=store,
        run_manager=runs,
        directory=str(root),
    )
    return DashboardServer(("127.0.0.1", port), handler, run_manager=runs)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        files = validate_dashboard()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.check:
        print(f"Dashboard ready: {len(files)} required assets found in {DASHBOARD_ROOT}")
        return 0

    try:
        server = create_server(args.port, args.workspace)
    except OSError as exc:
        print(f"대시보드 서버를 시작하지 못했습니다: {exc}", file=sys.stderr)
        return 1

    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"쿠팡 워크플로 대시보드: {url}")
    print("종료하려면 Ctrl+C를 누르세요.")
    if not args.no_open:
        threading.Timer(0.2, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
