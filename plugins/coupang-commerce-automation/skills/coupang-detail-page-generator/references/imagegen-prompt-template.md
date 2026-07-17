# ImageGen 프롬프트 템플릿

워크플로 5.3 이상은 승인된 `visual-storyboard.json`에서 생성 자산만 실행한다. ImageGen은 무문자 비주얼을 만들고, 카피·수치·치수선·표·배지는 HTML/SVG로 조립한다. 5.2 이하 레거시 프로젝트의 이미지 내 타이포 편집은 기존 매니페스트가 명시한 경우에만 유지한다.

## 공통 구조

```text
Use case: ads-marketing
Asset type: <모듈 ID와 상세페이지 안의 역할>
Primary request: <한 문장 작업>
Subject: <제품·합성 모델·보조 장면>
Scene/backdrop: <환경과 접지면>
Composition: <카메라, 프레이밍, 피사체 위치, 모바일·800px 안전 크롭>
Claim link: <이 이미지가 직접 보여 줄 승인 주장>
Required visual cues: <같은 프레임에서 실제로 보여야 할 구조·행동·결과>
Measurement guidance: <제품 전체, 측정 기준점용 여백, 잠긴 비율; 숫자 생성 금지>
Lighting/mood: <브랜드 사진 원칙>
Input images: <각 이미지의 역할과 source ID; 실제 사람 포함 이미지는 제외>
Constraints: <제품·인물·문자·계보 불변 조건>
Avoid: <잘림·추가 부품·무관 소품·워터마크·반복 구도>
```

`Claim link`와 `Required visual cues`가 없으면 생성하지 않는다. 프롬프트의 장면이 예쁘더라도 주장과 같은 프레임에서 확인할 시각 단서가 없으면 소재 QA 실패다.

## 공통 안전 블록

```text
All visible people, faces, skin, arms, hands, bodies, poses, and identities must be newly synthesized pixels.
Do not edit, preserve, trace, composite, or reproduce any real person from any input.
Every product input must be verified to contain no person pixels.
For a verified SKU, use only registered raw_capture or trusted manufacturer_source inputs as identity evidence.
Never use generated_master or generated_scene to establish actual product structure.
Generate no Korean or English text, letters, numbers, logos, readable labels, prices, certifications, measurement labels, or watermarks.
Preserve the full product subject and every storyboard critical region inside the safe crop for both 360px and 800px layouts.
```

공통 블록을 줄이거나 실제 인물 보존 표현으로 바꾸지 않는다.

## 합성 모델 장면

착용형 상품은 기본 1장, 최대 2장만 허용한다.

```text
Create one entirely fictional adult Korean campaign model from text.
Show the human scale and exact intended wearing area without glamour retouching.
Keep the product, upper edge, lower edge, fastening area, and every critical region fully visible.
Use a chest-up or waist-up composition with enough negative space for native HTML copy.
This model scene is usage context, not proof of product performance.
```

실제 SKU 제품 단독 소스가 없으면 모델이 착용한 제품도 `concept_only`다. 실제 길이·압박·호흡 성능·커버율 증거로 쓰지 않는다.

## 커버 범위·치수 장면

1. `measurement_anchors`의 시작점·끝점·단위·검증 상태를 먼저 확인한다.
2. 기준점이 `anchor_definition_pending`이면 실제 치수선 증거 생성을 중단한다.
3. ImageGen에는 제품 전체와 기준점 주변이 보이는 무문자 베이스만 요청한다.
4. 숫자·A~E 라벨·치수선은 정확한 HTML/SVG로 조립한다.
5. 피사체 bbox 95%, 각 기준점·타공·귀 구멍·목 끝단 critical bbox 100% 가시율을 목표로 한다.

```text
Measurement guidance: keep the entire product silhouette visible with generous space around the top, bottom, both ear openings, perforated zone, and lower neck edge. Preserve the locked product proportions from the verified product-only references. Do not draw measurement lines, letters, numbers, rulers, or labels. Leave a clean surrounding field for later native HTML/SVG measurement overlays.
```

## 제품 형태 잠금

`product-invariants.txt`와 해당 모듈의 canonical source ID만 사용한다.

- 전체 실루엣과 실제 비율
- 구성 수량과 옵션 색상
- 상단선·하단선·귀 구멍·조절부·연결부
- 타공 위치·수량·분포
- 봉제·절개·라벨 위치
- 추가하면 안 되는 부품·홀·장식

하나라도 실제 소스에서 확인할 수 없으면 생성 반복 대신 촬영 게이트로 돌아간다.

## 페이지별 증거 구도

- 히어로: 실제 크기 맥락의 합성 모델 또는 큰 제품, 핵심 제품과 사용 위치를 1초 안에 인지
- 선택 기준: 커버 상·하단과 호흡부 타공처럼 두 판단 기준을 같은 프레임 또는 명확한 두 패널로 연결
- 증거 개요: 시험·구조·실측 자산을 서로 다른 원천으로 구분
- 시험 문서: 원본 보존, AI 재생성 금지
- 구조 매크로: 주장하는 타공·봉제·결합부가 화면의 주인공
- 핏: 실제 제품 합성 전에는 콘셉트, 압박·흘러내림 단정 금지
- 치수: 전체 제품과 측정 기준점이 모두 보이는 `contain` 우선
- 옵션: 실제 4색 동일 조명·동일 구도 우선
- 정보: 검증된 제품 단독 이미지와 HTML 사양표
- 클로징: 앞 장과 다른 구도에서 승인된 세 근거를 회수

## 생성 직후 판정

1. 실제 인물 픽셀이 입력·결과에 없는지 확인한다.
2. 제품 불변 특성과 source lineage를 비교한다.
3. `required_visual_cues`가 실제 화면에 보이는지 확인한다.
4. 피사체·critical bbox가 360px·800px 안전 크롭 안에 들어가는지 확인한다.
5. 생성 문자·숫자·로고·워터마크가 없는지 확인한다.
6. 주장-이미지 연관성 점수를 0·25·50·75·100 루브릭으로 기록하고 80점 미만이면 자산을 교체한다.
7. 실패 원인과 수정 범위를 `regeneration-log.json`에 남긴다.
