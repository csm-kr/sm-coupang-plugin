---
name: coupang-detail-page-generator
description: 실제 상품 사진·공급처 URL·쿠팡 경쟁상품과 리뷰를 근거로 제품기획과 콘텐츠기획을 분리하고 사용자 승인을 받은 뒤, 주장-근거-이미지 스토리보드와 수치형 Acceptance Criteria를 잠그고 제품 비주얼은 이미지·GIF·영상으로 만들며 카피·정보는 편집 가능한 HTML로 조립해 소재별 QA와 통합 QA를 수행한다. 모델·커버 범위·치수 이미지, ImageGen 프롬프트, 사진 크롭·모듈 순서·한글 줄바꿈·광고표현 검수가 필요할 때 사용한다.
---

# 쿠팡 상세페이지: 제품 → 제품기획 승인 → 콘텐츠기획 승인 → 소재 제작·QA → HTML 조립·통합 QA

단순히 10장을 채우지 않는다. 제품 사실, 시장의 구매 질문, 브랜드 약속, 시각 증거가 한 줄로 연결된 상세페이지와 다음 촬영·모션 실행안까지 만든다.

## 절대 규칙

- `raw/`의 원본 상품을 제품 형태의 유일한 기준으로 사용한다. 도매·경쟁사·레퍼런스 제품 외형을 섞지 않는다.
- 모든 사실을 `CONFIRMED_USER`, `CONFIRMED_SOURCE`, `OBSERVED_IMAGE`, `INFERRED`, `CONFLICT`, `UNKNOWN`, `FORBIDDEN`으로 분리한다. 최종 카피에는 앞의 세 상태만 사용한다. 5.1 이하의 기존 상태는 읽기만 하고 새 프로젝트에는 쓰지 않는다.
- 실제 인물의 얼굴·피부·팔·손·몸·포즈 픽셀을 ImageGen 입력이나 최종 이미지에 사용하지 않는다. 필요한 인물·손·발은 텍스트에서 새로 만든 성인 합성 인물만 사용한다.
- 경쟁사 문구·브랜드·로고·수치·인증·후기를 복제하지 않는다. 경쟁사 관찰은 구매 판단 기준과 증거 방식으로만 변환한다.
- 분위기 사진을 기능 증거로 세지 않는다. 10장 중 최소 5장은 접촉·구조·변형·사용·보관·실측 중 서로 다른 기능 증거가 주인공이어야 한다.
- 얼굴이 보이는 전신 모델은 기본 1장, 최대 2장이다. 같은 포즈·보행·크롭을 반복하지 않는다.
- 제품마다 브랜드명 후보 3개 이상과 최종 제안 1개를 만든다. 제안명은 최종 보고에서 반드시 말하되, 사용자가 승인하기 전에는 상세 이미지·워드마크·로고에 노출하지 않는다.
- 브랜드 표현은 `실용 증거형 → 전문 기능형 → 감성 생활형` 순으로 우선한다. 감성 장면이 제품 효용·구조 증거를 대신하면 실패다.
- 워크플로 5.3의 ImageGen은 무문자 시각 자산만 만든다. 카피·표·FAQ·주의 문구는 네이티브 HTML로 조립하며 이미지에 굽지 않는다.
- 정보가 부족한 장면·수치·관리법은 상상하지 않는다. `촬영·공급사 확인 필요`로 넘기고 최종 주장에서는 제외한다.
- 제품 동일성은 더 엄격하게 처리한다. 실제 SKU의 실루엣·앞코·입구·잠금부·절개·밑창·각인·구성이 하나라도 불명확하거나 장면마다 달라지면 제품 생성·합성을 중단하고 확인 부위의 촬영을 요청한다.
- 제품 소스 계보를 `raw_capture`, `manufacturer_source`, `generated_master`, `generated_scene`으로 구분한다. 제품 동일성은 앞의 두 실제 소스로만 확정하며 AI 생성 마스터·장면은 실제 제품 근거로 사용하지 않는다.
- 페이지별 미세 승인은 요구하지 않는다. 그러나 `product-plan.json`과 `content-plan.json`은 각각 사용자가 현재 파일을 명시적으로 승인해야 한다. 추천대로 진행, 일괄 제작 요청, 사용자 침묵은 승인으로 대체할 수 없다.

## 정반합 의사결정 루프

