# ImageGen 프롬프트 템플릿

`output/imagegen-queue.json`의 `PG-01`~`PG-10`을 실행한다. 모든 작업은 최종 페이지의 무문자 비주얼 베이스 한 장을 만든다. 승인 후에는 [conditional-typography-pass.md](conditional-typography-pass.md)에 따라 각 베이스를 조건 이미지로 다시 입력해 정확한 카피를 생성한다.

## 공통 안전 블록

```text
All visible people, faces, skin, arms, hands, bodies, poses, and identities must be newly synthesized pixels.
Do not edit, preserve, trace, composite, or reproduce any real person from any input.
Do not resemble the person in the product evidence or the art-direction reference.
Every product input has been visually verified to contain no person pixels. Use product inputs only as construction evidence and the style crop only for composition, lighting, palette, spacing, scene density, and visual rhythm.
For a verified SKU, use only registered raw_capture or trusted manufacturer_source inputs as identity evidence. Never use generated_master or generated_scene to establish actual product structure.
Generate no Korean or English text, letters, numbers, logos, readable labels, badges, icons, prices, certifications, or watermarks.
Use conversion-focused Korean mobile-commerce art direction with one dominant product or evidence visual, high-contrast section breaks, and blank modules prepared for bold typography, comparison, detail, step, or specification content. Avoid quiet editorial layouts and unfinished blank bottoms.
```

공통 블록을 줄이거나 실제 인물 보존 표현으로 바꾸지 않는다.

## PG-01 합성 모델 기준

```text
Create one entirely fictional adult Korean campaign model from text. Use a natural short dark bob, neutral makeup, understated cream-and-pale-blue wardrobe, bright window daylight, and calm premium ecommerce styling. The model is not based on any input person and becomes the only identity anchor for later pages.
```

실제 착용 사진을 identity seed로 넣지 않는다. 레퍼런스 인물 얼굴도 참고하지 않는다.

## 얼굴이 보이는 추가 인물 페이지

```text
Input image 1 is PG-01, a fully synthetic campaign model anchor. Use it only when another face-visible person is indispensable. Match only this fictional identity, but create a completely different pose, camera angle, crop, and action. Do not repeat the hero walk or full-body composition. Do not preserve or imitate any person from product evidence or the style reference.
```

## 기능 증거 우선 페이지

PG-02·03·04·05·06·08·09·10에는 사람 없는 제품 증거를 우선하고 다음을 추가한다.

```text
Include no person, face, skin, hand, arm, or body. Create a people-free product still life or macro scene.
```

사용 순서처럼 손·발이 꼭 필요하면 얼굴 없는 합성 클로즈업만 생성한다. 실제 사람 입력은 사용하지 않고 PG-01의 전신 포즈를 반복하지 않는다.

## 제품 형태 잠금

`product-invariants.txt`를 모든 10개 프롬프트에 그대로 반복한다. 상품마다 최소 다음을 구체화한다.

- 전체 실루엣
- 수량과 구성품
- 색상
- 개구부·커프·조절부·연결부
- 소재 표면의 보이는 특징
- 봉제 위치와 방향
- 라벨 위치와 외곽
- 추가하면 안 되는 부품·장식·홀

실제 소스와 다음을 함께 잠근다: 전체 비율, 앞코·입구, 스트랩 수·위치·폭·길이, 잠금부, 절개·봉제·몰딩, 밑창 형태·무늬·돌기, 각인·라벨·로고 위치, 색·투명도, 구성과 결합 방식. 하나라도 확인할 수 없으면 프롬프트를 만들지 말고 촬영 게이트로 돌아간다.

모든 프롬프트에 `brand-system.json`의 핵심 컬러 역할·사진 원칙·컴포넌트·기억 장치·캠페인 상수만 짧게 반복한다. `working_draft`는 브랜드 이름·로고·슬로건을 생성하지 않는다.

`reference-routing.json`에서 해당 페이지에 선택된 source ID만 입력한다. 제품마다 잠긴 3~5개 canonical source를 기반으로 하되, 히어로·소재·사용·밑창 페이지가 보존해야 할 면에 맞춰 1~5개를 선택한다. 모든 페이지에 같은 입력 묶음을 반복하지 않는다.

1차 생성 라벨 문자를 정확히 만들 수 없으면 읽히지 않게 한다. 사람 없는 실제 라벨 원본만 조건부 ImageGen 편집의 참조로 사용할 수 있다. 로컬 타이포그래피 폴백이나 외부 문자 합성은 사용하지 않는다.

## 페이지별 구도

- PG-01: 질문·상황·상품이 함께 보이는 강한 훅, 상단 20% 안팎의 큰 제목 영역
- PG-02: 사람 없는 큰 제품 전체·구성, 빈 사실 칩 2~3개
- PG-03: 고객 상황을 만드는 실제 접촉과 제품 반응의 큰 매크로. 카피가 물·열·먼지·압력 등을 말하면 실제 제품 표면에서 그 접촉이 보여야 함
- PG-04: 큰 전체 실루엣과 결합·잠금·조절 구조의 서로 다른 원형 확대 2~3개
- PG-05: 굽힘·말림·펼침·개폐처럼 검증된 변형을 한 제품의 연속 상태로 보여 주는 기능 증거
- PG-06: 보관·휴대·관리 또는 소재 표면의 서로 다른 증거를 제품 중심으로 제시
- PG-07: 2~3단계 사용 순서 또는 한 장의 명확한 사용 시연
- PG-08: 사람 얼굴을 반복하지 않는 서로 다른 사용 상황의 비대칭 모자이크. 각 모듈에 제품이 크게 보여야 함
- PG-09: 큰 제품과 빈 스펙·색상·사이즈·고지 카드, 카드 안 문자는 없음
- PG-10: 사람 없는 제품 중심 클로징, 큰 제품과 실제 기능 증거 3종을 한 화면에서 회수

## 즉시 판정

1. 인물 페이지가 PG-01의 합성 모델과 일치하는지 확인한다.
2. 실제 원본 인물의 얼굴·신체·포즈 또는 피부 픽셀이 남지 않았는지 확인한다.
3. 실루엣, 개수, 색, 개구부, 봉제, 라벨 위치, 소재 표현을 원본과 비교한다.
4. 생성 문자, 이상한 로고, 워터마크, 기형 손·손가락을 확인한다.
5. 실패하면 같은 작업 ID로 재생성하고 실패 시도는 최종 경로에 두지 않는다.
6. 여러 페이지와 사용 단계에서 스트랩·잠금·절개·밑창이 달라지면 재생성을 반복하지 않고 동일성 게이트로 회귀한다.
7. `product-source-lineage.json`에 각 결과의 실제 소스 ID와 동일성 판정을 기록한다.
