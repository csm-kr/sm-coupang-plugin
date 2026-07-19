from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


SCHEMA_VERSION = "1.0.0"
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
STAGE_IDS = (
    "sourcing",
    "handoff",
    "product-planning",
    "content-planning",
    "detail-page",
    "motion",
    "html",
    "publish-qa",
    "feedback",
)
FOLDER_MAP = {
    "intake": "00-intake",
    "sourcing": "10-sourcing",
    "productPlanning": "20-product-planning",
    "contentPlanning": "30-content-planning",
    "sourceAssets": "40-assets/source",
    "generatedAssets": "40-assets/generated",
    "motionAssets": "40-assets/motion",
    "detailHtml": "50-detail-page/html",
    "channelPackages": "50-detail-page/channel-packages",
    "qa": "60-qa",
    "feedback": "70-feedback",
    "links": "links",
}
IMAGE_UPLOAD_TYPES = {
    ".gif": {"image/gif"},
    ".jpg": {"image/jpeg", "image/jpg"},
    ".jpeg": {"image/jpeg", "image/jpg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
}
WORKSPACE_FILE_KINDS = {
    ".gif": "image",
    ".htm": "html",
    ".html": "html",
    ".jpeg": "image",
    ".jpg": "image",
    ".json": "json",
    ".md": "text",
    ".png": "image",
    ".txt": "text",
    ".webp": "image",
}
MAX_WORKSPACE_FILES = 1000


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_project_id(project_id: str) -> str:
    if not isinstance(project_id, str) or not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ValueError("프로젝트 ID는 3~64자의 소문자 영문·숫자·하이픈이어야 합니다.")
    return project_id


def new_project_state(
    project_id: str,
    name: str,
    channel: str,
    sourcing_mode: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    if sourcing_mode not in {"standard", "high-markup"}:
        raise ValueError("탐색 방식은 standard 또는 high-markup이어야 합니다.")
    timestamp = created_at or utc_now()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "project": {
            "id": validate_project_id(project_id),
            "name": str(name).strip(),
            "channel": str(channel).strip(),
            "sourcingMode": str(sourcing_mode).strip(),
            "status": "active",
            "createdAt": timestamp,
            "updatedAt": timestamp,
        },
        "workflow": {
            "currentStage": "sourcing",
            "completedStages": [],
            "blockedReason": None,
        },
        "stageData": {
            stage_id: {"inputs": {}, "completed": False, "approved": False}
            for stage_id in STAGE_IDS
        },
        "folderMap": deepcopy(FOLDER_MAP),
        "links": {"reportRuns": [], "legacyDetailPageProjects": []},
    }


class ProjectStore:
    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()
        self.projects_root = self.workspace / "commerce-project" / "projects"

    def _project_root(self, project_id: str) -> Path:
        validate_project_id(project_id)
        return self.projects_root / project_id

    def _state_path(self, project_id: str) -> Path:
        return self._project_root(project_id) / "project.json"

    def _write_state(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(prefix="project-", suffix=".json", dir=path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            os.replace(temporary_name, path)
        finally:
            temporary = Path(temporary_name)
            if temporary.exists():
                temporary.unlink()

    def create_project(
        self,
        project_id: str,
        name: str,
        channel: str,
        sourcing_mode: str,
    ) -> dict[str, Any]:
        if not str(name).strip():
            raise ValueError("프로젝트 이름이 필요합니다.")
        project_root = self._project_root(project_id)
        if project_root.exists():
            raise FileExistsError(f"이미 존재하는 프로젝트입니다: {project_id}")

        project_root.mkdir(parents=True)
        for relative in FOLDER_MAP.values():
            (project_root / relative).mkdir(parents=True, exist_ok=True)
        payload = new_project_state(project_id, name, channel, sourcing_mode)
        self._write_state(project_root / "project.json", payload)
        return payload

    def get_project(self, project_id: str) -> dict[str, Any]:
        path = self._state_path(project_id)
        if not path.is_file():
            raise FileNotFoundError(f"프로젝트를 찾을 수 없습니다: {project_id}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._validate_state(project_id, payload)
        return payload

    def _validate_state(self, project_id: str, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict) or payload.get("schemaVersion") != SCHEMA_VERSION:
            raise ValueError("지원하지 않는 프로젝트 상태 스키마입니다.")
        project = payload.get("project")
        if not isinstance(project, dict) or project.get("id") != project_id:
            raise ValueError("프로젝트 ID는 경로와 project.json에서 같아야 합니다.")
        if set(payload.get("stageData", {})) != set(STAGE_IDS):
            raise ValueError("프로젝트 단계 데이터가 완전하지 않습니다.")

    def update_project(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.get_project(project_id)
        candidate = deepcopy(payload)
        self._validate_state(project_id, candidate)
        candidate["project"]["createdAt"] = current["project"]["createdAt"]
        candidate["project"]["updatedAt"] = utc_now()
        self._write_state(self._state_path(project_id), candidate)
        return candidate

    def list_projects(self) -> list[dict[str, Any]]:
        if not self.projects_root.is_dir():
            return []
        projects: list[dict[str, Any]] = []
        for directory in self.projects_root.iterdir():
            if not directory.is_dir() or directory.is_symlink():
                continue
            try:
                payload = self.get_project(directory.name)
            except (FileNotFoundError, ValueError, json.JSONDecodeError):
                continue
            project = payload["project"]
            workflow = payload["workflow"]
            projects.append(
                {
                    "projectId": project["id"],
                    "name": project["name"],
                    "channel": project["channel"],
                    "sourcingMode": project["sourcingMode"],
                    "status": project["status"],
                    "currentStage": workflow["currentStage"],
                    "blockedReason": workflow.get("blockedReason"),
                    "updatedAt": project["updatedAt"],
                }
            )
        return sorted(projects, key=lambda row: (row["updatedAt"], row["projectId"]), reverse=True)

    def register_report(self, project_id: str, report_path: str | Path) -> dict[str, Any]:
        report = Path(report_path)
        if not report.is_absolute():
            report = self.workspace / report
        report = report.resolve()
        reports_root = (self.workspace / "reports").resolve()
        try:
            report.relative_to(reports_root)
        except ValueError as exc:
            raise ValueError("보고서는 workspace의 reports 경로 안에 있어야 합니다.") from exc
        if not report.is_file():
            raise FileNotFoundError(report)

        payload = self.get_project(project_id)
        relative = report.relative_to(self.workspace).as_posix()
        links = payload["links"].setdefault("reportRuns", [])
        if relative not in links:
            links.append(relative)
        return self.update_project(project_id, payload)

    def _resolve_project_file(self, project_id: str, relative_path: str | Path) -> Path:
        project_root = self._project_root(project_id).resolve()
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("프로젝트 내부 상대 경로가 필요합니다.")
        target = (project_root / relative).resolve()
        try:
            target.relative_to(project_root)
        except ValueError as exc:
            raise ValueError("프로젝트 경로 밖의 파일에는 접근할 수 없습니다.") from exc
        return target

    @staticmethod
    def _workspace_kind(path: Path) -> str:
        return WORKSPACE_FILE_KINDS.get(path.suffix.casefold(), "file")

    def _project_file_entry(self, project_id: str, path: Path) -> dict[str, Any]:
        project_root = self._project_root(project_id).resolve()
        relative = path.relative_to(project_root).as_posix()
        return {
            "name": path.name,
            "path": relative,
            "kind": self._workspace_kind(path),
            "source": "project",
            "size": path.stat().st_size,
            "href": f"/project-files/{quote(project_id)}/{quote(relative, safe='/')}",
        }

    def list_workspace_files(self, project_id: str) -> dict[str, Any]:
        payload = self.get_project(project_id)
        project_root = self._project_root(project_id).resolve()
        files: list[dict[str, Any]] = []
        for path in sorted(project_root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if len(files) >= MAX_WORKSPACE_FILES:
                break
            if path.is_symlink() or not path.is_file():
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(project_root)
            except ValueError:
                continue
            files.append(self._project_file_entry(project_id, path))

        reports_root = (self.workspace / "reports").resolve()
        for report_path in payload.get("links", {}).get("reportRuns", []):
            path = (self.workspace / str(report_path)).resolve()
            try:
                path.relative_to(reports_root)
            except ValueError:
                continue
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(self.workspace).as_posix()
            files.append(
                {
                    "name": path.name,
                    "path": relative,
                    "kind": self._workspace_kind(path),
                    "source": "report",
                    "size": path.stat().st_size,
                    "href": f"/{quote(relative, safe='/')}",
                }
            )

        upload_target = str(payload.get("folderMap", {}).get("sourceAssets", FOLDER_MAP["sourceAssets"]))
        self._resolve_project_file(project_id, upload_target)
        return {
            "projectId": project_id,
            "files": files,
            "uploadTarget": Path(upload_target).as_posix(),
            "acceptedImageTypes": sorted({mime for values in IMAGE_UPLOAD_TYPES.values() for mime in values}),
            "truncated": len(files) >= MAX_WORKSPACE_FILES,
        }

    def resolve_project_file(self, project_id: str, relative_path: str | Path) -> Path:
        target = self._resolve_project_file(project_id, relative_path)
        if not target.is_file() or target.is_symlink():
            raise FileNotFoundError("프로젝트 파일을 찾을 수 없습니다.")
        return target

    @staticmethod
    def _valid_image_signature(extension: str, body: bytes) -> bool:
        if extension == ".png":
            return body.startswith(b"\x89PNG\r\n\x1a\n")
        if extension in {".jpg", ".jpeg"}:
            return body.startswith(b"\xff\xd8\xff")
        if extension == ".gif":
            return body.startswith((b"GIF87a", b"GIF89a"))
        if extension == ".webp":
            return len(body) >= 12 and body.startswith(b"RIFF") and body[8:12] == b"WEBP"
        return False

    def save_uploaded_image(
        self,
        project_id: str,
        filename: str,
        content_type: str,
        body: bytes,
    ) -> dict[str, Any]:
        if not isinstance(filename, str) or not filename or len(filename) > 160:
            raise ValueError("업로드 파일명이 올바르지 않습니다.")
        if Path(filename).name != filename or filename in {".", ".."}:
            raise ValueError("파일명에는 폴더 경로를 넣을 수 없습니다.")
        extension = Path(filename).suffix.casefold()
        if extension not in IMAGE_UPLOAD_TYPES:
            raise ValueError("PNG, JPG, GIF, WEBP 이미지만 업로드할 수 있습니다.")
        normalized_type = str(content_type).split(";", 1)[0].strip().casefold()
        if normalized_type not in IMAGE_UPLOAD_TYPES[extension]:
            raise ValueError("파일 확장자와 이미지 형식이 일치하지 않습니다.")
        if not self._valid_image_signature(extension, body):
            raise ValueError("이미지 파일 형식 시그니처를 확인할 수 없습니다.")

        payload = self.get_project(project_id)
        upload_target = str(payload.get("folderMap", {}).get("sourceAssets", FOLDER_MAP["sourceAssets"]))
        directory = self._resolve_project_file(project_id, upload_target)
        directory.mkdir(parents=True, exist_ok=True)
        if directory.is_symlink():
            raise ValueError("심볼릭 링크 폴더에는 업로드할 수 없습니다.")
        target = self._resolve_project_file(project_id, Path(upload_target) / filename)
        try:
            with target.open("xb") as stream:
                stream.write(body)
        except FileExistsError as exc:
            raise FileExistsError(f"같은 이름의 프로젝트 파일이 이미 있습니다: {filename}") from exc
        except Exception:
            if target.exists():
                target.unlink()
            raise
        return self._project_file_entry(project_id, target)

    def discover_legacy_projects(self) -> list[dict[str, str]]:
        root = self.workspace / "detail-page" / "projects"
        if not root.is_dir():
            return []
        return [
            {
                "name": path.name,
                "path": path.relative_to(self.workspace).as_posix(),
                "migrationStatus": "unregistered",
            }
            for path in sorted(root.iterdir(), key=lambda item: item.name.casefold())
            if path.is_dir() and not path.is_symlink()
        ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="쿠팡 커머스 프로젝트 폴더와 상태를 관리합니다.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    create = subcommands.add_parser("create")
    create.add_argument("--workspace", default=".")
    create.add_argument("--id", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--channel", default="coupang")
    create.add_argument("--mode", default="standard", choices=("standard", "high-markup"))

    listing = subcommands.add_parser("list")
    listing.add_argument("--workspace", default=".")

    show = subcommands.add_parser("show")
    show.add_argument("--workspace", default=".")
    show.add_argument("--id", required=True)

    legacy = subcommands.add_parser("legacy")
    legacy.add_argument("--workspace", default=".")

    report = subcommands.add_parser("register-report")
    report.add_argument("--workspace", default=".")
    report.add_argument("--id", required=True)
    report.add_argument("--path", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = ProjectStore(args.workspace)
    if args.command == "create":
        payload = store.create_project(args.id, args.name, args.channel, args.mode)
    elif args.command == "show":
        payload = store.get_project(args.id)
    elif args.command == "legacy":
        payload = store.discover_legacy_projects()
    elif args.command == "register-report":
        payload = store.register_report(args.id, args.path)
    else:
        payload = store.list_projects()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
