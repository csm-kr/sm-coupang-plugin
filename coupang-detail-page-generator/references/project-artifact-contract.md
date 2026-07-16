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
    │   └── content-plan.json
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
    ├── content-assets/
    │   ├── manifest.json
    │   └── 이미지·GIF·영상
    ├── html/
    │   ├── detail-page.html
    │   ├── styles.css
    │   └── package-manifest.json
    ├── qa/
    │   ├── material-qa.json
    │   └── integration-qa.json
    ├── images/01.png ... 10.png  # 5.2 레거시 정적 납품본
    ├── photo-shot-list.md
    ├── gif-plan.md
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
- 상품기획과 콘텐츠기획을 별도 JSON으로 기록하고, 각각 현재 파일 해시에 묶인 사용자 승인만 인정한다.
- 콘텐츠 모듈마다 구매 질문, 원장 ID, 참조 source ID, 장면, 금지 요소와 QA 기준을 둔다.
- OCR 기대문구와 불일치 후보, 제품·레이아웃 최대 2회, 한글 영역 최대 3회의 국소 수정 이력을 분리해 기록한다. 로컬 타이포그래피 폴백은 허용하지 않는다.
- 게이트 상태와 정반합 결정 로그를 남긴다.

## 완료 상태

- `draft`: 자동 템플릿만 존재
- `researched`: 제품·시장 근거가 잠김
- `product_plan_approved`: 상품기획의 현재 해시를 사용자가 승인함
- `content_plan_approved`: 승인된 상품기획을 참조하는 콘텐츠기획의 현재 해시를 사용자가 승인함
- `produced`: 실제 소스와의 제품 보존 시험 및 소재별 자동·육안 QA를 통과함
- `assembled`: 승인 소재가 HTML·CSS로 조립됨
- `completed`: 통합 자동·육안 QA가 현재 패키지 해시에 대해 통과함

파일이 존재한다는 이유만으로 상태를 올리지 않는다. 각 게이트의 필수 내용과 검증 결과를 함께 확인한다.

## 버전 호환

`project-manifest.yaml`이 없는 기존 프로젝트는 레거시 검증 경로를 사용한다. 5.0·5.1·5.2 프로젝트의 정적 이미지·타이포그래피 계약은 보존한다. 5.3 새 프로젝트는 분리된 두 계획, 사용자 승인 해시, 외부 콘텐츠 자산, 소재 QA, HTML 패키지와 통합 QA를 포함한다.

5.3의 편집 가능한 정본은 `output/html/detail-page.html`, `styles.css`, `content-assets/`다. 쿠팡 업로드용 정적 이미지는 채널 패키징 단계에서 이 정본으로부터 별도 렌더링하며, HTML 정본과 혼동하지 않는다.