모든 단계에서 아래 다섯 필드를 기록한다. 자세한 규칙은 [references/workflow-synthesis.md](references/workflow-synthesis.md)를 따른다.

1. `thesis`: 원본 사실, 기존 브랜드, 사용자 요구처럼 지켜야 할 기준
2. `antithesis`: 경쟁 불만, 제작 위험, 규제, 정보 부족처럼 기준을 흔드는 반대 근거
3. `synthesis`: 둘을 함께 만족시키는 실행 결정
4. `proof`: 그 결정을 사진·실측·출처·QA로 확인하는 방법
5. `rollback`: 실패 시 돌아갈 정확한 단계

의견을 절충해 흐리게 만들지 않는다. 충돌이 생기면 제품 사실·법적 안전·고객 오인 방지를 우선하고, 설득력은 더 강한 증거 방식으로 회복한다.

## 프로젝트 시작

새 프로젝트는 먼저 초기화한다.

```powershell
python <skill-dir>/scripts/initialize_project.py --project <project-root>
python <skill-dir>/scripts/inspect_assets.py --project <project-root>
```

기본 입력은 상품 원본 1개 이상과 도매·판매 URL이다. 레퍼런스·기존 결과·브랜드 자산은 선택 입력이다. 역할과 출처 계약은 [references/input-contract.md](references/input-contract.md), 전체 산출물 계약은 [references/project-artifact-contract.md](references/project-artifact-contract.md)를 따른다.

워크플로 `5.3` 신규 프로젝트는 이미지·GIF·영상 외부 자산과 네이티브 HTML 텍스트를 분리한다. `5.2` 이하 기존 프로젝트는 원래 정적 이미지·타이포그래피 계약을 보존하며 자동 변환하지 않는다. 산출물·승인·QA 계약은 [references/planning-and-hybrid-contract.md](references/planning-and-hybrid-contract.md)를 따른다.

## 10단계 진행 상태

현재 위치를 보고할 때 다음 번호를 고정해 사용한다.

1. 소싱·가격 승인
2. 제품 사실·정체성 잠금
3. 시장·리뷰 조사
4. 제품기획과 사용자 승인
5. 콘텐츠기획과 사용자 승인
6. UI와 장별 자산 전략
7. 콘텐츠 소재 생성과 소재 QA
8. 실사진·GIF·영상 교체
9. 콘텐츠 생성: 이미지+HTML 조립
10. 통합 QA와 최종 승격

상태 보고에는 `execution_stage`, `asset_scope`, `production_gate`, `next_gate`를 함께 적는다. 예를 들어 콘셉트 이미지를 생성 중이면 `execution_stage: 7/10`, `asset_scope: concept_only`, `production_gate: blocked`로 보고한다. 이미지 파일이 생겼다는 이유만으로 판매용 소재 생성이나 `produced` 상태로 올리지 않는다.

사용자가 실제 SKU 원본 없이 시각 품질 확인을 명시적으로 승인한 경우에만 `output/prototypes/<prototype-id>/`에서 concept-only 분기를 실행한다. 이 분기에서는 다음을 강제한다.

- `prototype-manifest.json`에 `production_use_allowed: false`와 실제 SKU 교체 조건을 기록한다.
- 생성 직후 모든 파일을 프로토타입 manifest와 `source-lineage.json`에 등록한다.
- 모든 결과를 `연출용 콘셉트 이미지`로 표시하고 제품 동일성·치수·성능 근거로 승격하지 않는다.
- UI·구매 흐름·이미지+HTML 조립 품질은 검토할 수 있지만 실제 SKU 판매용 상태로 승격하지 않는다.
- 실제 제품 단독 canonical source, 실측·라벨·옵션·필수 간이 QA가 확보되면 Gate A로 돌아가 판매용 자산을 다시 만든다.

## Gate A — 제품 사실과 정체성 잠금

