from __future__ import annotations

import json
import importlib.util
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "coupang-commerce-automation"
WORKFLOW_UI = ROOT / "coupang-workflow-ui"


def test_manifest_name_matches_plugin_directory():
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    assert manifest["name"] == PLUGIN.name


def test_repo_marketplace_exposes_plugin_for_cross_computer_installation():
    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8-sig"))

    assert marketplace["name"] == "sm-coupang-plugin"
    entry = next(plugin for plugin in marketplace["plugins"] if plugin["name"] == PLUGIN.name)
    assert entry["source"] == {
        "source": "local",
        "path": "./plugins/coupang-commerce-automation",
    }
    assert entry["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert entry["category"] == "Productivity"

    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")
    assert "codex plugin marketplace add csm-kr/sm-coupang-plugin" in readme
    assert "coupang-commerce-automation@sm-coupang-plugin" in readme


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
        Path("scripts/run_headless_browser_harness.py"),
        Path("scripts/build_qualified_report.py"),
        Path("references/evaluation-policy.md"),
        Path("references/research-protocol.md"),
    )
    for relative in required:
        assert (packaged / relative).read_bytes() == (source / relative).read_bytes(), relative

    readme = (PLUGIN / "README.md").read_text(encoding="utf-8-sig")
    assert "판매 근거 없는 등록가" in readme
    assert "PRICE_REVIEW_BLOCKED" in readme
    assert "headless Browser Harness" in readme
    assert "headless `nodriver`" in readme


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


def test_workflow_ui_skill_packages_a_built_react_dashboard():
    packaged = PLUGIN / "skills" / "coupang-workflow-ui"
    required = (
        Path("SKILL.md"),
        Path("agents/openai.yaml"),
        Path("scripts/project_store.py"),
        Path("scripts/codex_runner.py"),
        Path("scripts/serve_workflow_ui.py"),
        Path("assets/react-app/package.json"),
        Path("assets/react-app/src/App.jsx"),
        Path("assets/react-app/src/workflow.js"),
        Path("assets/react-app/src/workflow.test.js"),
        Path("assets/dashboard/index.html"),
    )

    for relative in required:
        source_file = WORKFLOW_UI / relative
        packaged_file = packaged / relative
        assert source_file.is_file(), source_file
        assert packaged_file.is_file(), packaged_file
        assert packaged_file.read_bytes() == source_file.read_bytes(), relative

    assert (WORKFLOW_UI / "scripts" / "project_store.py").read_bytes() == (
        ROOT / "commerce-project" / "scripts" / "project_store.py"
    ).read_bytes()

    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))
    assert "workflow-dashboard" in manifest["interface"]["capabilities"]
    assert any((WORKFLOW_UI / "assets" / "dashboard" / "assets").glob("*.js"))
    assert any((WORKFLOW_UI / "assets" / "dashboard" / "assets").glob("*.css"))
    assert not (packaged / "assets" / "react-app" / "node_modules").exists()


def test_workflow_ui_exposes_codex_run_controls_and_an_embedded_console():
    app = (WORKFLOW_UI / "assets" / "react-app" / "src" / "App.jsx").read_text(
        encoding="utf-8-sig"
    )
    server = (WORKFLOW_UI / "scripts" / "serve_workflow_ui.py").read_text(
        encoding="utf-8-sig"
    )

    assert 'method: "POST"' in app
    assert 'api("/api/runs"' in app
    assert "Codex 작업 시작" in app
    assert "Codex 실행 콘솔" in app
    assert 'method: "DELETE"' in app
    assert 'path == "/api/runs"' in server
    assert 'prefix = "/api/runs/"' in server


def test_workflow_ui_sourcing_shows_live_progress_then_only_real_results():
    app = (
        ROOT
        / "coupang-workflow-ui"
        / "assets"
        / "react-app"
        / "src"
        / "App.jsx"
    ).read_text(encoding="utf-8-sig")

    assert "function SourcingResultPanel" in app
    assert "진행중입니다." in app
    assert "실제 결과" in app
    assert "실패 이유" in app
    assert "도매꾹 확인 샘플" in app
    assert 'selectedStage.id === "sourcing"' in app


def test_workflow_ui_new_projects_use_the_requested_sourcing_defaults():
    workflow = (
        ROOT
        / "coupang-workflow-ui"
        / "assets"
        / "react-app"
        / "src"
        / "workflow.js"
    ).read_text(encoding="utf-8-sig")
    store = (ROOT / "commerce-project" / "scripts" / "project_store.py").read_text(
        encoding="utf-8-sig"
    )

    for expected in ('category: "전체"', 'maxUnitSupplyPrice: "5000"', 'minMarkupMultiple: "3"'):
        assert expected in workflow
    for expected in ('"category": "전체"', '"maxUnitSupplyPrice": "5000"', '"minMarkupMultiple": "3"'):
        assert expected in store


