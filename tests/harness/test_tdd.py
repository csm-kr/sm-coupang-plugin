from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import tdd


ROOT = Path(__file__).resolve().parents[2]


def test_pre_commit_uses_windows_compatible_python_shebang():
    first_line = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "#!/usr/bin/env python"


def write_config(tmp_path: Path) -> Path:
    payload = {
        "schema_version": "1.0",
        "report_path_pattern": "reports/{year}/{date}/{run_name}",
        "stages": [
            {
                "id": "sourcing",
                "order": 1,
                "paths": ["coupang-product-sourcing/**"],
                "test_paths": ["coupang-product-sourcing/tests/**"],
                "commands": [
                    {"name": "unit", "argv": ["python", "-c", "print('ok')"]}
                ],
            },
            {
                "id": "detail-page",
                "order": 3,
                "paths": ["coupang-detail-page-generator/**"],
                "test_paths": ["tests/detail_page/**"],
                "commands": [],
            },
        ],
    }
    path = tmp_path / "stages.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_stages_orders_and_indexes(tmp_path: Path):
    config = tdd.load_config(write_config(tmp_path))
    assert [stage["id"] for stage in config["stages"]] == ["sourcing", "detail-page"]
    assert tdd.stage_by_id(config, "sourcing")["order"] == 1


def test_repository_stage_descriptions_route_hybrid_detail_and_channel_packaging():
    config = tdd.load_config(ROOT / "harness" / "stages.json")
    stages = {stage["id"]: stage for stage in config["stages"]}

    assert "하이브리드 HTML" in stages["detail-page"]["description"]
    assert "사용자 승인" in stages["detail-page"]["description"]
    assert "채널별 정적 렌더링" in stages["html"]["description"]


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("coupang-product-sourcing/scripts/pricing.py", "sourcing"),
        ("coupang-product-sourcing/tests/test_pricing.py", "sourcing"),
        ("coupang-detail-page-generator/scripts/render.py", "detail-page"),
        ("docs/ROADMAP.md", None),
    ],
)
def test_route_path_to_stage(tmp_path: Path, path: str, expected: str | None):
    config = tdd.load_config(write_config(tmp_path))
    assert tdd.route_stage(config, path) == expected


@pytest.mark.parametrize(
    ("path", "valid"),
    [
        ("reports/2026/2026-07-16/sourcing-qualified-5/result.html", True),
        ("reports/2026/2026-07-16/run.json", True),
        ("reports/deprecated/2026/2026-07-16/sourcing-old/result.html", True),
        ("reports/AGENTS.md", True),
        ("reports/sourcing-qualified-5/result.html", False),
        ("reports/2026/07-16/result.html", False),
        ("reports/deprecated/2026/07-16/result.html", False),
    ],
)
def test_report_layout(path: str, valid: bool):
    assert tdd.valid_report_path(path) is valid


def test_report_dir_uses_year_and_iso_date(tmp_path: Path):
    result = tdd.report_dir(tmp_path, "sourcing-qualified-5", "2026-07-16")
    assert result == tmp_path / "reports" / "2026" / "2026-07-16" / "sourcing-qualified-5"


def test_prepare_report_dir_archives_older_active_runs(tmp_path: Path):
    day = tmp_path / "reports" / "2026" / "2026-07-16"
    for name in ("old-a", "old-b"):
        run = day / name
        run.mkdir(parents=True)
        (run / "result.json").write_text("{}", encoding="utf-8")

    current = tdd.prepare_report_dir(tmp_path, "current-run", "2026-07-16")

    assert current == day / "current-run"
    assert [path.name for path in day.iterdir()] == ["current-run"]
    assert (tmp_path / "reports" / "deprecated" / "2026" / "2026-07-16" / "old-a" / "result.json").is_file()
    assert (tmp_path / "reports" / "deprecated" / "2026" / "2026-07-16" / "old-b" / "result.json").is_file()