1. 모든 입력을 `PRODUCT_SOURCE`, `SUPPLIER_REFERENCE`, `COMPETITOR_REFERENCE`, `STYLE_REFERENCE`, `GENERATED_DRAFT`, `MEASUREMENT_EVIDENCE`로 분류하고, 별도로 `raw_capture`, `manufacturer_source`, `generated_master`, `generated_scene` 계보를 기록한다. 제품 외형은 신뢰 가능한 `PRODUCT_SOURCE`만 결정한다.
2. `output/product-truth-ledger.md`, `output/product-facts.json`, `output/product-invariants.txt`를 완성한다.
3. `output/product-source-lineage.json`에 실제 소스와 생성 자산의 계보를 기록한다. 신뢰 가능한 `raw_capture` 또는 `manufacturer_source`가 없으면 동일성 게이트를 통과시키지 않는다.
4. 제품 전체 비율, 정·후·측·상·하단, 앞코·입구, 색·투명도, 스트랩·잠금부·절개, 부품 수·위치·방향, 밑창·봉제·각인·라벨, 좌우 대칭, 구성과 결합, 변형되는 부분과 고정되는 부분, 절대 만들면 안 되는 유사 제품을 관찰 가능한 `product identity lock`으로 만든다.
5. 원본마다 `product_only`, `contains_person`, `safe_for_imagegen`, `safe_for_final_composite`를 판정한다. `contains_person`은 두 안전 필드가 항상 `false`다.
6. 실제 소스 중 정체성을 가장 잘 보이는 3~5장을 canonical reference로 고르고 `output/reference-routing.json`에 장별 필요한 면과 선택 소스 ID를 기록한다. 매번 같은 묶음을 쓰지 않는다.
7. 각 주장에 출처, 확인 상태, 허용 카피, 필요한 추가 증거를 연결한다.
8. 동일성 항목 하나라도 확인 불가이면 `BLOCKED`로 판정하고 필요한 정면·좌우 측면·앞코·입구·잠금 전후·밑창·각인·구성·사용 순서 중 필요한 촬영만 요청한다.

촬영 없이 진행하겠다는 사용자의 명시적 선택이 있을 때만 `concept_only_opt_in: true`로 기록하고 계속할 수 있다. 이때 모든 생성물은 `연출용 콘셉트 이미지`이며 실제 구조·사용법·제품 상세 증거로 표현하지 않는다.

```powershell
python <skill-dir>/scripts/validate_product_facts.py --facts <project-root>/output/product-facts.json
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate evidence --strict
```

[references/fact-policy.md](references/fact-policy.md)와 [references/product-truth-and-asset-strategy.md](references/product-truth-and-asset-strategy.md)를 따른다. 검증 전에는 시장조사 소구를 우리 제품 주장으로 승격하지 않는다.

## Gate B — Browser Use 시장·리뷰 조사

반드시 설치된 `browser-use` 스킬을 완전히 읽고 Browser Use CLI로 실제 Chrome을 제어한다. 인앱 브라우저로 대체하지 않는다.

1. 작업 전 열린 탭 목록을 기록한다.
2. 출처 URL을 먼저 열어 제품명·모델·옵션·사실·상세 자산을 저장한다.
3. 쿠팡에서 동일 모델, 같은 구조의 직접 경쟁상품, 다른 방식의 대체상품을 조사한다. 직접 경쟁사는 5개 이상 확보한다.
4. 각 상세페이지와 접근 가능한 리뷰에서 반복 긍정·불만·혼동·반품 위험·전개 순서·증거 모듈을 요약한다.
5. 빈도는 `높음/중간/낮음/확인 부족`으로 기록하고 한두 리뷰를 시장 전체로 일반화하지 않는다.
6. `경쟁 관찰 → 구매 판단 기준 → 우리 제품 근거 → 시각 증거`가 모두 이어지는 항목만 승인한다.
7. 조사 종료 시 이번 작업이 연 탭만 닫고 기존 사용자 탭은 보존한다.

산출물은 `output/browser-research/`의 JSON·출처·캡처와 `output/competitor-pain-map.md`, `output/planning-principles.md`다. [references/browser-use-competitor-research.md](references/browser-use-competitor-research.md)를 따른다.

```powershell
python <skill-dir>/scripts/validate_market_research.py --project <project-root> --strict
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate market --strict
```

## Gate C — 제품기획과 사용자 승인

제품기획은 `무엇을 누구에게 어떤 오퍼로 팔 것인가`를 잠근다. 브랜드는 그 결정을 반복해서 기억시키는 시스템이며 제품기획 안에 포함한다.

