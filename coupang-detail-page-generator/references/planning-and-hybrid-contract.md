# 상품기획·콘텐츠기획 분리와 하이브리드 HTML 계약

## 목적

워크플로 5.3은 `무엇을 팔 것인가`와 `어떻게 설명할 것인가`를 다른 산출물로 관리한다. 텍스트를 이미지에 굽지 않고 네이티브 HTML로 유지해 카피·순서·스타일을 다시 이미지 생성하지 않고 수정할 수 있게 한다.

## 1. 상품기획 계약

`output/planning/product-plan.json`은 다음을 잠근다.

- 승인된 소싱 후보와 프로젝트 ID
- 핵심 고객, 대표 문제, 포지셔닝
- 판매가, 옵션과 묶음 구성
- 게시 가능한 주장과 Evidence ID
- 금지 주장, 규제와 운영 위험

`status: ready_for_approval`인 계획만 승인 대상이다. `record_user_approval.py --target product-plan`은 현재 파일의 SHA-256을 `output/approvals/product-plan-approval.json`에 기록한다. `actor_type`은 항상 `user`다.

## 2. 콘텐츠기획 계약

`output/planning/content-plan.json`은 승인된 상품기획의 SHA-256을 참조하고 다음을 정의한다.

- 모듈 순서와 역할
- 네이티브 HTML 헤드라인·본문
- 주장·근거 ID
- 시각 자산 ID
- 수정 가능한 필드
- 모듈별 QA 기준

콘텐츠기획은 상품기획 승인 후에만 만들 수 있다. 콘텐츠기획도 사용자가 현재 파일을 명시적으로 승인해야 한다. 상품기획이나 콘텐츠기획이 승인 후 변경되면 기존 승인 해시는 오래된 상태가 되어 다음 단계가 차단된다.

## 3. 하이브리드 렌더링

```text
content-plan.json의 카피
  → detail-page.html의 h2·p 네이티브 텍스트

content-assets/의 이미지·GIF·영상
  → detail-page.html의 img·video 외부 참조

styles.css
  → 반응형 레이아웃·타이포·컴포넌트
```

- 제품 비주얼과 기능 증거는 이미지·GIF·영상 자산으로 만든다.
- 헤드라인, 본문, 표, FAQ, 주의 문구는 HTML 텍스트로 둔다.
- 이미지는 `data:image`로 인라인하지 않고 `output/content-assets/` 파일로 분리한다.
- 이미지에는 대체 텍스트와 제품 소스 계보·주장·근거 ID가 필요하다.
- HTML은 360px에서도 가로 스크롤이 없어야 하고 영상은 사용자 제어를 제공한다.

## 4. 소재별 QA

`output/qa/material-qa.json`은 콘텐츠 모듈마다 다음을 모두 `pass`로 기록한다.

1. `technical`: 파일 존재, 해시, 형식, 참조 경로
2. `product_identity`: 실제 SKU 형태·색상·구성·사용 방식
3. `claim_evidence`: 주장·근거·시각 증거 일치
4. `copy_accuracy`: 승인 카피와 의미·수치·표기 일치
5. `visual_quality`: 크롭, 가독성, 상업성, 생성 오류

자동 검사와 육안 검수 상태가 모두 `pass`여야 HTML 조립이 가능하다. 한 모듈이 실패하면 해당 모듈과 원인 자산만 수정한다.

## 5. 통합 QA

조립 후 `output/qa/integration-qa.json`에서 다음을 다시 검사한다.

- 상품기획·콘텐츠기획 정렬
- 전체 구매 흐름과 모듈 순서
- 브랜드·시각 일관성
- 모바일 반응형과 가로 스크롤
- 대체 텍스트·시맨틱 제목·영상 제어
- 전체 문맥에서의 광고 표현
- 채널 규격과 정적 대체 가능성

통합 QA는 현재 `output/html/package-manifest.json`의 SHA-256과 묶인다. HTML·CSS·계획·자산·소재 QA가 바뀌면 다시 조립하고 통합 QA를 재실행한다.

## 6. 표준 명령

```powershell
python <skill-dir>/scripts/validate_planning_contracts.py --project <project-root> --gate product-draft
python <skill-dir>/scripts/record_user_approval.py --project <project-root> --target product-plan --actor-id <user-id> --confirm-user-approval
python <skill-dir>/scripts/build_page_plan.py --project <project-root> --force
python <skill-dir>/scripts/record_user_approval.py --project <project-root> --target content-plan --actor-id <user-id> --confirm-user-approval
python <skill-dir>/scripts/validate_material_qa.py --project <project-root> --strict
python <skill-dir>/scripts/build_hybrid_detail_page.py --project <project-root>
python <skill-dir>/scripts/validate_hybrid_package.py --project <project-root> --strict
```

승인 기록 명령은 사용자가 현재 계획을 명시적으로 승인한 뒤에만 실행한다. 에이전트의 추천, 일괄 제작 요청 또는 침묵은 승인으로 간주하지 않는다.
