# 제품기획 산출물 계약

## 필수 산출물

- `product-truth-ledger.md`
- `product-facts.json`
- `competitor-pain-map.md`
- `claim-evidence-matrix.json`
- `planning/product-plan.json`
- `approvals/product-plan-approval.json`
- `experiment-plan.json`

## 입력과 조사 책임

- 공급처 상세 URL 하나만으로 조사를 시작할 수 있다. Codex는 상세 본문·옵션·상품정보·공개 후기·문의를 확인해 색상·사이즈·구성·소재·관리법을 정리하고, 조사 결과를 사용자에게 먼저 보고한다. 그다음 판매가·묶음·판매 옵션을 사용자와 정하는 오퍼 결정 게이트를 통과한다.
- 사용자는 사이즈·실측, 구성, 소재, 관리법과 실제 SKU·라벨 이미지를 제공한다. 이미지는 UI가 `project.json`의 `folderMap.sourceAssets`에 저장하며 경로 문자열을 수기 입력받지 않는다.
- Codex는 Browser Harness로 공개된 경쟁상품의 별점 1~3점 리뷰를 조사한다. `competitor-pain-map.md`에는 경쟁상품 URL, 리뷰 URL 또는 공개 페이지 근거, 조사시각, 별점 범위, 관찰 표본 수와 반복 불만을 기록한다.
- 로그인·CAPTCHA·접근 통제를 우회하지 않는다. 공개 근거를 확보하지 못하면 불만을 추정하지 않고 차단 상태와 재개 조건을 기록한다.
- 사용자 앞 단계 완료 확인은 진입 상태일 뿐 SKU·가격·공급처 검증을 대체하지 않는다.

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
