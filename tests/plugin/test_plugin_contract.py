from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "coupang-commerce-automation"


def test_manifest_name_matches_plugin_directory():
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    assert manifest["name"] == PLUGIN.name


def test_plugin_contains_both_current_skills():
    skills = PLUGIN / "skills"
    assert (skills / "coupang-product-sourcing" / "SKILL.md").is_file()
    assert (skills / "coupang-detail-page-generator" / "SKILL.md").is_file()


def test_plugin_packages_best_high_markup_sourcing_skill_from_root_source():
    name = "coupang-best-high-markup-sourcing"
    source = ROOT / name
    packaged = PLUGIN / "skills" / name

    required = (
        Path("SKILL.md"),
        Path("agents/openai.yaml"),
        Path("scripts/filter_high_markup_candidates.py"),
        Path("references/input-output-contract.md"),
    )
    for relative in required:
        source_file = source / relative
        packaged_file = packaged / relative
        assert source_file.is_file(), source_file
        assert packaged_file.is_file(), packaged_file
        assert packaged_file.read_bytes() == source_file.read_bytes(), relative

    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")
    assert name in readme


def test_plugin_readme_routes_back_to_repository_harness():
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")
    assert "AGENTS" in readme
    assert "TDD" in readme


def test_plugin_packages_demand_backed_market_price_policy_from_root_source():
    source = ROOT / "coupang-product-sourcing"
    packaged = PLUGIN / "skills" / "coupang-product-sourcing"
    required = (
        Path("SKILL.md"),
        Path("scripts/recommend_prices.py"),
        Path("scripts/price_nodriver_candidates.py"),
        Path("scripts/collect_coupang_nodriver.py"),
        Path("scripts/build_qualified_report.py"),
        Path("references/evaluation-policy.md"),
    )
    for relative in required:
        assert (packaged / relative).read_bytes() == (source / relative).read_bytes(), relative

    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")
    assert "판매 근거 없는 등록가" in readme
    assert "PRICE_REVIEW_BLOCKED" in readme


def test_plugin_readme_describes_hybrid_detail_page_boundary():
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")

    assert "제품기획·콘텐츠기획 사용자 승인" in readme
    assert "하이브리드 HTML" in readme
    assert "채널별 정적 렌더링" in readme


def test_plugin_detail_skill_includes_numbered_concept_only_contract():
    skill = PLUGIN / "skills" / "coupang-detail-page-generator"
    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8-sig")
    artifact_contract = (skill / "references" / "project-artifact-contract.md").read_text(encoding="utf-8-sig")
    openai_yaml = (skill / "agents" / "openai.yaml").read_text(encoding="utf-8-sig")

    assert "## 10단계 진행 상태" in skill_text
    assert "7. 콘텐츠 소재 생성과 소재 QA" in skill_text
    assert "asset_scope: concept_only" in skill_text
    assert "production_gate: blocked" in skill_text
    assert "production_use_allowed: false" in artifact_contract
    assert "제품기획·콘텐츠기획" in openai_yaml
    assert "하이브리드 HTML" in openai_yaml


def test_plugin_detail_skill_packages_html_typography_qa():
    skill = PLUGIN / "skills" / "coupang-detail-page-generator"
    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8-sig")

    assert "한글 줄바꿈·고아행·오버플로" in skill_text
    assert (skill / "references" / "html-typography-qa.md").is_file()
    assert (skill / "scripts" / "collect_html_typography_metrics.js").is_file()
    assert (skill / "scripts" / "collect_html_typography_metrics.mjs").is_file()
    assert (skill / "scripts" / "validate_html_typography.py").is_file()


def test_plugin_packages_visual_storyboard_qa_and_orchestration_skills():
    detail = PLUGIN / "skills" / "coupang-detail-page-generator"
    required_detail_files = [
        detail / "references" / "visual-storyboard-and-ac.md",
        detail / "scripts" / "validate_visual_storyboard.py",
        detail / "scripts" / "collect_visual_layout_metrics.js",
        detail / "scripts" / "collect_visual_layout_metrics.mjs",
        detail / "scripts" / "validate_visual_layout.py",
    ]
    for path in required_detail_files:
        assert path.is_file(), path

    expected_skills = {
        "coupang-commerce-orchestrator",
        "coupang-product-planning",
        "coupang-content-studio",
        "coupang-publish-qa",
    }
    for name in expected_skills:
        skill = PLUGIN / "skills" / name
        assert (skill / "SKILL.md").is_file(), name
        skill_text = (skill / "SKILL.md").read_text(encoding="utf-8-sig")
        assert f"name: {name}" in skill_text

    orchestrator = (PLUGIN / "skills" / "coupang-commerce-orchestrator" / "SKILL.md").read_text(
        encoding="utf-8-sig"
    )
    assert "한 번에 하나의 질문" in orchestrator
    assert "현재 단계" in orchestrator
    assert "acceptance criteria" in orchestrator.casefold()


def test_plugin_manifest_and_readme_expose_stage_orchestration_ux():
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")

    assert re.fullmatch(r"0\.2\.0\+codex\.\d{14}", manifest["version"])
    assert "orchestration" in manifest["interface"]["capabilities"]
    assert "현재 단계" in manifest["interface"]["defaultPrompt"]
    for name in (
        "coupang-commerce-orchestrator",
        "coupang-product-planning",
        "coupang-content-studio",
        "coupang-detail-page-generator",
        "coupang-publish-qa",
    ):
        assert name in readme
    assert "한 번에 하나의 질문" in readme
    assert "스토리보드" in readme


def test_new_plugin_contract_files_do_not_end_with_an_extra_blank_line():
    skill_names = (
        "coupang-best-high-markup-sourcing",
        "coupang-commerce-orchestrator",
        "coupang-content-studio",
        "coupang-product-planning",
        "coupang-publish-qa",
    )
    contract_files = []
    for name in skill_names:
        skill = PLUGIN / "skills" / name
        contract_files.extend(skill.rglob("*.md"))
        contract_files.extend(skill.rglob("*.yaml"))
    contract_files.append(
        PLUGIN
        / "skills"
        / "coupang-detail-page-generator"
        / "references"
        / "visual-storyboard-and-ac.md"
    )

    for path in contract_files:
        assert not path.read_text(encoding="utf-8-sig").endswith("\n\n"), path


def test_orchestrator_contract_defines_resume_approval_and_visual_rollback_rules():
    contract = (
        PLUGIN
        / "skills"
        / "coupang-commerce-orchestrator"
        / "references"
        / "stage-contract.md"
    ).read_text(encoding="utf-8-sig")

    assert "project_id" in contract
    assert "manifest의 `updated_at`" in contract
    assert "target_sha256" in contract
    assert "actor_type: user" in contract
    assert "integration_qa_failed" in contract
    assert "rollback_to" in contract
    assert "주 피사체 가시율 95%" in contract
    assert "핵심 영역 가시율 100%" in contract
