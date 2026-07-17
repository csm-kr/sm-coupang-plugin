# 단계·상태 계약

## 10단계

1. 소싱·가격 승인
2. 제품 사실·정체성 잠금
3. 시장·저별점 리뷰 조사
4. 제품기획과 사용자 승인
5. 콘텐츠기획과 사용자 승인
6. UI·주장-이미지 스토리보드 승인
7. 콘텐츠 소재 생성과 소재 QA
8. 실사진·GIF·영상 교체
9. 이미지+HTML 조립
10. 통합 QA와 최종 승격

## 상태 전이

```text
sourced
  → handoff_approved
  → identity_locked
  → product_plan_approved
  → content_plan_approved
  → storyboard_validated
  → materials_passed
  → assembled
  → completed
```

`concept_only`는 `storyboard_validated`부터 `assembled`까지 품질 검토만 허용한다. 실제 SKU 동일성 근거가 없으면 `completed` 또는 게시 가능 상태로 승격하지 않는다.

## 한 질문 규칙

다음 단계가 사용자 결정에 따라 달라질 때만 질문한다. 가장 앞선 차단 조건 하나를 선택한다.

우선순위는 다음과 같다.

1. 법률·안전·필수 표시
2. 상품·가격·제품기획 승인
3. 실제 SKU 동일성 자산
4. 콘텐츠기획·스토리보드 승인
5. 비용이 드는 촬영·실험
6. 미세한 디자인 선호

질문 후에는 답을 기다려야 하는 작업만 멈추고, 정본 점검·테스트·비파괴적 준비는 계속한다.

## 재개할 프로젝트 선택

1. 사용자가 `project_id` 또는 프로젝트 경로를 지정하면 그것만 사용한다.
2. 지정이 없으면 유효한 project/prototype manifest가 있고 `completed`가 아닌 후보를 찾는다.
3. 후보가 하나면 선택한다. 여러 개면 파일 수정시각이 아니라 manifest의 `updated_at`이 가장 최신인 후보를 선택한다.
4. `updated_at`이 없거나 최신 값이 같은 후보가 둘 이상이면 임의 선택하지 않고 후보 ID를 보여준 뒤 한 질문으로 대상을 확인한다.
5. 선택한 `project_id`, manifest 경로, `updated_at`과 마지막 통과 QA를 상태 카드의 완료 근거에 표시한다.

## 승인 기록 계약

제품기획·콘텐츠기획·스토리보드 승인은 아래 최소 필드를 가진 별도 기록이어야 한다.

```yaml
target_type: product_plan | content_plan | visual_storyboard
target_path: output/planning/<file>
target_sha256: <현재 대상 파일 SHA-256>
actor_type: user
decision: approved
approved_at: <ISO-8601>
```

`target_sha256`이 현재 파일과 다르거나 `actor_type: user`가 아니면 승인되지 않은 상태다. 오케스트레이터의 추천·요약·이전 대화는 이 기록을 대신하지 않는다.

## QA 실패와 롤백 상태

통합 시각 QA 실패는 완료 상태가 아니라 다음 상태로 기록한다.

```yaml
status: integration_qa_failed
failed_gate: visual_layout
failed_module_ids: ["03"]
rollback_to: html_assembly | content_studio
report_path: output/qa/visual-layout-qa.json
```

- CSS 그리드, 순서, `object-fit`, `object-position`, 패딩 때문에 실패하면 `rollback_to: html_assembly`다.
- 원본 구도·필수 부위·스토리보드 안전영역 자체가 부족하면 `rollback_to: content_studio`다.
- 수정 후 `coupang-publish-qa`가 같은 viewport에서 재검사하기 전에는 `completed`로 돌아가지 않는다.
- 필수 viewport는 360px·800px, 모듈 순서와 주장-자산 연결은 각각 100%다.
- 주 피사체 가시율 95% 이상, 핵심 영역 가시율 100%, 허용 크롭 실패 0건을 사용한다.
