# 주장 중심 비주얼 스토리보드와 수치형 AC

## 목적

HTML 카피와 이미지가 같은 모듈에 있다는 이유만으로 관련 있다고 판정하지 않는다. 생성 전에 `무슨 주장을 하는가 → 화면에서 무엇이 보여야 하는가 → 어떤 근거와 자산을 쓰는가 → 어느 정도 보여야 통과인가`를 스토리보드로 잠그고, 조립 뒤 실제 브라우저 좌표로 순서와 크롭을 다시 검증한다.

## 연구에서 가져온 원칙과 내부 기준

- Baymard의 제품 상세 연구는 제품 이미지가 스케일·특징·사용 맥락을 전달해야 하며, 적어도 하나의 실제 크기 맥락 이미지가 필요하다고 설명한다. 이를 착용형 상품의 합성 모델 1~2장과 `in-scale` 장면 요구로 번역한다. [Product Page UX Research](https://baymard.com/research/product-page), [In Scale Product Images](https://baymard.com/blog/in-scale-product-images)
- Google Merchant Center는 판매하는 실제 제품과 옵션을 정확히 보여주고 제품 전체가 보이도록 요구한다. 이를 제품 동일성 잠금, 피사체 bbox 95%, 핵심 부위 bbox 100% 가시율로 번역한다. [Google Merchant image guidelines](https://support.google.com/merchants/answer/6324350?hl=en)
- W3C는 순서를 바꾸면 의미가 달라지는 콘텐츠는 의미 있는 순서를 보존해야 한다고 설명한다. 이를 승인 스토리보드와 DOM 모듈 순서 100% 일치로 번역한다. [WCAG Meaningful Sequence](https://www.w3.org/WAI/WCAG21/Understanding/meaningful-sequence.html)
- web.dev는 이미지의 `width`·`height`로 로딩 전 공간을 확보해 레이아웃 이동을 줄이도록 안내한다. 이를 모든 이미지의 고유 크기 선언과 조립 후 레이아웃 안정성 검수로 번역한다. [Optimize CLS](https://web.dev/articles/optimize-cls)

80점·95%·100% 컷오프는 위 자료에 직접 제시된 업계 성과 수치가 아니라, 이 저장소가 반복 제작을 같은 기준으로 비교하기 위해 정한 내부 Acceptance Criteria다.

## 필수 산출물

- `output/planning/visual-storyboard.json`
- `output/qa/visual-storyboard-qa.json`
- `output/qa/visual-layout-metrics.json`
- `output/qa/visual-layout-qa.json`
- `output/qa/visual-layout-screenshots/`
- `output/experiment-plan.json`

완성 HTML과 실험 계획은 별도 산출물이다. HTML은 현재 확인된 범위의 구매 서사를 완성하고, 실험 계획은 실제 SKU에서 확인해야 할 주장·촬영·교체 자산·성공 기준을 기록한다.

## 스토리보드 필드

각 모듈은 다음을 가진다.

- `commercial_job`: 구매 흐름에서 하는 일
- `claim_ids`, `evidence_ids`, `asset_ids`: 주장·근거·자산 연결
- `claim_visual_role`: `direct`, `supporting`, `context`
- `visual_thesis`: 한 문장으로 설명한 화면의 증명 방식
- `required_visual_cues`: 화면에서 실제로 확인할 대상
- `model_policy`: `none` 또는 `synthetic_adult`
- `layout.mobile`, `layout.wide`: 카피·미디어 순서와 위치
- `asset_frames[].subject_bbox`: 0~1 정규화 피사체 범위
- `asset_frames[].critical_regions`: 얼굴선·목 끝단·타공·측정점처럼 절대 잘리면 안 되는 범위
- `qa.claim_visual_relevance_min`: 장별 최소 육안 점수
- `imagegen_prompt`: ImageGen을 사용하는 자산의 구조화 프롬프트

치수 상품은 `measurement_anchors`에 값뿐 아니라 시작점·끝점·단위·검증 상태를 둔다. 공급처 명칭만 있고 기준점이 불명확하면 `anchor_definition_pending`이며 실제 치수선 증거로 승격하지 않는다.

## ImageGen 프롬프트 계약

각 생성 자산에 다음 필드를 사용한다.

```text
Use case: <ads-marketing | product-mockup | photorealistic-natural>
Asset type: <상세페이지에서 쓰일 정확한 위치>
Primary request: <한 문장 작업>
Subject: <합성 모델·제품·보조 장면>
Composition: <프레이밍, 카메라, 여백, 모바일 크롭>
Claim link: <이 이미지가 직접 보여 줄 주장>
Measurement guidance: <제품 전체·기준점·비율; 숫자 생성 금지>
Constraints: <제품·인물·문자·계보 불변 조건>
Avoid: <잘림·추가 부품·무관 소품·워터마크>
```

- 실제 사람이 포함된 이미지를 ImageGen 입력으로 사용하지 않는다.
- 필요한 인물은 텍스트에서 새로 만든 성인 합성 모델만 사용한다.
- 제품 동일성은 실제 제품 단독 소스가 있을 때만 증명한다. 없으면 `concept_only`로 고지한다.
- 숫자·치수선·한글 카피를 생성 이미지에 굽지 않는다. 무문자 베이스와 정확한 HTML/SVG 레이어를 결합한다.
- A~E 실제 비율은 입력 제품 소스와 측정 기준점이 잠긴 경우에만 프롬프트 제약으로 사용한다.

## 주장-이미지 연관성 점수

| 점수 | 기준 |
|---:|---|
| 0 | 주장과 무관한 장식 이미지 |
| 25 | 카테고리나 사용 맥락만 비슷함 |
| 50 | 주장을 암시하지만 핵심 구조·행동이 보이지 않음 |
| 75 | 직접 관련되나 중요한 부위가 작거나 모호함 |
| 100 | 주장한 구조·행동·결과가 같은 프레임에서 명확함 |

모든 모듈은 80점 이상이어야 한다. 자동 이미지 유사도만으로 이 점수를 만들지 않고, 검수자가 `required_visual_cues`를 직접 확인해 기록한다.

## 기본 Acceptance Criteria

| 지표 | 기준 |
|---|---:|
| 주장-근거 연결 모듈 비율 | 100% |
| 핵심 주장 직접 시각화 비율 | 100% |
| 장별 주장-이미지 연관성 | 80/100 이상 |
| 피사체 bbox 가시율 | 95% 이상 |
| 핵심 부위 bbox 가시율 | 100% |
| 승인 모듈과 DOM 순서 일치 | 100% |
| claim ID와 asset ID 렌더 연결 | 100% |
| 착용형 상품 합성 모델 장면 | 1~2장 |
| 단순 크롭 재사용 | 0건 |
| 360px·800px 필수 viewport | 모두 존재 |

## 검증 명령

```powershell
python <skill-dir>/scripts/validate_visual_storyboard.py `
  --storyboard <project-root>/output/planning/visual-storyboard.json `
  --report <project-root>/output/qa/visual-storyboard-qa.json `
  --strict

node <skill-dir>/scripts/collect_visual_layout_metrics.mjs `
  --cdp http://127.0.0.1:9225 `
  --url http://127.0.0.1:8765/html/detail-page.html `
  --storyboard <project-root>/output/planning/visual-storyboard.json `
  --viewports 360x900,800x1000 `
  --screenshots <project-root>/output/qa/visual-layout-screenshots `
  --output <project-root>/output/qa/visual-layout-metrics.json

python <skill-dir>/scripts/validate_visual_layout.py `
  --storyboard <project-root>/output/planning/visual-storyboard.json `
  --metrics <project-root>/output/qa/visual-layout-metrics.json `
  --report <project-root>/output/qa/visual-layout-qa.json `
  --strict
```

## 실패별 롤백

- `PRIMARY_CLAIM_DIRECT_VISUAL`: 콘텐츠기획·스토리보드로 돌아가 증거 장면을 다시 설계한다.
- `PROMPT_CONTRACT`: 생성 전에 프롬프트의 주장 연결·구도·치수 제약을 보강한다.
- `MODULE_ORDER_MISMATCH`: HTML DOM 순서를 승인 계획과 맞춘다.
- `LAYOUT_ORDER_MISMATCH`: 모바일·800px 카피/미디어 위치를 스토리보드와 맞춘다.
- `SUBJECT_CROPPED`: `object-position`, 컨테이너 비율 또는 원본 구도를 수정한다.
- `CRITICAL_REGION_CROPPED`: 핵심 부위를 100% 보이게 하고 해당 viewport를 다시 캡처한다.
- 연관성 80점 미만: 예쁜 이미지를 유지하지 말고 주장에 필요한 시각 단서가 보이는 자산으로 교체한다.
