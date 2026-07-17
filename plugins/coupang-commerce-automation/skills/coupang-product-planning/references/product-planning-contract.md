# 제품기획 산출물 계약

## 필수 산출물

- `product-truth-ledger.md`
- `product-facts.json`
- `competitor-pain-map.md`
- `claim-evidence-matrix.json`
- `planning/product-plan.json`
- `approvals/product-plan-approval.json`
- `experiment-plan.json`

## 주장-근거 매트릭스

각 행에 다음을 기록한다.

| 필드 | 의미 |
|---|---|
| `pain_id` | 경쟁 저별점 반복 불만 |
| `claim_id` | 우리 소구 후보 |
| `sku_resolution` | 가능·조건부·불가·미확인 |
| `evidence_ids` | 검사서·시험·이미지·사용자 확인 |
| `phase_1_test` | 저비용 간이 실험 |
| `phase_2_test` | 판매 신호 후 심화 검증 |
| `publish_state` | 게시 가능·조건부·금지 |
| `rollback` | 실패 시 돌아갈 단계 |

경쟁 불만 빈도는 관찰 표본 안에서만 계산한다. 한두 리뷰를 시장 전체 사실로 일반화하지 않는다.
