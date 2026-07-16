# 상품 사실 정책

## 출처 우선순위

1. `raw/`의 인증서, 시험성적서, 공식 상품 정보, 설명서에 명시된 텍스트
2. `raw/` 사진에서 직접 보이는 외형
3. `raw/`의 기타 문서
4. 사용자가 대화에서 명시한 정보

`reference/`는 사실 출처가 아니다. 출처 간 충돌은 임의 해결하지 말고 `CONFLICT`로 표시하고 이유를 쓴다.

## Evidence Ledger 상태

`product-truth-ledger.md`와 워크플로 5.2의 `product-facts.json`은 같은 상태를 사용한다.

- `CONFIRMED_USER`: 사용자가 명시적으로 확인
- `CONFIRMED_SOURCE`: 도매·제조사·공급사·포장·설명서 같은 1차 자료에서 확인
- `OBSERVED_IMAGE`: 실제 제품 소스에서 직접 관찰
- `INFERRED`: 합리적 추론이지만 광고 사용 금지
- `CONFLICT`: 출처끼리 충돌해 확정 불가
- `UNKNOWN`: 제공되거나 확인된 정보 없음
- `FORBIDDEN`: 광고·기획에 사용 금지

광고 카피와 이미지 프롬프트에는 `CONFIRMED_USER`, `CONFIRMED_SOURCE`, `OBSERVED_IMAGE`만 사용한다. `OBSERVED_IMAGE`는 `raw_capture` 또는 신뢰 가능한 `manufacturer_source`에서 본 외형에만 사용하고 소재 혼용률·성능·수치에는 사용하지 않는다.

## 5.1 이하 상태 호환

기존 프로젝트는 아래 상태를 읽을 수 있지만 새로 쓰지 않는다.

| 5.1 이하 | 5.2 | 조건 |
|---|---|---|
| `verified_text`, `verified_evidence`, `VERIFIED_SOURCE` | `CONFIRMED_SOURCE` | 사용자 확인이면 `CONFIRMED_USER`로 분리 |
| `verified_visual`, `VERIFIED_VISUAL` | `OBSERVED_IMAGE` | 실제 SKU 소스만 허용 |
| `USER_CONFIRMED` | `CONFIRMED_USER` | 확인 시점·대화 근거 기록 |
| `uncertain`, `INFERRED` | `INFERRED` 또는 `CONFLICT` | 충돌 여부를 분리 |
| `not_provided`, `UNVERIFIED` | `UNKNOWN` | 값 비움 |
| `prohibited`, `PROHIBITED_CLAIM` | `FORBIDDEN` | 값 비움 |

`generated_master`와 `generated_scene`의 관찰은 `OBSERVED_IMAGE`로 승격하지 않는다.

## 필드 규칙

각 사실은 다음 구조를 사용한다.

```json
{
  "value": "확인된 값 또는 null",
  "status": "CONFIRMED_SOURCE",
  "evidence": "근거를 짧게 설명",
  "source": ["raw/product-info.md"]
}
```

- 광고 허용 상태는 비어 있지 않은 `value`, 구체적 `evidence`, 하나 이상의 `source`가 필요하다.
- `INFERRED`, `CONFLICT`, `UNKNOWN`, `FORBIDDEN`은 광고에 쓸 값을 두지 않는다. 관찰 후보가 필요하면 `notes`에만 기록한다.
- 수치에는 단위와 원문 위치를 기록한다.
- 증빙 유효기간, 적용 모델, 시험 조건이 불명확하면 해당 범위 이상으로 일반화하지 않는다.

## 금지 추론

- 사진의 질감만 보고 소재 혼용률 추정
- 여름 장면만 보고 냉감·자외선 차단 주장
- 물이 있는 장면만 보고 방수 주장
- 두꺼워 보인다는 이유로 보온·내구성 주장
- 로고나 마크 모양만 보고 인증 주장
- reference의 수치·후기·효과를 실제 상품으로 이전
- 일반적인 카테고리 상식을 해당 상품의 기능으로 단정

근거가 없으면 문장을 약하게 바꾸어 우회하지 말고 그 주장을 삭제한다.
