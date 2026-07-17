# 프로젝트 산출물 계약

## 폴더 구조

```text
project-root/
├── raw/
├── reference/
└── output/
    ├── project-manifest.yaml
    ├── README.md
    ├── asset-inventory.md
    ├── product-truth-ledger.md
    ├── product-facts.json
    ├── product-invariants.txt
    ├── product-source-lineage.json
    ├── reference-routing.json
    ├── browser-research/
    ├── competitor-pain-map.md
    ├── planning-principles.md
    ├── planning/
    │   ├── product-plan.json
    │   ├── content-plan.json
    │   └── visual-storyboard.json
    ├── approvals/
    │   ├── product-plan-approval.json
    │   └── content-plan-approval.json
    ├── brand/
    │   ├── brand-name-candidates.md
    │   ├── brand-brief.md
    │   ├── brand-system.json
    │   ├── brand-guide.md
    │   └── brand-evidence-library.json
    ├── ui-guide.md
    ├── page-plan.md
    ├── copy/overlay-copy.md
    ├── asset-strategy.md
    ├── fidelity-pilot.md
    ├── generated-pages/
    ├── typography-pages/
    ├── prototypes/
    │   └── <prototype-id>/
    │       ├── prototype-manifest.json
    │       ├── source-lineage.json
    │       └── content-assets/
    ├── content-assets/
    │   ├── manifest.json
    │   └── 이미지·GIF·영상
    ├── html/
    │   ├── detail-page.html
    │   ├── styles.css
    │   └── package-manifest.json
    ├── qa/
    │   ├── material-qa.json
    │   ├── integration-qa.json
    │   ├── typography-metrics.json
    │   ├── typography-qa.json
    │   ├── typography-screenshots/
    │   ├── visual-storyboard-qa.json
    │   ├── visual-layout-metrics.json
    │   ├── visual-layout-qa.json
    │   └── visual-layout-screenshots/
    ├── images/01.png ... 10.png  # 5.2 레거시 정적 납품본
    ├── photo-shot-list.md
    ├── gif-plan.md
    ├── experiment-plan.json
    ├── contact-sheet.jpg
    ├── image-inspection.json
    ├── ocr-expectations.json
    ├── ocr-report.json
    ├── regeneration-log.json
    └── qa-report.md
```

## 매니페스트 원칙

- `workflow_version`, 플랫폼, 캔버스, 모듈 수를 명시한다. 신규 5.3 프로젝트는 네이티브 HTML 텍스트와 외부 시각 자산을 분리한다.
- 모든 입력의 제작 역할·계보·사람 포함 여부·사용 안전성을 기록한다.
- 제품 필드의 값과 7개 Evidence Ledger 상태를 구분한다.
- 실제 제품 canonical source 3~5개와 페이지별 참조 라우팅을 기록한다.
- 브랜드의 제품별 최종 제안명, 이름 상태, 이미지 사용 가능 여부, 표현 우선순위를 기록한다.
- 제품기획과 콘텐츠기획을 별도 JSON으로 기록하고, 각각 현재 파일 해시에 묶인 사용자 승인만 인정한다.
- 콘텐츠 모듈마다 구매 질문, 원장 ID, 참조 source ID, 장면, 금지 요소와 QA 기준을 둔다.
- OCR 기대문구와 불일치 후보, 제품·레이아웃 최대 2회, 한글 영역 최대 3회의 국소 수정 이력을 분리해 기록한다. 로컬 타이포그래피 폴백은 허용하지 않는다.
- 5.3 HTML은 360px·800px 실제 브라우저 좌표 기반 `typography-metrics.json`과 엄격 판정 `typography-qa.json`을 보존한다. HTML·CSS·카피가 바뀌면 이전 결과는 오래된 상태다.
- 신규 스토리보드 계약은 모듈 순서, claim/asset ID, 피사체·핵심 부위 bbox와 주장-이미지 점수를 보존한다. HTML·CSS·자산·스토리보드가 바뀌면 `visual-layout-*` 결과는 오래된 상태다.
- 게이트 상태와 정반합 결정 로그를 남긴다.

## 완료 상태

- `draft`: 자동 템플릿만 존재
- `researched`: 제품·시장 근거가 잠김
- `product_plan_approved`: 제품기획의 현재 해시를 사용자가 승인함
- `content_plan_approved`: 승인된 제품기획을 참조하는 콘텐츠기획의 현재 해시를 사용자가 승인함
- `storyboard_validated`: 승인 콘텐츠기획을 참조하는 스토리보드와 수치형 AC가 자동 검증을 통과함
- `produced`: 실제 소스와의 제품 보존 시험 및 소재별 자동·육안 QA를 통과함
- `assembled`: 승인 소재가 HTML·CSS로 조립됨
- `completed`: 통합 자동·육안 QA가 현재 패키지 해시에 대해 통과함

파일이 존재한다는 이유만으로 상태를 올리지 않는다. 각 게이트의 필수 내용과 검증 결과를 함께 확인한다.

## Concept-only 프로토타입

실제 SKU canonical source가 없지만 사용자가 시각 품질 확인을 명시적으로 승인한 경우에만 `output/prototypes/<prototype-id>/`에 격리한다.

- `prototype-manifest.json`에 `artifact_type: concept_only_prototype`, `production_use_allowed: false`, 사용자 승인 범위와 실제 SKU 교체 조건을 기록한다.
- `source-lineage.json`에 생성 마스터와 장면별 파일·source ID·생성 단계·`concept_only: true`를 기록한다.
- 생성 자산은 UI·구매 흐름·HTML 프로토타입 검토에만 사용하고 제품 동일성·치수·성능 증거로 사용하지 않는다.
- concept-only 생성 완료는 프로젝트의 `produced`, `assembled`, `completed` 상태를 열지 않으며 실제 SKU 판매용 상태로 승격하지 않는다.
- 실제 제품 단독 canonical source와 필수 실측·라벨·옵션·간이 QA를 확보한 뒤 Gate A부터 판매용 자산을 다시 검증한다.

## 버전 호환

`project-manifest.yaml`이 없는 기존 프로젝트는 레거시 검증 경로를 사용한다. 5.0·5.1·5.2 프로젝트의 정적 이미지·타이포그래피 계약은 보존한다. 5.3 새 프로젝트는 분리된 두 계획, 사용자 승인 해시, 외부 콘텐츠 자산, 소재 QA, HTML 패키지와 통합 QA를 포함한다.

5.3 이상의 편집 가능한 정본은 `output/html/detail-page.html`, `styles.css`, `content-assets/`다. 실제 SKU에서 확인할 촬영·간이 실험·교체 자산은 별도 `output/experiment-plan.json`에 둔다. 쿠팡 업로드용 정적 이미지는 채널 패키징 단계에서 HTML 정본으로부터 별도 렌더링하며, HTML 정본과 혼동하지 않는다.