1. 기존 브랜드가 있으면 이름·로고·컬러·말투·금지사항을 `established`로 보존한다.
2. 없으면 제품 사실과 고객 불안에서 `working_draft` 브랜드 코어를 만든다. 제품마다 후보 3개 이상을 비교하고 최종 제안명 1개를 선택해 `proposed`로 기록한다.
3. 제안 브랜드명은 최종 보고에서 반드시 사용자에게 말한다. 사용자 승인 전에는 `name_usage_allowed: false`를 유지해 이미지·워드마크·로고에 노출하지 않는다.
4. `카테고리에서 익숙해야 하는 것`과 `우리만 반복할 것`을 분리해 포지셔닝, 약속, 이유, 성격, 목소리, 사진, 컬러, 컴포넌트, 기억 장치를 정의한다.
5. 표현 우선순위는 `실용 증거형 → 전문 기능형 → 감성 생활형`으로 고정한다. 실용 증거가 구매 이유를 만들고, 전문 기능 설명이 신뢰를 보강하며, 감성 생활 장면은 사용 맥락을 완성한다.
6. 상세페이지용 캠페인 변형은 브랜드 코어를 바꾸지 않고 제품 카테고리 강조색·상황 장면만 바꾼다.

`output/brand/brand-name-candidates.md`, `brand-brief.md`, `brand-system.json`, `brand-guide.md`, `brand-evidence-library.json`을 만든다. 제품별 제안명·포지셔닝·목소리·시각 토큰·금지 복제가 같은 논리로 이어져야 한다. [references/brand-system.md](references/brand-system.md)를 따른다.

`output/planning/product-plan.json`에 승인된 후보 ID, 핵심 고객·문제·포지셔닝, 판매가·옵션·묶음, 게시 가능한 주장·근거와 금지사항을 기록한다. 초안 검증 후 사용자에게 한 번에 제시하고, 명시적 승인을 받은 경우에만 현재 파일 해시를 승인 기록에 묶는다.

```powershell
python <skill-dir>/scripts/validate_planning_contracts.py --project <project-root> --gate product-draft
python <skill-dir>/scripts/record_user_approval.py --project <project-root> --target product-plan `
  --actor-id <user-id> --confirm-user-approval
python <skill-dir>/scripts/validate_planning_contracts.py --project <project-root> --gate product
```

사용자 승인 없이 승인 기록 명령을 실행하지 않는다. 승인 후 제품기획이 바뀌면 기존 승인은 오래된 상태가 되어 자동 차단된다.

```powershell
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate brand --strict
```

## Gate D — 콘텐츠기획과 사용자 승인

시장 결과를 카피 목록이 아니라 다음 인과관계로 바꾼다.

`고객 상황 → 구매 직전 질문 → 우리 제품의 검증 답변 → 사진 증거 → 다음 질문`

승인된 제품기획을 입력으로 `output/planning/content-plan.json`을 만든다. 추천 제품명·검색형 상품명, 리뷰 기반 구매 불안, 핵심 소구, 보류 소구, 관리·사이즈·구성·주의, 장별 카피·근거·자산·QA 기준을 모듈로 기록한다. 카피는 HTML에서 수정 가능한 `headline`과 `body`로 분리한다.

다음을 잠근다.

- 핵심 타겟 1그룹, 대표 문제 1개, 핵심 소구 3개, 금지 표현
- 한 줄 기획 원리와 페이지별 정반합 결정
- 페이지마다 고유한 `commercial_job`, `purchase_reason`, `buyer_question`, `evidence_ledger_ids`, `proof_type`, `evidence`, `brand_role`, `required_product_view`, `reference_source_ids`, `scene`, `real_photo_required`, `gif_candidate`, `forbidden_elements`, `qa_criteria`
- 기능 페이지마다 `상황 → 접촉/행동 → 제품 반응 → 보이는 증거 → 제한된 카피`

```powershell
python <skill-dir>/scripts/build_page_plan.py --project <project-root> --force
python <skill-dir>/scripts/validate_planning_contracts.py --project <project-root> --gate content-draft
python <skill-dir>/scripts/record_user_approval.py --project <project-root> --target content-plan `
  --actor-id <user-id> --confirm-user-approval
```

초안은 반드시 상품 사실과 승인 소구로 다시 쓴 뒤 `status: ready_for_approval`로 바꿔 사용자에게 제시한다. 사용자가 현재 콘텐츠기획을 승인한 뒤에만 시각 소재를 생성한다. [references/function-first-evidence.md](references/function-first-evidence.md), [references/page-structure.md](references/page-structure.md), [references/copy-rules.md](references/copy-rules.md)를 따른다.

