from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "coupang-detail-page-generator"
SCRIPTS = SKILL / "scripts"
ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z2S8AAAAASUVORK5CYII="
)


def run_script(name: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *(str(arg) for arg in args)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initialize(project: Path) -> None:
    result = run_script("initialize_project.py", "--project", project)
    assert result.returncode == 0, result.stderr


def write_ready_plans(project: Path) -> tuple[Path, Path]:
    product_path = project / "output" / "planning" / "product-plan.json"
    product_plan = {
        "schema_version": "1.0",
        "artifact_type": "product_plan",
        "project_id": "hybrid-fixture",
        "status": "ready_for_approval",
        "source_candidate_id": "C-001",
        "target_customer": "한여름 야외 활동 고객",
        "primary_problem": "목 주변 열감",
        "positioning": "실제 구조와 사용 장면으로 설명하는 실용형 상품",
        "offer": {
            "currency": "KRW",
            "recommended_price": 16800,
            "bundles": [{"id": "B-2", "quantity": 2, "status": "confirmed"}],
        },
        "claims": [
            {
                "id": "CLAIM-01",
                "text": "목에 둘러 사용하는 쿨링 스카프",
                "evidence_ids": ["FACT-01"],
                "status": "CONFIRMED_SOURCE",
            }
        ],
        "constraints": {"forbidden_claims": ["검증되지 않은 체온 저하 수치"]},
    }
    write_json(product_path, product_plan)

    content_path = project / "output" / "planning" / "content-plan.json"
    content_plan = {
        "schema_version": "1.0",
        "artifact_type": "content_plan",
        "project_id": "hybrid-fixture",
        "status": "ready_for_approval",
        "product_plan_ref": {
            "path": "output/planning/product-plan.json",
            "sha256": sha256(product_path),
        },
        "rendering": {
            "mode": "hybrid_html",
            "text_layer": "native_html",
            "visual_layer": "external_assets",
        },
        "modules": [
            {
                "id": "M01",
                "order": 1,
                "role": "hero",
                "headline": "더운 날, 목 주변을 가볍게",
                "body": "확인된 제품 구조와 사용 장면을 중심으로 소개합니다.",
                "evidence_ids": ["FACT-01"],
                "claim_ids": ["CLAIM-01"],
                "asset_ids": ["ASSET-01"],
                "editable_fields": ["headline", "body"],
                "qa_criteria": ["copy_accuracy", "product_identity", "claim_evidence"],
            }
        ],
    }
    write_json(content_path, content_plan)
    return product_path, content_path


def approve(project: Path, target: str) -> subprocess.CompletedProcess[str]:
    return run_script(
        "record_user_approval.py",
        "--project",
        project,
        "--target",
        target,
        "--actor-id",
        "fixture-user",
        "--confirm-user-approval",
    )


def write_asset_and_qa(project: Path, *, material_status: str) -> None:
    asset_path = project / "output" / "content-assets" / "hero.png"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(ONE_PIXEL_PNG)
    write_json(
        project / "output" / "content-assets" / "manifest.json",
        {
            "schema_version": "1.0",
            "assets": [
                {
                    "id": "ASSET-01",
                    "type": "image",
                    "path": "output/content-assets/hero.png",
                    "sha256": sha256(asset_path),
                    "alt": "목에 두르는 쿨링 스카프 제품 이미지",
                    "evidence_ids": ["FACT-01"],
                    "claim_ids": ["CLAIM-01"],
                    "lineage_ids": ["SOURCE-01"],
                }
            ],
        },
    )
    gate_value = "pass" if material_status == "pass" else "fix"
    write_json(
        project / "output" / "qa" / "material-qa.json",
        {
            "schema_version": "1.0",
            "materials": [
                {
                    "module_id": "M01",
                    "asset_ids": ["ASSET-01"],
                    "gates": {
                        "technical": gate_value,
                        "product_identity": gate_value,
                        "claim_evidence": gate_value,
                        "copy_accuracy": gate_value,
                        "visual_quality": gate_value,
                    },
                    "automated_status": gate_value,
                    "visual_review_status": gate_value,
                    "status": material_status,
                }
            ],
        },
    )


def prepare_approved_project(project: Path, *, material_status: str = "pass") -> None:
    initialize(project)
    write_ready_plans(project)
    result = approve(project, "product-plan")
    assert result.returncode == 0, result.stderr
    result = approve(project, "content-plan")
    assert result.returncode == 0, result.stderr
    write_asset_and_qa(project, material_status=material_status)


def test_initialize_project_separates_plans_and_user_approval_gates(tmp_path: Path) -> None:
    project = tmp_path / "project"
    initialize(project)

    manifest = (project / "output" / "project-manifest.yaml").read_text(encoding="utf-8")
    product_plan = json.loads((project / "output" / "planning" / "product-plan.json").read_text(encoding="utf-8"))
    content_plan = json.loads((project / "output" / "planning" / "content-plan.json").read_text(encoding="utf-8"))
    product_approval = json.loads(
        (project / "output" / "approvals" / "product-plan-approval.json").read_text(encoding="utf-8")
    )
    content_approval = json.loads(
        (project / "output" / "approvals" / "content-plan-approval.json").read_text(encoding="utf-8")
    )

    assert 'workflow_version: "5.3"' in manifest
    assert product_plan["artifact_type"] == "product_plan"
    assert content_plan["artifact_type"] == "content_plan"
    assert product_approval["decision"] == "pending"
    assert content_approval["decision"] == "pending"
    assert product_approval["actor_type"] == "user"
    assert content_approval["actor_type"] == "user"


def test_user_approval_binds_exact_plan_hash_and_enforces_order(tmp_path: Path) -> None:
    project = tmp_path / "project"
    initialize(project)
    product_path, content_path = write_ready_plans(project)

    content_first = approve(project, "content-plan")
    assert content_first.returncode != 0
    assert "product-plan" in content_first.stderr

    product_result = approve(project, "product-plan")
    assert product_result.returncode == 0, product_result.stderr
    product_approval = json.loads(
        (project / "output" / "approvals" / "product-plan-approval.json").read_text(encoding="utf-8")
    )
    assert product_approval["target_sha256"] == sha256(product_path)
    assert product_approval["decision"] == "approved"
    assert product_approval["actor_type"] == "user"

    content_result = approve(project, "content-plan")
    assert content_result.returncode == 0, content_result.stderr
    content_approval = json.loads(
        (project / "output" / "approvals" / "content-plan-approval.json").read_text(encoding="utf-8")
    )
    assert content_approval["target_sha256"] == sha256(content_path)

    content_plan = json.loads(content_path.read_text(encoding="utf-8"))
    content_plan["modules"][0]["headline"] = "승인 뒤 바뀐 문구"
    write_json(content_path, content_plan)
    validation = run_script("validate_planning_contracts.py", "--project", project, "--gate", "content")
    assert validation.returncode != 0
    assert "stale" in validation.stderr.lower()


def test_hybrid_builder_blocks_failed_material_qa_and_keeps_copy_editable(tmp_path: Path) -> None:
    project = tmp_path / "project"
    prepare_approved_project(project, material_status="fix")

    material_blocked = run_script("validate_material_qa.py", "--project", project, "--strict")
    assert material_blocked.returncode != 0
    blocked = run_script("build_hybrid_detail_page.py", "--project", project)
    assert blocked.returncode != 0
    assert "material" in blocked.stderr.lower()

    write_asset_and_qa(project, material_status="pass")
    material_passed = run_script("validate_material_qa.py", "--project", project, "--strict")
    assert material_passed.returncode == 0, material_passed.stderr
    built = run_script("build_hybrid_detail_page.py", "--project", project)
    assert built.returncode == 0, built.stderr

    html_path = project / "output" / "html" / "detail-page.html"
    css_path = project / "output" / "html" / "styles.css"
    package_path = project / "output" / "html" / "package-manifest.json"
    html = html_path.read_text(encoding="utf-8")

    assert "더운 날, 목 주변을 가볍게" in html
    assert 'data-module-id="M01"' in html
    assert 'data-claim-ids="CLAIM-01"' in html
    assert 'data-asset-id="ASSET-01" data-claim-ids="CLAIM-01"' in html
    assert "../content-assets/hero.png" in html
    assert "data:image" not in html
    assert css_path.is_file()
    assert package_path.is_file()


def test_integrated_qa_is_required_after_hybrid_assembly(tmp_path: Path) -> None:
    project = tmp_path / "project"
    prepare_approved_project(project)
    built = run_script("build_hybrid_detail_page.py", "--project", project)
    assert built.returncode == 0, built.stderr

    pending = run_script("validate_hybrid_package.py", "--project", project, "--strict")
    assert pending.returncode != 0
    assert "integration" in pending.stderr.lower()

    write_json(
        project / "output" / "qa" / "integration-qa.json",
        {
            "schema_version": "1.0",
            "package_manifest_sha256": sha256(project / "output" / "html" / "package-manifest.json"),
            "gates": {
                "planning_alignment": "pass",
                "sequence_flow": "pass",
                "visual_consistency": "pass",
                "responsive_layout": "pass",
                "accessibility": "pass",
                "claims_policy": "pass",
                "channel_constraints": "pass",
            },
            "automated_status": "pass",
            "visual_review_status": "pass",
            "status": "pass",
        },
    )
    passed = run_script("validate_hybrid_package.py", "--project", project, "--strict")
    assert passed.returncode == 0, passed.stderr
    legacy_entrypoint = run_script("validate_outputs.py", "--project", project, "--strict")
    assert legacy_entrypoint.returncode == 0, legacy_entrypoint.stderr


def test_build_page_plan_populates_separate_content_plan_for_user_approval(tmp_path: Path) -> None:
    project = tmp_path / "project"
    initialize(project)
    product_path, _ = write_ready_plans(project)
    result = approve(project, "product-plan")
    assert result.returncode == 0, result.stderr

    built = run_script("build_page_plan.py", "--project", project, "--force")
    assert built.returncode == 0, built.stderr

    content_path = project / "output" / "planning" / "content-plan.json"
    content_plan = json.loads(content_path.read_text(encoding="utf-8"))
    approval = json.loads(
        (project / "output" / "approvals" / "content-plan-approval.json").read_text(encoding="utf-8")
    )
    assert content_plan["artifact_type"] == "content_plan"
    assert content_plan["status"] == "ready_for_approval"
    assert content_plan["product_plan_ref"]["sha256"] == sha256(product_path)
    assert len(content_plan["modules"]) == 10
    assert all(module["editable_fields"] == ["headline", "body"] for module in content_plan["modules"])
    assert approval["decision"] == "pending"


def test_manifest_base_accepts_workflow_53_hybrid_contract() -> None:
    manifest = yaml.safe_load(
        (SKILL / "assets" / "project-template" / "project-manifest.yaml").read_text(encoding="utf-8")
    )
    sys.path.insert(0, str(SCRIPTS))
    try:
        from validate_project_manifest import validate_base
    finally:
        sys.path.remove(str(SCRIPTS))

    errors: list[str] = []
    validate_base(manifest, errors)
    assert errors == []
    assert manifest["project"]["canvas"] == {
        "mode": "responsive",
        "width": 800,
        "height": None,
        "min_width": 360,
        "max_width": 800,
    }


def test_skill_reports_numbered_workflow_and_concept_only_prototype_gate() -> None:
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    artifact_contract = (SKILL / "references" / "project-artifact-contract.md").read_text(encoding="utf-8")
    openai_yaml = yaml.safe_load((SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8"))

    required_contract = [
        "## 10단계 진행 상태",
        "1. 소싱·가격 승인",
        "4. 제품기획과 사용자 승인",
        "5. 콘텐츠기획과 사용자 승인",
        "6. UI와 장별 자산 전략",
        "7. 콘텐츠 소재 생성과 소재 QA",
        "9. 콘텐츠 생성: 이미지+HTML 조립",
        "10. 통합 QA와 최종 승격",
        "execution_stage",
        "asset_scope",
        "production_gate",
        "production_use_allowed: false",
        "output/prototypes/<prototype-id>/",
    ]

    for item in required_contract:
        assert item in skill_text

    assert "output/prototypes/<prototype-id>/" in artifact_contract
    assert "concept_only" in artifact_contract
    assert "production_use_allowed: false" in artifact_contract
    assert "실제 SKU 판매용 상태로 승격하지 않는다" in artifact_contract

    default_prompt = openai_yaml["interface"]["default_prompt"]
    assert "$coupang-detail-page-generator" in default_prompt
    assert "제품기획" in default_prompt
    assert "콘텐츠기획" in default_prompt
    assert "하이브리드 HTML" in default_prompt
