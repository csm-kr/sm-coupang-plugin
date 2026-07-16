#!/usr/bin/env python3
"""Create a concise ten-page plan before the ImageGen batch."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from hybrid_contract import (
    CONTENT_APPROVAL_PATH,
    CONTENT_PLAN_PATH,
    PRODUCT_PLAN_PATH,
    load_json,
    sha256,
    validate_planning,
)

try:
    import yaml
except ImportError:  # Project planning still works without manifest synchronization.
    yaml = None

LOGGER = logging.getLogger("build_page_plan")

FLOW = [
    ("01", "hero", "hook", "질문·상황·핵심 상품을 결합한 첫 화면 훅", "{product}, 핵심부터 보여드릴게요", "제품 형태와 핵심 구성을 첫 화면에서 확인하세요", "PRODUCT", "hero_full", "center", "{product}", "hero_product"),
    ("02", "product_overview", "solution_overview", "제품 전체와 가장 강한 해결 구조", "구성부터 한눈에", "전체 제품과 제공된 구성품을 빠르게 확인하세요", "COMPONENTS", "studio_flatlay", "left", "한눈에", "complete_product"),
    ("03", "problem_context", "problem_or_criterion", "고객 고민 또는 선택 기준 비교", "사용 장면에서 먼저 확인하세요", "제품이 실제 장면에 놓였을 때의 형태와 비율을 비교합니다", "CHECK", "two_card_context", "center", "먼저 확인", "context_comparison"),
    ("04", "construction", "proof_1", "전체 실루엣·길이·결합 구조 증명", "전체 구조가 한눈에", "처음부터 끝까지 이어지는 형태를 크게 보여드립니다", "POINT 01", "full_plus_inset", "left", "전체 구조", "construction"),
    ("05", "key_detail", "proof_2", "핵심 개구부·커프·조절부 증명", "눈여겨볼 핵심 디테일", "확인 가능한 핵심 구조와 마감 비율을 확대합니다", "POINT 02", "macro_focus", "center", "핵심 디테일", "key_detail"),
    ("06", "material_detail", "proof_3", "표면·봉제·라벨·구성 증명", "가까이에서 보는 표면과 마감", "표면의 결, 봉제와 라벨 위치를 각각 확인하세요", "POINT 03", "macro_grid", "left", "표면과 마감", "material_finish"),
    ("07", "daily_use", "use_or_demonstration", "사용 순서 또는 실제 사용 맥락", "사용 전, 순서부터 확인하세요", "제공된 정보 안에서 사용 흐름을 2~3단계로 정리합니다", "HOW TO", "lifestyle_full", "left", "순서부터", "use_sequence"),
    ("08", "lifestyle_mosaic", "friction_reducer", "보관·관리·휴대·옵션 또는 장면 모자이크", "사용 전후 체크 포인트", "검증된 관리 정보 또는 서로 다른 사용 장면을 정리합니다", "CHECK POINT", "four_panel_mosaic", "center", "체크 포인트", "friction_reducer"),
    ("09", "product_information", "purchase_information", "검증된 구성·색상·사이즈·고지 정보", "구매 전, 이것만은 꼭 확인하세요", "검증된 상품 정보만 표와 카드로 정리합니다", "INFO", "spec_cards", "left", "꼭 확인", "specification"),
    ("10", "closing", "recap", "큰 제품 또는 합성 모델과 핵심 3가지 요약", "{product}, 핵심만 다시", "형태·구성·핵심 디테일을 간결하게 회수합니다", "SUMMARY", "closing_split", "center", "{product}", "three_point_recap"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a ten-page generation and copy plan")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def product_name(project: Path) -> str:
    path = project / "output" / "product-facts.json"
    if not path.is_file():
        return "상품"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        value = data.get("product_name", {})
        allowed = {"CONFIRMED_USER", "CONFIRMED_SOURCE", "OBSERVED_IMAGE"}
        status = str(value.get("status", "")) if isinstance(value, dict) else ""
        if isinstance(value, dict) and (status in allowed or status.startswith("verified_")) and value.get("value"):
            return str(value["value"])
    except Exception:
        pass
    return "상품"


def brand_context(project: Path) -> tuple[str, str]:
    path = project / "output" / "brand" / "brand-system.json"
    if not path.is_file():
        return "미설정", "브랜드 가이드 확정 필요"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        status = str(data.get("status", "미설정"))
        promise = str(data.get("promise", "")).strip() or "브랜드 약속 확정 필요"
        return status, promise
    except Exception:
        return "읽기 실패", "브랜드 시스템 JSON 수정 필요"


def reference_routes(project: Path) -> dict[str, dict]:
    path = project / "output" / "reference-routing.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        pages = data.get("pages", {})
        return pages if isinstance(pages, dict) else {}
    except Exception:
        return {}


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    project = args.project.expanduser().resolve()
    output = project / "output"
    manifest_path = output / "project-manifest.yaml"
    workflow_version = "legacy"
    if manifest_path.is_file() and yaml is not None:
        try:
            workflow_version = str((yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig")) or {}).get("workflow_version", "legacy"))
        except Exception:
            workflow_version = "legacy"
    if workflow_version == "5.3":
        approval_errors = validate_planning(project, "product")
        if approval_errors:
            for error in approval_errors:
                LOGGER.error(error)
            LOGGER.error("content planning requires explicit user approval of the current product-plan")
            return 1
    plan_path = output / "page-plan.md"
    copy_path = output / "copy" / "overlay-copy.md"
    if not args.force and (plan_path.exists() or copy_path.exists()):
        LOGGER.error("existing plan preserved; use --force to replace")
        return 2
    name = product_name(project)
    brand_status, brand_promise = brand_context(project)
    routes = reference_routes(project)
    plan = [
        "# 상세페이지 10장 일괄 생성 계획",
        "",
        f"- 상품: {name}",
        f"- 브랜드 상태: {brand_status}",
        f"- 브랜드 약속: {brand_promise}",
        "- 인물 정책: 실제 인물 픽셀 0건, 인물은 PG-01 기반 합성 모델만 사용",
        "- 이미지 정책: 1차 ImageGen은 무문자 비주얼, 2차는 각 이미지를 조건으로 승인 카피와 타이포그래피를 ImageGen이 직접 통합",
        "- 제작 게이트: 아래 카피는 안전한 초안이다. verified_* 사실과 고유 구매 이유로 보강하고 copy_status를 approved로 바꾸기 전에는 제작하지 않는다.",
        "",
        "| 순서 | 역할 | 구매 질문 | Evidence ID | 필요한 제품 면 | Reference source ID | 장면 | 실사진 | GIF | 금지 요소 | QA 기준 | 메인 헤드라인 |",
        "|---:|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    copy = [
        "# Overlay Copy",
        "",
        "초기 안전 카피다. verified_* 사실이 있으면 더 구체적으로 바꾸되 근거 없는 기능은 추가하지 않는다.",
        "",
    ]
    page_records = []
    content_modules = []
    product_plan: dict = {}
    product_claims: list[dict] = []
    if workflow_version == "5.3":
        plan_errors: list[str] = []
        product_plan = load_json(project / PRODUCT_PLAN_PATH, plan_errors, "product-plan")
        product_claims = [item for item in product_plan.get("claims", []) if isinstance(item, dict)]
        if plan_errors or not product_claims:
            for error in plan_errors or ["product-plan requires at least one approved claim"]:
                LOGGER.error(error)
            return 1
    for page, role, commercial_job, purpose, headline_template, subcopy, badge, layout, alignment, emphasis_template, proof_type in FLOW:
        headline = headline_template.format(product=name)
        emphasis = emphasis_template.format(product=name)
        selected_claim = product_claims[(int(page) - 1) % len(product_claims)] if workflow_version == "5.3" else None
        person = "텍스트 기반 합성 모델" if page == "01" else ("얼굴 없는 합성 손·발" if page == "07" else "없음")
        reason = {
            "01": "상품의 첫인상과 전체 형태",
            "02": "전체 제품과 구성 확인",
            "03": "사용 맥락 이해",
            "04": "전체 실루엣 확인",
            "05": "핵심 구조 확인",
            "06": "표면·봉제·라벨 확인",
            "07": "스타일링 맥락 확인",
            "08": "장면 다양성 확인",
            "09": "구매 정보 확인",
            "10": "핵심 내용 회상",
        }[page]
        brand_role = "브랜드 첫인상" if page == "01" else ("브랜드 증거 태도" if page in {"03", "04", "05", "06", "07"} else ("브랜드 구매 신뢰" if page == "09" else "브랜드 기억 회수" if page == "10" else "브랜드 시스템 유지"))
        proof_chain = "상황→행동/접촉→제품 반응→보이는 증거→제한 카피" if page in {"03", "04", "05", "06", "07", "08"} else "해당 역할의 검증 증거"
        route = routes.get(page, {}) if isinstance(routes.get(page, {}), dict) else {}
        required_views = ", ".join(str(value) for value in route.get("required_views", [])) or "확정 필요"
        source_ids = [str(value) for value in route.get("source_ids", [])]
        source_text = ", ".join(source_ids) or "확정 필요"
        buyer_question = purpose
        scene_text = f"{layout} / {proof_chain}"
        forbidden = "미확정 기능·수치·추가 부품·경쟁사 복제"
        qa_criteria = "질문-근거-사진 1:1, 제품 동일성, 승인 문구"
        plan.append(f"| {page} | {role} | {buyer_question} | FACT-ID 확정 필요 | {required_views} | {source_text} | {scene_text} | false | 검토 | {forbidden} | {qa_criteria} | {headline} |")
        page_records.append(
            {
                "page": page,
                "role": role,
                "commercial_job": commercial_job,
                "purchase_reason": reason,
                "proof_type": proof_type,
                "evidence": str(selected_claim.get("text", "")) if selected_claim else "verified facts required",
                "brand_role": brand_role,
                "buyer_question": buyer_question,
                "evidence_ledger_ids": [str(value) for value in selected_claim.get("evidence_ids", [])] if selected_claim else ["FACT-ID-required"],
                "required_product_view": required_views,
                "reference_source_ids": source_ids,
                "scene": scene_text,
                "real_photo_required": False,
                "forbidden_elements": ["unverified_claim", "invented_product_part", "competitor_copy"],
                "qa_criteria": ["claim_evidence_match", "product_identity", "exact_approved_copy"],
                "asset_strategy": "pending",
                "real_photo_replacement": [],
                "gif_candidate": None,
            }
        )
        if workflow_version == "5.3":
            claim = selected_claim or {}
            content_modules.append(
                {
                    "id": f"M{page}",
                    "order": int(page),
                    "role": role,
                    "headline": headline,
                    "body": subcopy,
                    "evidence_ids": [str(value) for value in claim.get("evidence_ids", [])],
                    "claim_ids": [str(claim.get("id", ""))],
                    "asset_ids": [f"ASSET-{page}"],
                    "editable_fields": ["headline", "body"],
                    "qa_criteria": ["copy_accuracy", "product_identity", "claim_evidence"],
                }
            )
        copy.extend(
            [
                f"## {page}",
                "- mode: conditioned",
                "- copy_status: draft_requires_fact_rewrite",
                f"- commercial_job: {commercial_job}",
                f"- brand_role: {brand_role}",
                f"- claim_id: CLAIM-{page}",
                f"- headline: {headline}",
                f"- emphasis: {emphasis}",
                f"- headline_alignment: {alignment}",
                f"- proof_type: {proof_type}",
                "- proof_frame: verified visual evidence required",
                "- asset_mode: choose from asset-strategy.md",
                f"- subcopy: {subcopy}",
                f"- badge: {badge}",
                "- safe_area: top",
                f"- evidence: {'verified facts required' if page == '09' else 'visible product form or non-claiming context'}",
                "",
            ]
        )
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    copy_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("\n".join(plan) + "\n", encoding="utf-8")
    copy_path.write_text("\n".join(copy) + "\n", encoding="utf-8")
    if workflow_version == "5.3":
        content_plan = {
            "schema_version": "1.0",
            "artifact_type": "content_plan",
            "project_id": str(product_plan.get("project_id", "")),
            "status": "ready_for_approval",
            "product_plan_ref": {"path": PRODUCT_PLAN_PATH, "sha256": sha256(project / PRODUCT_PLAN_PATH)},
            "rendering": {
                "mode": "hybrid_html",
                "text_layer": "native_html",
                "visual_layer": "external_assets",
            },
            "modules": content_modules,
        }
        content_path = project / CONTENT_PLAN_PATH
        content_path.parent.mkdir(parents=True, exist_ok=True)
        content_path.write_text(json.dumps(content_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        approval_path = project / CONTENT_APPROVAL_PATH
        approval = load_json(approval_path, [], "content-plan approval")
        approval.update(
            {
                "schema_version": "1.0",
                "artifact_type": "approval",
                "target_type": "content_plan",
                "target_path": CONTENT_PLAN_PATH,
                "target_sha256": "",
                "decision": "pending",
                "actor_type": "user",
                "actor_id": "",
                "approved_at": "",
                "note": "content-plan was regenerated and requires user approval",
            }
        )
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if manifest_path.is_file() and yaml is not None:
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig")) or {}
            if isinstance(manifest, dict) and str(manifest.get("workflow_version", "")) in {"5.0", "5.1", "5.2", "5.3"}:
                manifest["pages"] = page_records
                manifest_path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
        except Exception as exc:
            LOGGER.warning("project-manifest.yaml page synchronization skipped: %s", exc)
    LOGGER.info("ten-page plan created before generation: %s", plan_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