```powershell
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate planning --strict
```

## Gate E — UI와 장별 자산 전략

이미지보다 먼저 `output/ui-guide.md`와 `output/asset-strategy.md`를 잠근다.

- UI는 브랜드 토큰을 상속하고 캔버스·안전 여백·그리드·폰트·카드·아이콘·사진 크롭·정렬 축을 정의한다.
- 각 제품 요소를 `PRESERVE`, `COMPOSITE`, `EDIT_BACKGROUND_ONLY`, `GENERATE_SUPPORT`, `GENERATE_PRODUCT_ALLOWED`, `REAL_PHOTO_REQUIRED`, `GIF_REQUIRED` 중 하나로 판정한다.
- 히어로, 구조, 잠금부, 밑창, 옵션, 사이즈, 첫·마지막 구매 장면은 원본 왜곡 위험이 높으므로 `PRESERVE` 또는 `COMPOSITE`를 우선한다.
- 원본에 없는 각도·내부·밑창을 AI로 상상하지 않는다. 빈 교체 프레임과 촬영 목록으로 넘긴다.
- `reference-routing.json`의 3~5개 canonical source 안에서 페이지 목적에 맞는 1~5개만 선택한다. 히어로·소재·사용 장면이 보존해야 할 면이 다르면 입력 묶음도 달라야 한다.
- `output/planning/visual-storyboard.json`에 모듈별 주장·근거·자산 ID, `visual_thesis`, 필수 시각 단서, 모델 정책, 모바일·800px 순서, 피사체·핵심 부위 bbox, 주장-이미지 점수 기준을 기록한다.
- 착용형 상품은 실제 크기 맥락을 보여 주는 합성 모델 장면을 기본 1장, 최대 2장 둔다. 모델 장면은 사용 맥락이며 실제 SKU 성능 증거로 쓰지 않는다.
- 치수 장면은 A~E 값뿐 아니라 시작점·끝점·단위·검증 상태를 잠근다. 기준점이 불명확하면 치수 이미지 생성을 차단한다.

[references/ui-design-system.md](references/ui-design-system.md), [references/product-truth-and-asset-strategy.md](references/product-truth-and-asset-strategy.md), [references/commercial-ad-benchmark.md](references/commercial-ad-benchmark.md), [references/visual-storyboard-and-ac.md](references/visual-storyboard-and-ac.md)를 따른다.

```powershell
python <skill-dir>/scripts/validate_visual_storyboard.py --storyboard <project-root>/output/planning/visual-storyboard.json --report <project-root>/output/qa/visual-storyboard-qa.json --strict
```

```powershell
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate ui_assets --strict
```

## Gate F — 제품 보존 시험과 시각 소재 제작·개별 QA

제품이 크게 보이는 1장 또는 3장을 먼저 만들어 원본과 비교한다. 생성이 구조를 틀리면 해당 장은 합성 방식으로 전환한다.

`output/fidelity-pilot.md`에서 실제 소스와 실루엣·앞코·입구·스트랩·잠금·절개·밑창·각인·색·구성을 대조한다. 한 항목이라도 불명확하거나 다르면 `BLOCKED`로 판정하고 필요한 촬영을 요청한다.

```powershell
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate fidelity_pilot --strict
```

```powershell
python <skill-dir>/scripts/build_imagegen_queue.py --project <project-root> `
  --reference <reference-image> --product-images <person-free-product-images> `
  --confirm-person-free --confirm-actual-product-source --force
python <skill-dir>/scripts/validate_campaign_assets.py --project <project-root> --queue-only --strict
python <skill-dir>/scripts/build_image_prompts.py --project <project-root> --force
```

사용자 레퍼런스가 없으면 `--reference`를 생략해 스킬의 상업형 벤치마크를 사용한다.
사용자가 촬영 없이 콘셉트 진행을 명시한 예외 프로젝트만 `--confirm-actual-product-source` 대신 `--confirm-concept-only`를 사용한다. 모든 생성 소재에는 실제 제품 증거가 아니라는 계보와 `연출용 콘셉트 이미지` 표시가 강제된다.

비트맵 생성·편집에는 `imagegen` 스킬을 사용한다. [references/campaign-generation.md](references/campaign-generation.md)와 [references/imagegen-prompt-template.md](references/imagegen-prompt-template.md)를 따른다.

