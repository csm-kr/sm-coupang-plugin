# 조건 이미지 기반 타이포그래피 패스

## 목적

무문자 상세페이지 비주얼을 ChatGPT/ImageGen에 편집 대상으로 다시 넣어, 이미지의 피사체와 실제 여백을 읽은 타이포그래피를 생성한다. 카피의 사실성은 사전에 잠그고 시각적 의사결정만 모델에 맡긴다. 제작 순서는 `기획 → 배경 그리기 → 글자 추가`이며, 이 문서는 마지막 글자 추가 패스만 다룬다.

## 입력과 출력

- 입력: `output/generated-pages/PG-01.png`~`PG-10.png`
- 카피: `output/copy/overlay-copy.md`의 `headline`, `subcopy`, `badge`, 선택적 `card_*`
- 브랜드: `output/brand/brand-system.json`의 컬러 역할·폰트·컴포넌트·기억 장치·로고 정책
- 프롬프트: `output/typography-prompts/TY-01.md`~`TY-10.md`
- 승인 원본: `output/typography-pages/TY-01.png`~`TY-10.png`
- 최종 게시본: `output/images/01.png`~`10.png`

## 실행

1. `build_typography_prompts.py`로 정확히 10개 작업을 만든다.
2. 각 PG 이미지를 `view_image`로 확인한 뒤 built-in ImageGen의 편집 대상으로 한 장씩 입력한다.
3. 모델이 얼굴·손·제품·인셋·카드를 가리지 않는 위치를 선택하게 한다. 페이지의 세로 중심축, 카드 그리드와 안전 여백은 기획에서 잠그고, 세부 좌표와 줄바꿈만 조건 이미지에 맞게 정한다.
4. 헤드라인은 가장 크고 무거운 한글 Black, 보조 문구는 중간 크기, 배지·단계 번호는 작은 Bold로 구성한다. `emphasis` 구절 하나만 고채도 강조색으로 처리하고 중복 렌더링하지 않는다. 필요한 경우에만 대비가 강한 컬러 밴드, 아이보리 카드, 비교 마커 또는 단계 원을 추가한다.
5. `working_draft` 브랜드는 제품별 제안명을 문서에 남기되 이름·로고·슬로건을 이미지에 만들지 않고 승인된 시각 토큰과 목소리만 적용한다. `concept_only` 제품은 모든 장에 `연출용 콘셉트 이미지`를 읽히는 보조 라벨로 표시한다.
6. 출력에서 승인 문구를 글자 단위로 읽고 오탈자·누락·중복·추가 문자를 확인한다. `ocr-expectations.json`을 기준으로 `extract_ocr.py`를 실행하되 OCR 결과를 정답으로 간주하지 않는다.
7. 원본과 비교해 인물 정체성, 얼굴, 손가락, 제품 수량, 실루엣, 개구부, 잠금부, 절개, 밑창, 라벨 위치, 패널 구도와 조명이 유지됐는지 확인한다.
8. 실패하면 한 번에 한 문제만 지적해 같은 TY 작업의 해당 텍스트 영역만 ImageGen으로 편집하고 `regeneration-log.json`에 남긴다. 최초 TY 결과 이후 한글 부분 편집을 총 3회까지 허용하며 승인 전 결과를 최종 경로에 두지 않는다.
9. 승인본을 매니페스트의 정확한 캔버스에 맞춰 `output/images`에 게시한다. 워크플로 5.2는 10장 모두 정확히 `800×2400px`다. 높이가 맞지 않으면 승인 TY와 합성 보조 배경을 `compose_fixed_canvas.py`로 조립한다. 어떤 경우에도 타이포그래피를 다시 그리거나 재조판하지 않는다.

## 얼라인과 중앙정렬

- 한 페이지에서 헤드라인·서브카피·배지가 중앙정렬이면 세 요소의 광학 중심을 같은 세로축에 둔다.
- 최종 800px 기준 중앙축 오차는 16px 이내를 목표로 한다.
- 2열 비교는 두 열 폭과 거터를 동일하게 하고, 2×2·2×3 카드는 폭·높이·간격·모서리 반경을 반복한다.
- 카드 문장이 좌측 정렬이어도 문장 블록의 바운딩 박스는 카드의 광학 중심에 둔다.
- 같은 역할의 카드 문구는 폰트 크기, 굵기, 행간, 시작 높이, 내부 여백을 통일한다.
- 정보표의 각 행은 `라벨 열 / 구분점 열 / 값 열`을 고정한다. 모든 값은 동일한 x축에서 시작하고 두 줄 값의 둘째 줄도 같은 값 열에 행걸이 정렬한다. 최종 800px에서 반복 열의 시작축 편차가 8px을 넘으면 실패다.
- 줄바꿈은 의미 단위로 하고, 왼쪽과 오른쪽 행 길이가 지나치게 달라지지 않게 균형을 맞춘다.
- 글자 블록과 얼굴·손·제품 사이에는 명확한 안전 여백을 둔다.
- 열 장을 모두 중앙정렬하지 않는다. `headline_alignment`를 잠그고 비교·단계·정보 페이지는 좌측축 또는 카드축을 우선한다.

