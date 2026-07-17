# 스토리보드·제작 계약

## 이중 납품

1. `output/html/`: 현재 근거로 완성한 편집 가능한 HTML 패키지
2. `output/experiment-plan.json`: 실제 SKU에서 확인해야 할 가설·촬영·실험·교체 자산과 성공 기준

콘셉트 HTML은 UI·서사·이미지-카피 연결을 평가할 수 있지만 실제 SKU 근거로 승격할 수 없다.

## 주장-이미지 점수

| 점수 | 판정 |
|---:|---|
| 0 | 주장과 무관한 장식 이미지 |
| 25 | 사용 맥락만 비슷함 |
| 50 | 주장을 암시하지만 핵심 부위가 보이지 않음 |
| 75 | 직접 관련되나 한 장면만으로 판단이 모호함 |
| 100 | 주장한 구조·행동·결과가 같은 프레임에서 명확함 |

최종 모듈은 80점 이상이어야 한다. 80점은 자동 유사도 점수가 아니라 동일한 루브릭으로 기록하는 육안 검수 점수다.

## 실험 계획 필드

- `hypothesis_id`
- `claim_id`
- `method`
- `sample_count`
- `control`
- `measurement`
- `success_threshold`
- `failure_action`
- `affected_modules`
- `replacement_asset_ids`