def test_workflow_ui_uses_a_coupang_mood_without_copying_brand_assets():
    app = (WORKFLOW_UI / "assets" / "react-app" / "src" / "App.jsx").read_text(
        encoding="utf-8-sig"
    )
    styles = (WORKFLOW_UI / "assets" / "react-app" / "src" / "styles.css").read_text(
        encoding="utf-8-sig"
    )
    workflow = (WORKFLOW_UI / "assets" / "react-app" / "src" / "workflow.js").read_text(
        encoding="utf-8-sig"
    )

    assert "--commerce-blue: #2563eb" in styles
    assert "--commerce-red: #e5484d" in styles
    assert "--surface-canvas: #f5f7fa" in styles
    assert ".flow-summary {" in styles
    assert ".workflow-overview {" in styles
    assert 'className={`flow-summary ${copy.action}`}' in app
    assert "<FlowSummary" in app
    assert 'aria-label="전체 워크플로 진행률"' in app
    assert 'aria-current={selectedId === stage.id ? "step" : undefined}' in app
    assert 'role="progressbar"' in app
    assert "aria-valuenow={progress.percentage}" in app
    assert "stageActionCopy" in workflow
    assert "쿠팡 로고" not in app
    assert "var(--commerce-red) 72%" not in styles
    assert ".brand-mark::after" not in styles

    compact_rules = styles.rsplit("@media (max-width: 850px)", 1)[1].split("@media", 1)[0]
    assert re.search(r"\.project-rail\s*\{[^}]*position:\s*static", compact_rules)
    assert re.search(r"\.project-rail\s*\{[^}]*width:\s*auto", compact_rules)
    assert re.search(r"\.workspace\s*\{[^}]*margin-left:\s*0", compact_rules)


def test_workflow_ui_refresh_resets_fixed_desktop_layout_on_mobile():
    styles = (WORKFLOW_UI / "assets" / "react-app" / "src" / "styles.css").read_text(
        encoding="utf-8-sig"
    )
    refresh = styles.split("/* Commerce Flow visual system", 1)[1]
    mobile = refresh.split("@media (max-width: 850px)", 1)[1]

    assert re.search(r"\.project-rail\s*\{[^}]*position:\s*static", mobile, re.S)
    assert re.search(r"\.project-rail\s*\{[^}]*width:\s*auto", mobile, re.S)
    assert re.search(r"\.workspace\s*\{[^}]*margin-left:\s*0", mobile, re.S)


def test_workflow_ui_logic_enforces_stage_gates_and_builds_codex_prompt():
    completed = subprocess.run(
        ["node", "--test", "src/workflow.test.js"],
        cwd=WORKFLOW_UI / "assets" / "react-app",
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_workflow_ui_uses_the_full_best_category_as_the_default():
    completed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { STAGES, buildCodexPrompt, createInitialState, deriveProgress, "
                "setStageCompleted, updateStageInput } from './src/workflow.js'; "
                "let state = createInitialState('2026-07-19T00:00:00Z'); "
                "for (const [field, value] of Object.entries({ "
                "maxUnitSupplyPrice: '5000', minMarkupMultiple: '3' })) "
                "state = updateStageInput(state, 'sourcing', field, value); "
                "const sourcing = STAGES.find((stage) => stage.id === 'sourcing'); "
                "const category = sourcing.inputs.find((input) => input.id === 'category'); "
                "state = setStageCompleted(state, 'sourcing', true); "
                "console.log(JSON.stringify({ required: category.required, "
                "type: category.type, options: (category.options ?? []).map(([value]) => value), "
                "hasSourcingMode: sourcing.inputs.some((input) => input.id === 'sourcingMode'), "
                "projectSourcingMode: state.project.sourcingMode, "
                "currentStageId: deriveProgress(state).currentStageId, "
                "prompt: buildCodexPrompt(state, 'sourcing') }));"
            ),
        ],
        cwd=WORKFLOW_UI / "assets" / "react-app",
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["required"] is False
    assert payload["type"] == "select"
    assert payload["options"] == [
        "전체",
        "패션잡화/화장품",
        "의류/언더웨어",
        "출산/유아동/완구",
        "가구/생활/취미",
        "스포츠/건강/식품",
        "가전/휴대폰/산업",
    ]
    assert payload["hasSourcingMode"] is False
    assert payload["projectSourcingMode"] == "high-markup"
    assert payload["currentStageId"] == "handoff"
    assert "$coupang-commerce-automation:coupang-best-high-markup-sourcing" in payload["prompt"]
    assert "도매꾹 Best 카테고리: 전체" in payload["prompt"]
    assert "도매꾹 개당 공급가 상한: 5000" in payload["prompt"]
    assert "최소 가격 배수: 3" in payload["prompt"]
    assert "미입력 필수 항목: 없음" in payload["prompt"]
    assert "설명만 하지 말고 실제 조사를 실행" in payload["prompt"]
    assert "HTML·JSON 보고서" in payload["prompt"]
    assert "설정한 최소 가격 배수 이상인 pair가 하나라도" in payload["prompt"]
    assert "더 싼 등록은 탈락 근거로 사용하지 않는다" in payload["prompt"]
    assert "리뷰 또는 100명 이상 만족" in payload["prompt"]
    assert "links.reportRuns" in payload["prompt"]

    app = (WORKFLOW_UI / "assets" / "react-app" / "src" / "App.jsx").read_text(encoding="utf-8-sig")
    assert '<option value="standard">일반 소싱</option>' not in app
    assert "도매꾹 Best 고배수 pair 탐색" in app


