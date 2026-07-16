# output 폴더 안내

## 워크플로 5.3 편집 가능한 정본

`html/detail-page.html`, `html/styles.css`, `content-assets/`가 편집 가능한 하이브리드 상세페이지 정본입니다. 카피는 HTML 텍스트, 제품·연출 비주얼은 외부 이미지·GIF·영상으로 분리됩니다.

`planning/product-plan.json`과 `planning/content-plan.json`은 각각 사용자가 승인해야 하며 승인 기록은 `approvals/`에 현재 파일 해시와 함께 저장됩니다.

## 주요 폴더

| 경로 | 내용 | 최종 사용 여부 |
|---|---|---|
| `planning/` | 상품기획과 콘텐츠기획 | 정본 |
| `approvals/` | 현재 계획 해시에 묶인 사용자 승인 | 게이트 |
| `content-assets/` | 생성·촬영 이미지, GIF, 영상과 manifest | 사용 |
| `html/` | 편집 가능한 HTML·CSS와 패키지 manifest | 사용 |
| `qa/` | 소재별 QA와 조립 후 통합 QA | 게이트 |
| `images/` | 5.2 레거시 최종 10장 또는 채널 렌더링본 | 채널별 |
| `generated-pages/` | 글자가 없는 이미지 베이스 | 중간 작업용 |
| `typography-pages/` | 승인 카피를 적용한 타이포 편집본 | 검수·승인용 |
| `typography-prompts/` | 타이포 편집 지시문 | 작업 기록 |
| `browser-research/` | Browser Use 경쟁사·리뷰 조사 | 기획 근거 |
| `brand/` | 제품별 브랜드명 제안과 브랜드 시스템 | 브랜드 근거 |
| `copy/` | 페이지별 승인 카피 | 제작 근거 |

## 함께 볼 파일

- `qa/material-qa.json`: 각 콘텐츠 모듈의 자동·육안 QA
- `qa/integration-qa.json`: HTML 조립 후 전체 흐름·반응형·접근성·광고 QA
- `html/package-manifest.json`: 계획·자산·QA·HTML·CSS 해시 연결
- `qa-report.md`: 최종 검수 결과
- `photo-shot-list.md`: 실사진 교체 촬영안
- `gif-plan.md`: 동작 GIF 제작안
- `project-manifest.yaml`: 프로젝트 규격과 게이트 상태
- `planning/product-plan.json`: 고객·문제·포지셔닝·오퍼·승인 주장
- `planning/content-plan.json`: 장별 카피·근거·자산·QA 명세
- `reference-routing.json`: 제품 canonical source와 페이지별 참조 선택
- `ocr-report.json`: 기대 한글과 OCR 불일치 후보
- `regeneration-log.json`: 실패 페이지의 국소 수정 이력

> 수정 가능한 상세페이지를 찾을 때는 먼저 `output/html/detail-page.html`을 연다.
