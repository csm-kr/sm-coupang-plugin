---
name: coupang-content-studio
description: 승인된 제품기획을 구매 서사와 콘텐츠기획으로 바꾸고, 주장-근거-이미지 스토리보드와 수치형 Acceptance Criteria를 잠근 뒤 ImageGen 무문자 자산, 실사진, GIF·영상, 편집 가능한 HTML을 제작한다. 상세페이지 콘텐츠기획, 모델 장면, 커버 범위·치수 이미지, 이미지 프롬프트, 크롭·순서 개선, 모션 또는 HTML 조립이 필요할 때 사용한다.
---

# 쿠팡 콘텐츠 스튜디오

이미지를 먼저 만들지 않는다. 각 모듈의 주장과 실제로 보여야 할 시각 단서를 잠근 뒤 자산을 만든다.

## 작업 순서

1. 승인된 `product-plan.json`에서 핵심 주장·근거·금지 표현을 읽는다.
2. `content-plan.json`에 구매 질문, HTML 카피, 주장·근거 ID, 모듈 순서를 기록하고 사용자 승인을 받는다.
3. `visual-storyboard.json`에 장별 `visual_thesis`, 필수 시각 단서, 모델 정책, 샷·크롭, 치수 기준점, 자산 ID와 수치형 AC를 기록한다.
4. `$imagegen`을 사용해 무문자 비트맵을 만든다. 실제 사람 픽셀을 입력하지 않고 필요한 인물은 텍스트에서 새로 만든 성인 합성 모델만 사용한다.
5. 이미지·GIF·영상마다 소재 QA를 통과시킨다.
6. 승인 카피는 네이티브 HTML로, 시각 자산은 외부 파일로 조립한다.
7. 완성 HTML과 별도로 `experiment-plan.json`을 만들어 실물 촬영·간이 실험·교체 자산·성공 기준을 남긴다.

## 모델·치수 이미지

- 착용형 상품은 실제 크기 맥락을 위한 합성 모델 장면을 기본 1장, 최대 2장 둔다.
- 모델 장면은 사용 맥락이며 실제 SKU 성능 증거가 아니다. 실제 제품 픽셀 합성 전에는 `concept_only`로 고지한다.
- A~E 치수는 값만 적지 말고 시작점·끝점·단위·허용 오차 상태를 잠근다.
- ImageGen에는 숫자·치수선을 만들게 하지 않는다. 제품 전체와 기준점이 잘리지 않는 무문자 베이스를 만들고 정확한 값·선은 HTML/SVG로 조립한다.
- 측정 기준점이 불명확하면 이미지를 생성하지 말고 `anchor_definition_pending`으로 차단한다.

## ImageGen 프롬프트

모든 생성 자산에 `use_case`, `asset_type`, `primary_request`, `subject`, `composition`, `claim_link`, `measurement_guidance`, `constraints`, `avoid`를 넣는다. 상품 전체·핵심 부위의 정규화 bbox와 모바일·800px 크롭 목표도 스토리보드에 기록한다.

## Acceptance Criteria

- 주장-근거 연결 모듈 비율: 100%
- 핵심 주장 직접 시각화 비율: 100%
- 장별 주장-이미지 연관성 육안 점수: 80/100 이상
- 피사체 bbox 가시율: 95% 이상
- 핵심 부위 bbox 가시율: 100%
- 360px·800px 모듈 순서 일치율: 100%
- 착용형 상품 합성 모델 장면: 1~2개
- 같은 이미지의 단순 크롭 재사용: 0건

세부 스키마와 명령은 `$coupang-detail-page-generator`의 `references/visual-storyboard-and-ac.md`를 읽고 따른다. 기존 5.3 프로젝트는 해당 호환 스킬의 스크립트를 사용한다.
