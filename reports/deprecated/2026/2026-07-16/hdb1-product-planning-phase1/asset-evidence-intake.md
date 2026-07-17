# HDB-1 숨트임 실제 자산·근거 인입 결과

> 상태: `BLOCKED_IDENTITY_ASSETS`
> 프로젝트: [hdb1-sumteuim-phase1](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/README.md)
> 공급처: https://domeggook.com/56587588
> 확인일: 2026-07-16

## 결론

공급처 페이지에서 최신 제품 사진·상품정보표·Intertek 시험 페이지를 확보했다. 상품정보표의 나일론 76%·스판덱스 24%, 4색, 제조국·제조사·판매원과 시험 페이지의 UPF50+는 문서 근거로 잠갔다.

그러나 최신 제품 사진은 전부 실제 인물의 얼굴·피부·손·몸 픽셀을 포함한다. 사람 없는 제품 단독 이미지는 파일명에 `Gemini_Generated_Image`가 있고 표·영문·형태 오류가 있는 생성 이미지뿐이다. 이 생성 이미지는 제품·치수 근거에서 제외했다. 과거형 긴 상세 이미지도 최신 76/24 정보·제품 사진과 충돌할 가능성이 있어 실제 출고 SKU 근거로 승격하지 않았다.

따라서 ImageGen 입력, 제품 마스터 생성, 실제 인물 포함 사진의 최종 합성, 게시 패키지 승격은 차단한다. 제품기획과 콘텐츠기획 승인은 유지되며 실제 SKU 자산을 받으면 동일성 게이트부터 재개한다.

## 인입·분류 결과

| 구분 | 수량 | 판정 |
|---|---:|---|
| 공급처 수집 파일 | 11 | 출처·해시 기록 완료 |
| 실제 인물 포함 제품 사진 | 8 | ImageGen 입력·최종 합성 금지 |
| 문서 근거 | 2 | 상품정보표·Intertek 원본 사용 가능 |
| 공급처 생성 치수 이미지 | 1 | 실제 제품·치수 근거 금지 |
| 안전한 실제 제품 단독 사진 | 0 | 제품 동일성 게이트 차단 |

## 잠근 사실

- 제품명: `숨트임`
- 모델: `HDB-1`
- 색상: 블랙·다크그레이·그레이·핑크
- 혼용률: 나일론 76%·스판덱스 24% — 입고 라벨 재확인 조건
- A~E: 25·13.7·6.7·28.5·4.5cm — 실제 자 실측 조건
- 자외선 차단: 공급처 제공 Intertek `ITKD25025374` 3/7쪽 기준 UPF50+
- 구조: 입·코 주변 좌우 타공, 세로 중심 절개, 원단형 귀 구멍, 롱커버 후보

## 남은 충돌·위험

- 최신 사진과 과거형 긴 상세 사이의 실제 출고 디자인 차이
- 일부 색상에만 보이는 흰색 UPF50+ 인쇄의 실제 유무
- 입고 케어라벨 76/24 일치 여부
- A~E 기준점과 허용 오차
- 전체 시험성적서·HDB-1·색상별 시료 매핑
- `숨쉬기 편함` 게시 조건을 위한 3인 휴식·걷기 간이 QA

## 필요한 P0 자산

1. 블랙 제품 단독 정면·후면·전체 펼침
2. 좌우 측면과 귀 구멍·후면 겹침 확대
3. 입·코 타공 매크로
4. 4색 동일 구도·동일 화이트밸런스
5. 자와 함께 A~E 기준점 실측
6. 포장 앞뒤와 케어라벨·혼용률·제조 표시

자세한 기준은 [촬영 목록](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/photo-shot-list.md), [사실 원장](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/product-truth-ledger.md), [자산 분류](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/asset-inventory.md)에서 관리한다.

## 승인 경계

- 승인 유지: 제품기획·콘텐츠기획·제품명 `숨트임`
- 승인 대기: 샘플 발주·비용, 제안 브랜드명 `에어베일`, 이미지/GIF/영상 제작 완료, 게시
- 수행하지 않은 작업: 발주·결제·상품 등록·광고 집행·ImageGen 제작

## 검증

- `validate_product_facts.py --strict`: 사실 40개, 경고 0개로 통과
- JSON 구문 검사: `product-source-lineage.json`, `reference-routing.json`, `brand-system.json`, `brand-evidence-library.json` 통과
- `validate_project_manifest.py --gate evidence`: 의도한 차단 13건으로 실패
  - `product_truth_images` 0개
  - 실제 SKU identity 상태 `unverified`
  - canonical source 0개
  - 01~10장 reference route의 실제 source ID 없음

위 13건은 템플릿이나 구문 오류가 아니라 P0 실물 촬영이 들어오면 해소할 제품 동일성 게이트다.

- `python scripts\tdd.py verify detail-page`: 상세페이지 테스트 6개와 스킬 검증 통과
- `python scripts\tdd.py check-routing`: 통과
- `python scripts\tdd.py check-reports`: 활성 1개와 보관 구조 통과
- 제품·콘텐츠기획 승인 SHA-256: 기존 승인 기록과 일치
