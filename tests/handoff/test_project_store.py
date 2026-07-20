from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "commerce-project" / "scripts" / "project_store.py"


def load_module():
    spec = importlib.util.spec_from_file_location("project_store", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_project_builds_one_clear_stage_folder_tree(tmp_path: Path):
    store = load_module().ProjectStore(tmp_path)
    project = store.create_project(
        project_id="summer-mask-001",
        name="여름 스포츠 마스크",
        channel="coupang",
        sourcing_mode="high-markup",
    )

    project_root = tmp_path / "commerce-project" / "projects" / "summer-mask-001"
    assert project["project"]["id"] == "summer-mask-001"
    assert project["workflow"]["currentStage"] == "sourcing"
    assert (project_root / "project.json").is_file()
    for folder in (
        "00-intake",
        "10-sourcing",
        "20-product-planning",
        "30-content-planning",
        "40-assets/source",
        "40-assets/generated",
        "40-assets/motion",
        "50-detail-page/html",
        "50-detail-page/channel-packages",
        "60-qa",
        "70-feedback",
        "links",
    ):
        assert (project_root / folder).is_dir(), folder


def test_project_index_lists_current_stage_and_never_overwrites_existing_project(tmp_path: Path):
    store = load_module().ProjectStore(tmp_path)
    store.create_project("summer-mask-001", "여름 스포츠 마스크", "coupang", "high-markup")

    projects = store.list_projects()
    assert projects == [
        {
            "projectId": "summer-mask-001",
            "name": "여름 스포츠 마스크",
            "channel": "coupang",
            "sourcingMode": "high-markup",
            "status": "active",
            "currentStage": "sourcing",
            "blockedReason": None,
            "updatedAt": projects[0]["updatedAt"],
        }
    ]
    with pytest.raises(FileExistsError):
        store.create_project("summer-mask-001", "덮어쓰기", "coupang", "high-markup")


def test_update_project_rejects_schema_or_identity_changes_and_path_traversal(tmp_path: Path):
    module = load_module()
    store = module.ProjectStore(tmp_path)
    project = store.create_project("summer-mask-001", "여름 스포츠 마스크", "coupang", "high-markup")

    project["workflow"]["currentStage"] = "handoff"
    updated = store.update_project("summer-mask-001", project)
    assert updated["workflow"]["currentStage"] == "handoff"

    invalid = json.loads(json.dumps(project))
    invalid["project"]["id"] = "other-project"
    with pytest.raises(ValueError, match="프로젝트 ID"):
        store.update_project("summer-mask-001", invalid)
    removed_mode = json.loads(json.dumps(project))
    removed_mode["project"]["sourcingMode"] = "standard"
    with pytest.raises(ValueError, match="high-markup"):
        store.update_project("summer-mask-001", removed_mode)
    with pytest.raises(ValueError, match="프로젝트 ID"):
        store.get_project("../outside")
    with pytest.raises(ValueError, match="3~64자"):
        store.create_project("a", "너무 짧은 ID", "coupang", "high-markup")
    with pytest.raises(ValueError, match="high-markup"):
        store.create_project("standard-mode-001", "일반 소싱 제거", "coupang", "standard")
    with pytest.raises(ValueError, match="high-markup"):
        store.create_project("invalid-mode-001", "잘못된 방식", "coupang", "unknown")


def test_register_report_links_existing_report_without_copying_it(tmp_path: Path):
    store = load_module().ProjectStore(tmp_path)
    store.create_project("summer-mask-001", "여름 스포츠 마스크", "coupang", "high-markup")
    report = tmp_path / "reports" / "2026" / "2026-07-17" / "sample-run" / "report.html"
    report.parent.mkdir(parents=True)
    report.write_text("<h1>검증 보고서</h1>", encoding="utf-8")

    project = store.register_report("summer-mask-001", report)
    assert project["links"]["reportRuns"] == ["reports/2026/2026-07-17/sample-run/report.html"]
    repeated = store.register_report("summer-mask-001", report)
    assert repeated["links"]["reportRuns"] == [
        "reports/2026/2026-07-17/sample-run/report.html"
    ]
    assert report.is_file()
    assert not (tmp_path / "commerce-project" / "projects" / "summer-mask-001" / "report.html").exists()

    outside = tmp_path / "elsewhere" / "report.html"
    outside.parent.mkdir()
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(ValueError, match="reports"):
        store.register_report("summer-mask-001", outside)


def test_discover_legacy_workspaces_exposes_existing_detail_page_folders_read_only(tmp_path: Path):
    legacy = tmp_path / "detail-page" / "projects" / "old-project"
    legacy.mkdir(parents=True)
    (legacy / "keep.txt").write_text("legacy", encoding="utf-8")

    discovered = load_module().ProjectStore(tmp_path).discover_legacy_projects()
    assert discovered == [
        {
            "name": "old-project",
            "path": "detail-page/projects/old-project",
            "migrationStatus": "unregistered",
        }
    ]
    assert (legacy / "keep.txt").read_text(encoding="utf-8") == "legacy"


def test_project_workspace_lists_preview_files_and_safely_saves_source_images(tmp_path: Path):
    store = load_module().ProjectStore(tmp_path)
    project = store.create_project("summer-mask-001", "여름 스포츠 마스크", "coupang", "high-markup")
    project_root = tmp_path / "commerce-project" / "projects" / "summer-mask-001"
    html = project_root / "50-detail-page" / "html" / "detail-page.html"
    html.write_text("<html><body>미리보기</body></html>", encoding="utf-8")
    report = tmp_path / "reports" / "2026" / "2026-07-19" / "sample" / "report.html"
    report.parent.mkdir(parents=True)
    report.write_text("<html><body>보고서</body></html>", encoding="utf-8")
    store.register_report(project["project"]["id"], report)

    workspace = store.list_workspace_files("summer-mask-001")
    assert workspace["uploadTarget"] == "40-assets/source"
    assert any(item["path"] == "50-detail-page/html/detail-page.html" for item in workspace["files"])
    assert any(item["source"] == "report" for item in workspace["files"])
    assert store.resolve_project_file("summer-mask-001", "50-detail-page/html/detail-page.html") == html

    png = b"\x89PNG\r\n\x1a\n" + b"source-image"
    uploaded = store.save_uploaded_image("summer-mask-001", "front-view.png", "image/png", png)
    assert uploaded["path"] == "40-assets/source/front-view.png"
    assert (project_root / uploaded["path"]).read_bytes() == png

    with pytest.raises(FileExistsError):
        store.save_uploaded_image("summer-mask-001", "front-view.png", "image/png", png)
    with pytest.raises(ValueError, match="폴더 경로"):
        store.save_uploaded_image("summer-mask-001", "../outside.png", "image/png", png)
    with pytest.raises(ValueError, match="형식"):
        store.save_uploaded_image("summer-mask-001", "fake.jpg", "image/jpeg", png)


def test_project_state_schema_and_template_are_machine_readable():
    schema = json.loads(
        (ROOT / "commerce-project" / "schema" / "project-state.schema.json").read_text(encoding="utf-8")
    )
    template = json.loads(
        (ROOT / "commerce-project" / "templates" / "project.json").read_text(encoding="utf-8")
    )

    assert schema["$id"].endswith("project-state.schema.json")
    assert schema["properties"]["schemaVersion"]["const"] == "1.0.0"
    assert schema["properties"]["project"]["properties"]["sourcingMode"]["enum"] == ["high-markup"]
    assert template["schemaVersion"] == "1.0.0"
    assert template["project"]["sourcingMode"] == "high-markup"
    assert set(template["stageData"]) == {
        "sourcing",
        "handoff",
        "product-planning",
        "content-planning",
        "detail-page",
        "motion",
        "html",
        "publish-qa",
        "feedback",
    }