def test_prepare_report_dir_rejects_existing_active_run(tmp_path: Path):
    current = tmp_path / "reports" / "2026" / "2026-07-16" / "current-run"
    current.mkdir(parents=True)
    (current / "result.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError, match="활성 보고서"):
        tdd.prepare_report_dir(tmp_path, "current-run", "2026-07-16")


def test_prepare_report_dir_preflights_archive_collisions(tmp_path: Path):
    day = tmp_path / "reports" / "2026" / "2026-07-16"
    for name in ("old-a", "old-b"):
        (day / name).mkdir(parents=True)
    archived = tmp_path / "reports" / "deprecated" / "2026" / "2026-07-16" / "old-b"
    archived.mkdir(parents=True)

    with pytest.raises(FileExistsError, match="deprecated 보고서"):
        tdd.prepare_report_dir(tmp_path, "current-run", "2026-07-16")

    assert (day / "old-a").is_dir()
    assert (day / "old-b").is_dir()
    assert not (day / "current-run").exists()


def test_check_reports_rejects_more_than_one_active_run_per_day(tmp_path: Path):
    day = tmp_path / "reports" / "2026" / "2026-07-16"
    for name in ("run-a", "run-b"):
        run = day / name
        run.mkdir(parents=True)
        (run / "result.json").write_text("{}", encoding="utf-8")

    result = tdd.check_reports(tmp_path)

    assert result.ok is False
    assert "활성 보고서" in result.message


@pytest.mark.parametrize("bad_name", ["../escape", "has space", "한글", "A_UPPER"])
def test_report_dir_rejects_unsafe_run_name(tmp_path: Path, bad_name: str):
    with pytest.raises(ValueError):
        tdd.report_dir(tmp_path, bad_name, "2026-07-16")


def test_verify_stage_runs_every_command(tmp_path: Path):
    config = tdd.load_config(write_config(tmp_path))
    seen: list[list[str]] = []

    def runner(argv, cwd):
        seen.append(argv)
        return 0

    result = tdd.verify_stage(config, "sourcing", root=tmp_path, runner=runner)
    assert result.ok is True
    assert seen == [["python", "-c", "print('ok')"]]


def test_verify_stage_fails_when_no_commands(tmp_path: Path):
    config = tdd.load_config(write_config(tmp_path))
    result = tdd.verify_stage(config, "detail-page", root=tmp_path, runner=lambda *_: 0)
    assert result.ok is False
    assert "검증 명령" in result.message


def test_verify_stage_stops_on_failed_command(tmp_path: Path):
    config = tdd.load_config(write_config(tmp_path))
    result = tdd.verify_stage(config, "sourcing", root=tmp_path, runner=lambda *_: 7)
    assert result.ok is False
    assert result.exit_code == 7


def test_select_stages_implemented_only_excludes_partial(tmp_path: Path):
    config = tdd.load_config(write_config(tmp_path))
    config["stages"][0]["status"] = "implemented"
    config["stages"][1]["status"] = "partial"
    assert [stage["id"] for stage in tdd.select_stages(config, implemented_only=True)] == ["sourcing"]


def test_real_stage_test_paths_route_back_to_same_stage():
    config = tdd.load_config(tdd.DEFAULT_CONFIG)
    for stage in config["stages"]:
        for pattern in stage.get("test_paths") or []:
            sample = pattern.replace("**", "test_contract.py").replace("*", "contract")
            assert tdd.route_stage(config, sample) == stage["id"], (stage["id"], pattern, sample)


def test_external_skill_and_plugin_validators_force_utf8_on_windows():
    config = tdd.load_config(tdd.DEFAULT_CONFIG)
    commands = [
        command["argv"]
        for stage in config["stages"]
        for command in stage.get("commands") or []
        if "validation" in command.get("name", "") or command.get("name", "").endswith("-skill")
    ]
    assert commands
    assert all(argv[:3] == ["python", "-X", "utf8"] for argv in commands)


def test_issue_repeated_three_times_requires_promoted_rule(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ISSUE.md").write_text(
        "# ISSUE\n\n## SOURCING-OFFER-EVIDENCE-001\n\n- 반복 횟수: 3\n",
        encoding="utf-8",
    )
    (docs / "RULE.md").write_text("# RULE\n", encoding="utf-8")
    result = tdd.check_issue_rules(tmp_path)
    assert result.ok is False
    assert "SOURCING-OFFER-EVIDENCE-001" in result.message
    assert "RULE 승격" in result.message


def test_issue_repeated_three_times_passes_after_rule_promotion(tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "ISSUE.md").write_text(
        "# ISSUE\n\n## SOURCING-OFFER-EVIDENCE-001\n\n- 반복 횟수: 3\n",
        encoding="utf-8",
    )
    (docs / "RULE.md").write_text(
        "# RULE\n\n## SOURCING-OFFER-EVIDENCE-001\n\n진행 전 공급조건을 검증한다.\n",
        encoding="utf-8",
    )
    result = tdd.check_issue_rules(tmp_path)
    assert result.ok is True