1. 콘텐츠 모듈에 필요한 무문자 이미지·GIF·영상 소재를 만든다.
2. 모든 ImageGen 작업에 `subject`, `composition`, `claim_link`, `measurement_guidance`, 불변 조건과 금지 요소를 넣는다. 숫자·치수선·한글 카피는 생성하지 않고 HTML/SVG로 조립한다.
3. 실제 SKU와 구조가 다르면 생성 반복 대신 동일성 게이트로 회귀해 촬영을 요청한다.
4. 각 파일을 `output/content-assets/manifest.json`에 안정적 ID, SHA-256, 대체 텍스트, 주장·근거·계보 ID와 함께 등록한다.
5. `output/qa/material-qa.json`에서 모듈별 기술·제품 동일성·주장-근거·카피 정확성·시각 품질과 주장-이미지 연관성 80점 이상을 자동·육안으로 검사한다.
6. 한 모듈이 실패하면 해당 소재만 수정하고 다시 QA한다. 소재 QA가 하나라도 실패하면 HTML 조립을 시작하지 않는다.

```powershell
python <skill-dir>/scripts/validate_campaign_assets.py --project <project-root> --strict
python <skill-dir>/scripts/validate_material_qa.py --project <project-root> --strict
```

## Gate G — 실사진 교체와 GIF·영상 실행안

시안이 완성되면 `output/photo-shot-list.md`와 `output/gif-plan.md`를 반드시 완성한다. 각 컷은 페이지·영역·해결할 불안·촬영 상태·구도·교체 방법까지 연결한다. 실제 치수·포장·착용 순서·세척·밑창·마감·성능 증명은 실사를 우선한다. 제품 동작 GIF는 3~6초 안에 이해되고 형태가 프레임마다 유지되어야 한다. [references/real-photo-and-motion.md](references/real-photo-and-motion.md)를 따른다.

## Gate H — 이미지+HTML 조립과 통합 QA

```powershell
python <skill-dir>/scripts/build_hybrid_detail_page.py --project <project-root>
python <skill-dir>/scripts/validate_hybrid_package.py --project <project-root> --strict
python <skill-dir>/scripts/validate_market_research.py --project <project-root> --strict
python <skill-dir>/scripts/validate_outputs.py --project <project-root> --strict
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate production --strict
```

조립기는 승인된 콘텐츠기획의 `headline`·`body`를 `<h2>`·`<p>`로 만들고, 검수된 시각 소재는 외부 `<img>`·`<video>`로 참조한다. `data:image` 인라인과 이미지 안 카피를 금지한다. 조립 후에는 기획 정렬, 구매 흐름, 브랜드 일관성, 모바일 반응형, 접근성, 광고 표현, 채널 규격을 다시 자동·육안 검수한다. `integration-qa.json`은 현재 `package-manifest.json` 해시에 묶여야 한다.

모든 모듈에 `data-claim-ids`, 모든 이미지·영상에 `data-asset-id`를 둔다. 실제 360px·800px 좌표에서 승인 모듈 순서 100%, claim/asset 연결 100%, 피사체 bbox 95% 이상, 핵심 부위 bbox 100%를 검증한다.

```powershell
node <skill-dir>/scripts/collect_visual_layout_metrics.mjs --cdp http://127.0.0.1:9225 --url http://127.0.0.1:8765/html/detail-page.html --storyboard <project-root>/output/planning/visual-storyboard.json --viewports 360x900,800x1000 --screenshots <project-root>/output/qa/visual-layout-screenshots --output <project-root>/output/qa/visual-layout-metrics.json
python <skill-dir>/scripts/validate_visual_layout.py --storyboard <project-root>/output/planning/visual-storyboard.json --metrics <project-root>/output/qa/visual-layout-metrics.json --report <project-root>/output/qa/visual-layout-qa.json --strict
```

HTML 타이포그래피는 DOM 텍스트나 이미지 캡처만 보고 통과시키지 않는다. QA용 Chromium 또는 Edge를 실제 `360x900`, `800x1000` viewport로 열고 각 글자의 렌더 좌표와 모듈별 스크린샷을 수집한다. 캐시는 끄고 새 URL로 측정하며, QA가 띄운 브라우저·서버는 수집 종료 후 닫는다.