def test_workflow_ui_handoff_is_an_inline_click_confirm_and_advance_flow():
    app = (WORKFLOW_UI / "assets" / "react-app" / "src" / "App.jsx").read_text(encoding="utf-8-sig")

    assert "CandidateDecisionPanel" in app
    assert "도매꾹 ↔ 쿠팡 pair를 비교하세요" in app
    assert "낮은 가격의 다른 등록은 이 pair를 탈락시키지 않습니다" in app
    assert "상품·가격 확정하고 상품기획으로" in app
    assert "selectSourcingCandidate" in app
    assert "confirmSourcingSelection" in app
    assert "WorkspaceViewer" in app
    assert "onDrop" in app
    assert "HTML·이미지 미리보기와 JSON·텍스트 확인" in app


def test_workflow_ui_product_planning_uses_user_entry_confirmation_and_asset_drop_preview():
    workflow = (WORKFLOW_UI / "assets" / "react-app" / "src" / "workflow.js").read_text(
        encoding="utf-8-sig"
    )
    app = (WORKFLOW_UI / "assets" / "react-app" / "src" / "App.jsx").read_text(
        encoding="utf-8-sig"
    )
    styles = (WORKFLOW_UI / "assets" / "react-app" / "src" / "styles.css").read_text(
        encoding="utf-8-sig"
    )

    assert "setPriorStageConfirmation" in workflow
    assert 'skill: "coupang-product-planning"' in workflow
    assert "sizeMeasurements" in workflow
    assert "packageComposition" in workflow
    assert "careInstructions" in workflow
    assert "경쟁사 별점 1~3점 저평점 리뷰를 Codex가 직접 조사" in workflow
    assert 'field("identityAssets"' not in workflow
    assert 'field("lowRatingReviews"' not in workflow
    assert 'field("sourceAssets"' not in workflow
    assert 'field("motionAssets"' not in workflow
    assert "앞 단계 완료 확인" in app
    assert 'variant="stage-assets"' in app
    assert "asset-preview-grid" in app
    assert "경로를 입력하지 마세요" in app
    assert ".asset-preview-grid" in styles

    planning_skill = (ROOT / "coupang-product-planning" / "SKILL.md").read_text(
        encoding="utf-8-sig"
    )
    assert "Browser Harness" in planning_skill
    assert "사용자에게 리뷰 URL이나 조사 파일 경로를 입력받지 않는다" in planning_skill
    assert "folderMap.sourceAssets" in planning_skill


def test_product_planning_starts_with_supplier_url_search_then_user_offer_decision():
    source_skill = (ROOT / "coupang-product-planning" / "SKILL.md").read_text(
        encoding="utf-8-sig"
    )
    source_contract = (
        ROOT
        / "coupang-product-planning"
        / "references"
        / "product-planning-contract.md"
    ).read_text(encoding="utf-8-sig")
    packaged_skill = (
        PLUGIN
        / "skills"
        / "coupang-product-planning"
        / "SKILL.md"
    ).read_text(encoding="utf-8-sig")
    packaged_contract = (
        PLUGIN
        / "skills"
        / "coupang-product-planning"
        / "references"
        / "product-planning-contract.md"
    ).read_text(encoding="utf-8-sig")

    for text in (source_skill, source_contract):
        assert "공급처 상세 URL 하나만으로 조사를 시작" in text
        assert "상세 본문·옵션·상품정보·공개 후기·문의" in text
        assert "색상·사이즈·구성·소재·관리법" in text
        assert "조사 결과를 사용자에게 먼저 보고" in text
        assert "판매가·묶음·판매 옵션" in text
        assert "오퍼 결정 게이트" in text
        assert "사용자와 정하는 오퍼 결정 게이트" in text

    assert source_skill == packaged_skill
    assert source_contract == packaged_contract