## 상업형 크기와 대비

- 최종 800px 기준 히어로 헤드라인은 74~94px, 섹션 헤드라인은 60~78px, 본문은 26~34px, 캡션·칩은 19~25px를 목표로 한다.
- 한글 헤드라인은 ExtraBold/Black, 행간 0.96~1.08, 2~3줄 이내로 조판한다. 본문과 크기 차이가 약한 조판은 실패다.
- 헤드라인은 1~2줄을 우선하고 3줄을 넘지 않는다. 폭이 안정적인 한글 산세리프를 사용하며 세로로 늘어나거나 지나치게 좁은 글리프는 실패다. 짧은 둘째 줄만 과도하게 키우지 말고 제목 전체를 폭이 높이보다 충분히 큰 상업형 덩어리로 유지한다.
- 제목의 정확한 `emphasis` 구절만 강조색으로 바꾼다. 전체 제목을 같은 파란색으로 칠하거나 강조 구절을 별도 문장으로 반복하지 않는다.
- 화이트 면은 딥 네이비·차콜, 고채도 컬러 면은 흰색을 우선한다. 파스텔 면 위 연회색 본문처럼 명도 대비가 약한 조합은 금지한다.
- 카드·단계·비교 페이지는 굵은 숫자, 짧은 라벨, 제목, 설명의 시작선과 내부 여백을 반복한다.
- 영문 배지는 정보가 있을 때만 사용한다. 장식용 `DAILY`, `SUMMARY`, `DETAIL`을 모든 페이지에 반복하지 않는다.

## 공통 편집 프롬프트

```text
Use case: ads-marketing
Asset type: Korean Coupang mobile detail-page panel
Input image: Image 1 is the only edit target and visual condition.
Primary request: add only the exact approved typography to Image 1. First inspect the real negative space, product evidence, and subject hierarchy, then choose the most persuasive commercial placement, line breaks, scale, alignment, and contrast. Follow the locked headline_alignment. Center-aligned blocks must share one optical axis; comparison, step, and information modules must use identical card margins and baseline logic.
Text (verbatim): render every supplied string exactly once with no changes and no extra characters.
Typography: conversion-focused Korean ecommerce art direction; ExtraBold/Black Korean headline with tight 0.96~1.08 line spacing, a clearly smaller clean subcopy, compact Bold labels and step numbers. Render only the supplied emphasis substring in one high-contrast accent color without duplicating it. Use strong navy/white/brand-accent contrast rather than pale editorial styling.
Constraints: preserve every person, face, hand, finger, product, seam, opening, label, panel, crop, background, lighting, color grade, and composition. Add only typography and minimal flat support shapes. Do not regenerate or restyle the photograph.
Avoid: covering the face, hands, product, insets, or information cards; misspelled Hangul; extra copy; price; discount; certification; logo; watermark.
```

## 합격 기준

- `text_accuracy: pass`: 모든 승인 문구가 정확히 한 번씩 보인다.
- `base_preservation: pass`: 비주얼 베이스의 의미 있는 픽셀이 바뀌지 않았다.
- `product_fidelity: pass`: 상품 구조가 유지됐다.
- `source_person_pixels: none`: 실제 인물 입력을 추가하지 않았다.
- `render_mode: imagegen_conditioned`: 로컬 재조판 없이 모델이 타이포그래피를 통합했다.
- `commercial_hierarchy: pass`: 헤드라인·강조 구절·본문·라벨의 크기와 대비가 즉시 구분된다.
- `commercial_flow_support: pass`: 조판이 해당 페이지의 훅·비교·증거·단계·정보 역할을 강화한다.
- `alignment_consistency: pass`: 반복 카드와 정보표의 외곽선·라벨 열·구분점 열·값 열·행걸이 정렬이 일치한다.
- `headline_compactness: pass`: 헤드라인이 1~3줄 안에서 폭이 안정적이고, 세로로 늘어난 글리프나 과도하게 높은 제목 덩어리가 없다.

로컬 타이포그래피 폴백, 외부 폰트 조판, 텍스트 오버레이 합성은 사용하지 않는다. 세 번의 한글 부분 편집 후에도 정확한 문구·정렬을 얻지 못하면 해당 페이지를 `BLOCKED_TEXT`로 기록하고 무문자 베이스·정확 문구·실패 이력을 제공한다. 그 페이지는 최종 게시본으로 승인하지 않는다. 제품 구조나 전체 비주얼 보존이 실패하면 텍스트로 덮지 말고 제품·레이아웃 게이트로 회귀한다.