```powershell
node <skill-dir>/scripts/collect_html_typography_metrics.mjs `
  --cdp http://127.0.0.1:9225 `
  --url http://127.0.0.1:8765/html/detail-page.html `
  --viewports 360x900,800x1000 `
  --screenshots <project-root>/output/qa/typography-screenshots `
  --output <project-root>/output/qa/typography-metrics.json
python <skill-dir>/scripts/validate_html_typography.py `
  --metrics <project-root>/output/qa/typography-metrics.json `
  --report <project-root>/output/qa/typography-qa.json `
  --strict
```

필수 viewport 누락, 문서·요소 가로 넘침, 단어·숫자 중간 분리, 한 글자 고아행, 허용 행수 초과, 세로 잘림, 행 겹침, 대체문자 발생은 오류다. 짧은 마지막 행도 `--strict`에서 차단한다. 제목·중요 본문에는 `data-typography-max-lines`를 명시하고, 의도된 짧은 마지막 행만 `data-typography-allow-short-last="true"`로 예외를 기록한다. 자동 결과가 통과한 뒤 360px·800px 모듈별 캡처를 육안 검수해야 한다. 자세한 절차와 수정 순서는 [references/html-typography-qa.md](references/html-typography-qa.md)를 따른다.

## Gate I — 폐쇄형 최종 승격

소재 QA와 통합 QA가 모두 통과해야 `completed`다. 실패는 `rollback`에 기록한 가장 가까운 단계로만 되돌린다. HTML·CSS·계획·자산이 변경되면 패키지 해시가 바뀌므로 통합 QA를 다시 수행한다. 전체 기준은 [references/qa-checklist.md](references/qa-checklist.md)를 따른다.

시각 검수까지 통과한 뒤 매니페스트의 `final_qa`를 `pass`로 바꾸고 마지막 폐쇄 검증을 실행한다.

```powershell
python <skill-dir>/scripts/validate_project_manifest.py --project <project-root> --gate final --strict
```

## 지속 업데이트

새 사례를 받으면 기존 규칙을 덮어쓰지 않는다. `사례에서 관찰한 원리 → 기존 원리의 반례 → 적용 범위가 명시된 새 합성 규칙 → 실제 프로젝트 회귀 검증` 순서로 추가한다. 상품·브랜드·문구를 복제하지 않고 구성·증거·타이포·밀도 원리만 학습한다. 회귀 검증에서 사실성, 실제 인물 0건, 브랜드 코어, 기능 증거, 10장 구매 흐름이 약해지면 업데이트를 승인하지 않는다.

## 완료 산출물

- 제품: 자산 목록, 프로젝트 매니페스트, 사실 원장, 사실 JSON, 정체성 잠금, canonical reference 라우팅
- 조사: 출처, 경쟁사 5개 이상, 리뷰 불편 지도, 소구 맵, 기획 원리
- 브랜드: 제품별 브랜드명 후보·최종 제안, 브랜드 브리프, 시스템 JSON, 가이드, 증거 라이브러리
- 제품기획: `product-plan.json`, 현재 해시에 묶인 사용자 승인
- 콘텐츠기획: `content-plan.json`, 현재 해시에 묶인 사용자 승인, UI 가이드와 자산 전략
- 비주얼 기획: `visual-storyboard.json`, 수치형 AC, ImageGen 프롬프트, 커버 범위·치수 기준점
- 제작: `content-assets/manifest.json`, 이미지·GIF·영상 소재, 모듈별 `material-qa.json`
- 조립: 편집 가능한 `detail-page.html`, `styles.css`, `package-manifest.json`
- 후속 실행: 완성 HTML과 분리된 `experiment-plan.json`, 실사진 촬영·교체 목록, GIF 계획
- 검수: 소재별 자동·육안 QA, 조립 후 통합 자동·육안 QA, `visual-layout-metrics.json`·`visual-layout-qa.json`, `typography-metrics.json`·`typography-qa.json`, 360/800px 모듈 캡처, 재생성 로그

최종 보고 첫 줄에는 `편집 가능한 상세페이지: <project-root>/output/html/detail-page.html`을 적는다. 이어서 제품기획·콘텐츠기획 승인 상태, 소재 QA·통합 QA 결과, 남은 미확인 정보, 실사진·GIF·영상 우선순위만 간결하게 적는다.

통합 QA는 한글 줄바꿈·고아행·오버플로, 모듈 순서, 주장-자산 연결과 이미지 크롭을 실제 브라우저 좌표로 검사한다.