def test_workflow_ui_generates_a_safe_default_project_id_for_beginners():
    completed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { createDefaultProjectId } from './src/workflow.js'; "
                "console.log(createDefaultProjectId(new Date('2026-07-17T02:30:45.123Z')));"
            ),
        ],
        cwd=WORKFLOW_UI / "assets" / "react-app",
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "project-20260717-023045-123"


def test_workflow_ui_server_can_preflight_packaged_assets_without_opening_browser():
    completed = subprocess.run(
        [
            sys.executable,
            str(WORKFLOW_UI / "scripts" / "serve_workflow_ui.py"),
            "--check",
            "--no-open",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "dashboard ready" in completed.stdout.casefold()


def test_workflow_ui_api_creates_lists_and_updates_real_project_folders(tmp_path: Path):
    server_path = WORKFLOW_UI / "scripts" / "serve_workflow_ui.py"
    spec = importlib.util.spec_from_file_location("serve_workflow_ui", server_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    server = module.create_server(0, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    def request(path: str, method: str = "GET", payload: dict | None = None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            origin + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        created = request(
            "/api/projects",
            "POST",
            {
                "projectId": "summer-mask-001",
                "name": "여름 스포츠 마스크",
                "channel": "coupang",
                "sourcingMode": "high-markup",
            },
        )
        assert created["project"]["id"] == "summer-mask-001"
        assert request("/api/projects")["projects"][0]["currentStage"] == "sourcing"

        created["workflow"]["blockedReason"] = "실제 SKU 사진 필요"
        updated = request("/api/projects/summer-mask-001", "PUT", created)
        assert updated["workflow"]["blockedReason"] == "실제 SKU 사진 필요"
        assert (
            tmp_path
            / "commerce-project"
            / "projects"
            / "summer-mask-001"
            / "project.json"
        ).is_file()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_workflow_ui_serves_only_files_inside_the_workspace_reports_root(tmp_path: Path):
    server_path = WORKFLOW_UI / "scripts" / "serve_workflow_ui.py"
    spec = importlib.util.spec_from_file_location("serve_workflow_ui_reports", server_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    report = tmp_path / "reports" / "2026" / "2026-07-19" / "sample" / "report.html"
    report.parent.mkdir(parents=True)
    report.write_text("<html><body>신규 소싱 보고서</body></html>", encoding="utf-8")
    (tmp_path / "STATUS.md").write_text("외부 파일", encoding="utf-8")

    server = module.create_server(0, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    try:
        with urllib.request.urlopen(
            origin + "/reports/2026/2026-07-19/sample/report.html",
            timeout=3,
        ) as response:
            assert response.status == 200
            assert "신규 소싱 보고서" in response.read().decode("utf-8")

        try:
            urllib.request.urlopen(origin + "/reports/%2e%2e/STATUS.md", timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError("reports 루트 밖 파일이 노출됐습니다.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_workflow_ui_project_workspace_lists_previews_and_accepts_image_drop_uploads(tmp_path: Path):
    server_path = WORKFLOW_UI / "scripts" / "serve_workflow_ui.py"
    spec = importlib.util.spec_from_file_location("serve_workflow_ui_workspace", server_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    store = module.ProjectStore(tmp_path)
    project = store.create_project("summer-mask-001", "여름 스포츠 마스크", "coupang", "high-markup")
    project_root = tmp_path / "commerce-project" / "projects" / "summer-mask-001"
    preview = project_root / "50-detail-page" / "html" / "detail-page.html"
    preview.write_text("<html><body><h1>상세페이지 미리보기</h1></body></html>", encoding="utf-8")

    report = tmp_path / "reports" / "2026" / "2026-07-19" / "sample" / "report.html"
    report.parent.mkdir(parents=True)
    report.write_text("<html><body>소싱 보고서</body></html>", encoding="utf-8")
    store.register_report(project["project"]["id"], report)

    server = module.create_server(0, tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    try:
        with urllib.request.urlopen(origin + "/api/projects/summer-mask-001/workspace", timeout=3) as response:
            workspace = json.loads(response.read().decode("utf-8"))
        assert workspace["uploadTarget"] == "40-assets/source"
        assert any(
            item["path"] == "50-detail-page/html/detail-page.html"
            and item["kind"] == "html"
            and item["source"] == "project"
            for item in workspace["files"]
        )
        assert any(item["source"] == "report" and item["kind"] == "html" for item in workspace["files"])

        with urllib.request.urlopen(
            origin + "/project-files/summer-mask-001/50-detail-page/html/detail-page.html",
            timeout=3,
        ) as response:
            assert "상세페이지 미리보기" in response.read().decode("utf-8")
            assert "script-src 'none'" in response.headers["Content-Security-Policy"]

        png = b"\x89PNG\r\n\x1a\n" + b"candidate-image"
        upload = urllib.request.Request(
            origin + "/api/projects/summer-mask-001/assets?filename=front-view.png",
            data=png,
            method="POST",
            headers={"Content-Type": "image/png"},
        )
        with urllib.request.urlopen(upload, timeout=3) as response:
            uploaded = json.loads(response.read().decode("utf-8"))
        assert uploaded["path"] == "40-assets/source/front-view.png"
        assert (project_root / "40-assets" / "source" / "front-view.png").read_bytes() == png

        with urllib.request.urlopen(origin + uploaded["href"], timeout=3) as response:
            assert response.read() == png

        for filename, expected_status in (("front-view.png", 409), ("..%2Fevil.png", 400)):
            duplicate = urllib.request.Request(
                origin + f"/api/projects/summer-mask-001/assets?filename={filename}",
                data=png,
                method="POST",
                headers={"Content-Type": "image/png"},
            )
            try:
                urllib.request.urlopen(duplicate, timeout=3)
            except urllib.error.HTTPError as error:
                assert error.code == expected_status
            else:
                raise AssertionError(f"안전하지 않은 업로드가 허용됐습니다: {filename}")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_workflow_ui_api_starts_streams_and_stops_the_current_codex_stage(tmp_path: Path):
    server_path = WORKFLOW_UI / "scripts" / "serve_workflow_ui.py"
    spec = importlib.util.spec_from_file_location("serve_workflow_ui_runs", server_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class FakeRunManager:
        def __init__(self):
            self.started = []
            self.stopped = []
            self.run = {
                "runId": "run-001",
                "projectId": "summer-mask-001",
                "stageId": "sourcing",
                "status": "running",
                "events": [],
            }

        def runtime_status(self):
            return {"codexAvailable": True, "sandbox": "workspace-write"}

        def start_run(self, project_id, stage_id, prompt):
            self.started.append((project_id, stage_id, prompt))
            return self.run

        def list_runs(self, project_id=None):
            return [self.run] if project_id in {None, self.run["projectId"]} else []

        def get_run(self, run_id):
            if run_id != self.run["runId"]:
                raise FileNotFoundError(run_id)
            return self.run

        def stop_run(self, run_id):
            self.stopped.append(run_id)
            self.run = {**self.run, "status": "stopped"}
            return self.run

        def stop_all(self):
            return None

    runs = FakeRunManager()
    server = module.create_server(0, tmp_path, run_manager=runs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    def request(path: str, method: str = "GET", payload: dict | None = None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            origin + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        request(
            "/api/projects",
            "POST",
            {
                "projectId": "summer-mask-001",
                "name": "여름 스포츠 마스크",
                "channel": "coupang",
                "sourcingMode": "high-markup",
            },
        )
        started = request(
            "/api/runs",
            "POST",
            {
                "projectId": "summer-mask-001",
                "stageId": "sourcing",
                "prompt": "소싱을 시작해줘.",
            },
        )
        assert started["runId"] == "run-001"
        assert runs.started == [("summer-mask-001", "sourcing", "소싱을 시작해줘.")]
        assert request("/api/runs?projectId=summer-mask-001")["runs"][0]["status"] == "running"
        assert request("/api/runs/run-001")["projectId"] == "summer-mask-001"
        assert request("/api/runs/run-001", "DELETE")["status"] == "stopped"

        try:
            request(
                "/api/runs",
                "POST",
                {
                    "projectId": "summer-mask-001",
                    "stageId": "detail-page",
                    "prompt": "잠긴 단계를 실행해줘.",
                },
            )
        except urllib.error.HTTPError as error:
            assert error.code == 409
        else:
            raise AssertionError("잠긴 미래 단계의 Codex 실행이 허용됐습니다.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
