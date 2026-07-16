from __future__ import annotations

import json
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


def test_plugin_readme_routes_back_to_repository_harness():
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")
    assert "AGENTS" in readme
    assert "TDD" in readme


def test_plugin_readme_describes_hybrid_detail_page_boundary():
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")

    assert "상품·콘텐츠기획 사용자 승인" in readme
    assert "하이브리드 HTML" in readme
    assert "채널별 정적 렌더링" in readme
