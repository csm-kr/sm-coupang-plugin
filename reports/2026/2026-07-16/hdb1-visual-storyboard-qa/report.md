# HDB-1 `숨트임` 시각 스토리보드·수치형 QA 개선 보고

- 실행일: 2026-07-16
- 상태: `CONCEPT_PROTOTYPE_PASS_NOT_PROMOTABLE`
- 목적: 상세페이지의 주장-이미지 연관성, 커버 범위, 이미지 크롭, 모듈 순서와 한글 줄바꿈을 감이 아닌 수치로 검증
- 실제 제품 동일성: `BLOCKED_IDENTITY_ASSETS`

## 결과

| 항목 | 결과 | 내부 AC |
|---|---:|---:|
| 스토리보드 모듈 | 10개 | 10개 |
| 주장-근거 연결 | 100% | 100% |
| 핵심 주장 직접 시각화 | 100% | 100% |
| 모듈 순서 일치 | 100% | 100% |
| 주장-자산 연결 | 100% | 100% |
| 주 피사체·핵심 영역 크롭 통과 | 100% | 95% 이상·100% |
| 주장-이미지 연관성 | 평균 92.1/100, 실패 0개 | 모듈별 80/100 이상 |
| 한글 타이포 | 360px·800px, 80개 요소, 오류 0·경고 0 | 오류·strict 경고 0건 |
| 합성 모델 장면 | 2개 | 1~2개 |

첫 브라우저 측정에서는 03장 주 피사체 가시율 80%, 핵심 영역 78.2%, 10장 핵심 영역 99.1%, 800px 히어로 제목 4행이 검출됐다. 임계값을 낮추지 않고 이미지 `object-fit`, 히어로 그리드·패딩·제목 크기를 수정한 뒤 같은 360x900·800x1000 조건으로 재측정해 모두 통과했다.

## 산출물

- [편집 가능한 HTML](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/html/detail-page.html)
- [시각 스토리보드](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/planning/visual-storyboard.json)
- [분리된 실험 계획](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/experiment-plan.json)
- [자산 manifest](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/content-assets/manifest.json)
- [스토리보드 QA](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/visual-storyboard-qa.json)
- [시각 좌표 QA](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/visual-layout-qa.json)
- [주장-이미지 육안 QA](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/claim-visual-qa.json)
- [한글 타이포 QA](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/typography-qa.json)
- [360·800px 모듈 캡처](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/visual-layout-screenshots/)

## 해석과 제한

앞 2개 모듈은 마네킹 대신 합성 성인 모델을 사용해 눈 아래 상단선, 입·코 타공, 귀 주변, 목 하단의 착용 범위를 직접 보여준다. 07장은 A=25cm와 D=28.5cm 기준선을 HTML/SVG로 분리해 숫자가 바뀌어도 이미지 재생성 없이 수정할 수 있다. GIF는 전체 형태에서 호흡부 타공으로 초점을 이동하며 성능 수치를 주장하지 않는다.

생성 모델과 가상 제품은 실제 HDB-1 사진·핏·치수·성능 근거가 아니다. 공급처 시험 문서도 실제 출고 SKU와 시험 시료의 매핑이 끝나지 않았다. 따라서 이번 통과는 스토리보드·레이아웃·편집성·QA 방식의 통과이며 판매용 승격을 허용하지 않는다.

## 다음 게이트

1. 실제 HDB-1 단독 정·후·좌우·펼침·타공·4색·라벨·포장 사진과 A~E 실측 기준점을 확보한다.
2. 1차 계획의 호흡 보행·착용 압박·흘러내림·치수·색상 간이 실험을 수행하고 결과를 사실 원장에 연결한다.
3. 합성 모델·가상 마스터를 실제 SKU 자산으로 교체한 뒤 소재 QA와 통합 QA를 모두 다시 실행한다.
4. 캠페인 14일 내 판매 2개 이상과 ROAS 400% 이상을 함께 충족하면 2차 검사서·후기·다수 샘플 검증으로 승격한다.
