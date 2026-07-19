#!/usr/bin/env python3
"""Stage-aware TDD runner and repository layout validator."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "harness" / "stages.json"
REPORT_RE = re.compile(r"^reports/\d{4}/\d{4}-\d{2}-\d{2}/[^/]+(?:/.*)?$")
DEPRECATED_REPORT_RE = re.compile(r"^reports/deprecated/\d{4}/\d{4}-\d{2}-\d{2}/[^/]+(?:/.*)?$")
RUN_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    exit_code: int
    message: str


def normalize_path(value: str | Path) -> str:
    normalized = str(value).replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    stages = payload.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("harness/stages.json에 stages 배열이 필요합니다.")
    ids = [stage.get("id") for stage in stages]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("stage id는 비어 있지 않고 중복되지 않아야 합니다.")
    payload["stages"] = sorted(stages, key=lambda row: (row.get("order", 999), row["id"]))
    return payload


def stage_by_id(config: dict, stage_id: str) -> dict:
    for stage in config["stages"]:
        if stage["id"] == stage_id:
            return stage
    raise KeyError(f"알 수 없는 stage: {stage_id}")


def _matches(path: str, patterns: Sequence[str]) -> bool:
    normalized = normalize_path(path)
    return any(fnmatch.fnmatchcase(normalized, normalize_path(pattern)) for pattern in patterns)


def route_stage(config: dict, path: str | Path) -> str | None:
    normalized = normalize_path(path)
    for stage in config["stages"]:
        if _matches(normalized, stage.get("paths") or []):
            return stage["id"]
    return None


def is_test_path(config: dict, stage_id: str, path: str | Path) -> bool:
    stage = stage_by_id(config, stage_id)
    return _matches(normalize_path(path), stage.get("test_paths") or [])


def valid_report_path(path: str | Path) -> bool:
    normalized = normalize_path(path)
    if normalized == "reports/AGENTS.md":
        return True
    return bool(REPORT_RE.fullmatch(normalized) or DEPRECATED_REPORT_RE.fullmatch(normalized))


def report_dir(root: Path, run_name: str, run_date: str | None = None) -> Path:
    if not RUN_NAME_RE.fullmatch(run_name):
        raise ValueError("run name은 소문자 kebab-case만 허용합니다.")
    iso_date = run_date or date.today().isoformat()
    try:
        parsed = date.fromisoformat(iso_date)
    except ValueError as exc:
        raise ValueError("date는 YYYY-MM-DD 형식이어야 합니다.") from exc
    return root / "reports" / str(parsed.year) / iso_date / run_name


def prepare_report_dir(root: Path, run_name: str, run_date: str | None = None) -> Path:
    """Create the active run and archive every older run from the same day."""
    target = report_dir(root, run_name, run_date)
    if target.exists():
        raise FileExistsError(f"활성 보고서가 이미 존재합니다: {target}")
    active_day = target.parent
    archive_day = root / "reports" / "deprecated" / active_day.parent.name / active_day.name
    older_runs: list[Path] = []
    if active_day.exists():
        older_runs = [
            child
            for child in sorted(active_day.iterdir(), key=lambda path: path.name)
            if child != target and child.is_dir()
        ]
        conflicts = [archive_day / child.name for child in older_runs if (archive_day / child.name).exists()]
        if conflicts:
            raise FileExistsError(f"deprecated 보고서가 이미 존재합니다: {conflicts[0]}")
        for child in older_runs:
            archive_day.mkdir(parents=True, exist_ok=True)
            child.replace(archive_day / child.name)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _expand_argv(argv: Sequence[str], root: Path) -> list[str]:
    values = {"root": str(root), "home": str(Path.home())}
    return [str(value).format(**values) for value in argv]


def _default_runner(argv: list[str], cwd: Path) -> int:
    return subprocess.run(argv, cwd=cwd, check=False).returncode


def verify_stage(
    config: dict,
    stage_id: str,
    *,
    root: Path = ROOT,
    runner: Callable[[list[str], Path], int] = _default_runner,
) -> VerificationResult:
    stage = stage_by_id(config, stage_id)
    commands = stage.get("commands") or []
    if not commands:
        return VerificationResult(False, 2, f"{stage_id}: 검증 명령이 없습니다.")
    for item in commands:
        argv = _expand_argv(item.get("argv") or [], root)
        if not argv:
            return VerificationResult(False, 2, f"{stage_id}/{item.get('name')}: 빈 검증 명령")
        print(f"[TDD:{stage_id}] {item.get('name', 'check')}: {' '.join(argv)}", flush=True)
        code = runner(argv, root)
        if code != 0:
            return VerificationResult(False, code, f"{stage_id}/{item.get('name')}: 실패(exit {code})")
    return VerificationResult(True, 0, f"{stage_id}: 모든 필수 검증 통과")


def check_reports(root: Path = ROOT) -> VerificationResult:
    reports = root / "reports"
    if not reports.exists():
        return VerificationResult(True, 0, "reports 디렉터리 없음")
    invalid = [
        normalize_path(path.relative_to(root))
        for path in reports.rglob("*")
        if path.is_file() and not valid_report_path(path.relative_to(root))
    ]
    if invalid:
        return VerificationResult(False, 2, "날짜 경로 밖의 보고서: " + ", ".join(sorted(invalid)))
    multiple_active: list[str] = []
    for year_dir in reports.iterdir():
        if not year_dir.is_dir() or not re.fullmatch(r"\d{4}", year_dir.name):
            continue
        for day_dir in year_dir.iterdir():
            if not day_dir.is_dir() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day_dir.name):
                continue
            active_runs = [path for path in day_dir.iterdir() if path.is_dir()]
            if len(active_runs) > 1:
                multiple_active.append(normalize_path(day_dir.relative_to(root)))
    if multiple_active:
        return VerificationResult(False, 2, "날짜별 활성 보고서는 1개만 허용: " + ", ".join(sorted(multiple_active)))
    return VerificationResult(True, 0, "활성 1개 + reports/deprecated/YYYY/YYYY-MM-DD 구조 통과")


def check_routing(root: Path = ROOT) -> VerificationResult:
    required = [
        "AGENTS.md",
        "docs/ISSUE.md",
        "docs/RULE.md",
        "docs/AGENTS.md",
        "coupang-product-sourcing/AGENTS.md",
        "coupang-detail-page-generator/AGENTS.md",
        "detail-page/AGENTS.md",
        "commerce-project/AGENTS.md",
        "plugins/coupang-commerce-automation/AGENTS.md",
        "reports/AGENTS.md",
        "tests/AGENTS.md",
        "scripts/AGENTS.md",
        "harness/AGENTS.md",
        ".codex/AGENTS.md",
    ]
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        return VerificationResult(False, 2, "AGENTS 라우팅 누락: " + ", ".join(missing))
    return VerificationResult(True, 0, "AGENTS 라우팅 파일 통과")


def check_issue_rules(root: Path = ROOT) -> VerificationResult:
    """Require every issue repeated three times to have a matching RULE heading."""
    issue_path = root / "docs" / "ISSUE.md"
    rule_path = root / "docs" / "RULE.md"
    missing = [str(path.relative_to(root)) for path in (issue_path, rule_path) if not path.is_file()]
    if missing:
        return VerificationResult(False, 2, "이슈·규칙 문서 누락: " + ", ".join(missing))

    issue_text = issue_path.read_text(encoding="utf-8-sig")
    rule_text = rule_path.read_text(encoding="utf-8-sig")
    heading_re = re.compile(r"^##\s+([A-Z0-9][A-Z0-9._-]+)\s*$", re.MULTILINE)
    issue_matches = list(heading_re.finditer(issue_text))
    rule_ids = set(heading_re.findall(rule_text))
    malformed: list[str] = []
    promotion_required: list[str] = []
    for index, match in enumerate(issue_matches):
        issue_id = match.group(1)
        end = issue_matches[index + 1].start() if index + 1 < len(issue_matches) else len(issue_text)
        section = issue_text[match.end():end]
        count_match = re.search(r"^-\s*반복 횟수\s*:\s*(\d+)\s*$", section, re.MULTILINE)
        if not count_match:
            malformed.append(issue_id)
            continue
        if int(count_match.group(1)) >= 3 and issue_id not in rule_ids:
            promotion_required.append(issue_id)
    if malformed:
        return VerificationResult(False, 2, "반복 횟수 형식 누락: " + ", ".join(malformed))
    if promotion_required:
        return VerificationResult(False, 2, "RULE 승격 필요: " + ", ".join(promotion_required))
    return VerificationResult(True, 0, "ISSUE 3회 반복 → RULE 승격 규칙 통과")


def _git_changed_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def verify_changed(config: dict, files: Sequence[str], root: Path = ROOT) -> VerificationResult:
    stage_ids = {
        stage_id
        for path in files
        if (stage_id := route_stage(config, path)) is not None
    }
    for stage in config["stages"]:
        if stage["id"] in stage_ids:
            result = verify_stage(config, stage["id"], root=root)
            if not result.ok:
                return result
    reports_result = check_reports(root)
    if not reports_result.ok:
        return reports_result
    issue_result = check_issue_rules(root)
    if not issue_result.ok:
        return issue_result
    return VerificationResult(True, 0, "변경 경로의 단계 검증 통과")


def select_stages(config: dict, *, implemented_only: bool = False) -> list[dict]:
    if not implemented_only:
        return list(config["stages"])
    return [stage for stage in config["stages"] if stage.get("status") == "implemented"]


def _print_result(result: VerificationResult) -> int:
    stream = sys.stdout if result.ok else sys.stderr
    print(result.message, file=stream)
    return result.exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")
    route = sub.add_parser("route")
    route.add_argument("path")
    verify = sub.add_parser("verify")
    verify.add_argument("stage")
    verify_all = sub.add_parser("verify-all")
    verify_all.add_argument("--implemented-only", action="store_true")
    changed = sub.add_parser("changed")
    changed.add_argument("--files", nargs="*")
    report = sub.add_parser("report-path")
    report.add_argument("run_name")
    report.add_argument("--date")
    report.add_argument("--create", action="store_true")
    sub.add_parser("check-reports")
    sub.add_parser("check-routing")
    sub.add_parser("check-issues")

    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.command == "list":
        for stage in config["stages"]:
            print(f"{stage['order']}: {stage['id']} ({stage.get('status', 'planned')})")
        return 0
    if args.command == "route":
        print(route_stage(config, args.path) or "unrouted")
        return 0
    if args.command == "verify":
        return _print_result(verify_stage(config, args.stage))
    if args.command == "verify-all":
        for stage in select_stages(config, implemented_only=args.implemented_only):
            result = verify_stage(config, stage["id"])
            if not result.ok:
                return _print_result(result)
        reports_result = check_reports()
        if not reports_result.ok:
            return _print_result(reports_result)
        return _print_result(check_issue_rules())
    if args.command == "changed":
        files = args.files if args.files is not None else _git_changed_files(ROOT)
        return _print_result(verify_changed(config, files, ROOT))
    if args.command == "report-path":
        path = prepare_report_dir(ROOT, args.run_name, args.date) if args.create else report_dir(ROOT, args.run_name, args.date)
        print(path)
        return 0
    if args.command == "check-reports":
        return _print_result(check_reports())
    if args.command == "check-routing":
        return _print_result(check_routing())
    if args.command == "check-issues":
        return _print_result(check_issue_rules())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
