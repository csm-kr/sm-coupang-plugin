# 입력 계약

## 최소 입력

- 하나 이상의 실제 제품 소스: `raw_capture` 또는 신뢰 가능한 `manufacturer_source`
- 하나의 도매·판매·공식 상품 URL 또는 사용자가 확인한 상품 정보

긴 레퍼런스와 기존 결과는 선택 입력이다. 사용자 레퍼런스가 없으면 스킬의 상업형 벤치마크를 광고 문법의 기본값으로 사용한다. 실제 제품 소스가 없으면 사용자의 명시적 `concept_only` 선택 전에는 제품 이미지를 생성하지 않는다. 상품 정보가 부족하면 확인되지 않은 기능·소재·수치·제조 정보는 카피에서 제외한다.

## 원본 상품 이미지 판정

먼저 모든 파일에 다음 제작 역할 하나를 지정한다.

- `PRODUCT_SOURCE`: 실제 판매·출고 SKU의 외형 기준
- `SUPPLIER_REFERENCE`: 공급처 설명·연출 참고. 실제 SKU와 일치하고 출처가 신뢰될 때만 별도 계보 검증 후 제품 근거 가능
- `COMPETITOR_REFERENCE`: 경쟁 구성·카피·정보 순서 조사 전용
- `STYLE_REFERENCE`: 색·레이아웃·분위기 참고 전용
- `GENERATED_DRAFT`: 수정 대상인 이전 생성본. 실제 제품 근거 금지
- `MEASUREMENT_EVIDENCE`: 자·저울·포장 표시·시험 문서 같은 수치 근거

제품의 실루엣·색·부품·로고·수량은 `PRODUCT_SOURCE`만 결정한다. 공급처·경쟁사·스타일·생성본을 섞어 하나의 제품을 만들지 않는다.

각 원본을 다음처럼 분류한다.

- `product_only`: 사람 얼굴·피부·손·팔·몸이 전혀 없는 제품 사진
- `contains_person`: 실제 사람의 일부라도 보이는 착용·사용 사진
- `document`: 라벨, 패키지, 설명서, 인증서, 상품 정보
- `unknown`: 역할이 불명확하거나 읽기 어려움

별도로 제품 소스 계보를 다음처럼 분류한다.

- `raw_capture`: 사용자가 직접 촬영한 실제 제품
- `manufacturer_source`: 제조사·공급처의 실제 제품 사진
- `generated_master`: AI로 다시 만든 제품 마스터
- `generated_scene`: AI 연출 장면

제품 동일성은 `raw_capture` 또는 신뢰 가능한 `manufacturer_source`로만 잠근다. `generated_master`와 `generated_scene`은 실제 구조 근거로 사용하지 않는다.

그리고 별도로 다음을 기록한다.

- `safe_for_imagegen`: 사람 픽셀이 없어 ImageGen 제품 근거로 넣을 수 있는가
- `safe_for_final_composite`: 사람 픽셀이 없는 제품 전용 이미지인가
- `reference_only`: 제품 구조 참고로만 볼 것인가
- `visible_facts`: 색, 개수, 실루엣, 개구부, 봉제, 라벨 위치 등 직접 확인되는 사실
- `not_verifiable`: 소재 혼용률, 기능, 성능, 제조 정보 등 사진만으로 확인할 수 없는 사실

`contains_person`은 항상 `safe_for_imagegen: false`, `safe_for_final_composite: false`다. 실제 사람의 일부라도 보이는 이미지는 제품 형태 참고를 포함해 ImageGen 입력에서 완전히 제외한다. 필요한 구조가 그 사진에만 보이면 사람 없는 제품 전용 사진을 추가 확보한 뒤 진행한다.

## 사람 사용 금지

다음 입력 역할을 만들지 않는다.

- `identity_seed`
- `real_model`
- `wearing_target`
- `edit_target`
- `preserve_edit`
- 실제 사람 누끼

큐에는 `product_only`이면서 `safe_for_imagegen: true`인 원본만 넣는다. 큐 생성 시 `--confirm-person-free`를 사용해 이 시각 판정을 명시적으로 잠근다.

새 워크플로 프로젝트에서는 `product-source-lineage.json`에 등록되어 있고 `trusted_for_identity: true`인 실제 소스만 제품 증거 입력으로 넣는다. `--confirm-actual-product-source`로 이 판정을 함께 잠근다.

## 제품 잠금

ImageGen 큐 전에 원본에서 가능한 범위의 역할을 고른다.

- `full_product`: 전체 실루엣과 구성
- `key_detail`: 개구부, 커프, 조절부, 연결부 등 핵심 구조
- `material`: 표면 결, 두께, 봉제
- `label`: 라벨의 위치와 외곽
- `components`: 수량과 구성품

모든 제품 포함 프롬프트에 동일한 `product-invariants.txt`를 그대로 반복한다. 1차 베이스의 라벨 문자를 정확히 재현할 수 없으면 읽히지 않게 한다. 사람 픽셀이 없는 실제 라벨만 조건부 ImageGen 편집의 참조로 사용할 수 있으며 로컬 타이포그래피 폴백은 금지한다.

## Canonical reference 라우팅

실제 제품 소스 중 서로 다른 면과 핵심 구조를 가장 잘 보여주는 3~5개를 `reference-routing.json`의 `canonical_sources`로 고른다. 각 페이지는 그 안에서 필요한 1~5개만 선택한다.

- 히어로: 전체 실루엣·정면·측면·실제 출고 형태
- 소재·마감: 매크로·측면·전체
- 사용·잠금: 사용 상태·열림/닫힘·방향 확인
- 밑창·옵션: 밑창 전체·좌우 방향·구성품

모든 페이지에 같은 입력 묶음을 기계적으로 넣지 않는다. 페이지가 요구하는 면을 보여 주지 못하거나 source ID가 계보에 없으면 큐 생성을 중단한다.

## 레퍼런스 사용

레퍼런스에서 가져올 수 있는 것은 다음뿐이다.

- 페이지 흐름
- 사진과 텍스트의 비율
- 조명, 팔레트, 배경
- 타이포그래피 위계
- 카드, 원형 확대, 모자이크 같은 레이아웃 방식
- 여백과 장면 전환 리듬

가져오지 않는 것은 얼굴, 정체성, 브랜드, 로고, 상품 외형, 라벨, 카피, 수치, 인증, 후기, 가격, 기능 주장이다.

긴 레퍼런스는 `hero`, `problem`, `product`, `feature`, `lifestyle`, `closing` 여섯 크롭으로 나눈다. 각 생성 작업에는 역할 크롭 하나만 사용한다.

## 첨부 순서

대화에서 사용자가 상품 원본을 먼저 넣고 긴 레퍼런스를 나중에 넣으면, 마지막의 긴 세로 이미지를 레퍼런스로 보고 이전 상품 이미지를 제품 근거로 사용한다. 파일 역할이 명확하면 추가 질문 없이 진행한다.
