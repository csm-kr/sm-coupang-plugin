# HDB-1 `숨트임` 이미지+HTML·GIF 콘셉트 품질 프로토타입

- 실행일: 2026-07-16
- 상태: `PROTOTYPE_PASS_NOT_PROMOTABLE`
- 목적: 실제 제품 단독 원본이 없는 상태에서 가상 원본으로 외부 시각 소재 + 네이티브 HTML + GIF 제작 방식의 품질과 수정성을 확인
- 사용자 허용: 가상 원본, 약 10개 HTML 모듈, GIF, 소재 QA, 통합 QA와 스킬 준비 문서 기록
- 제외: 실제 SKU 동일성, 콘텐츠기획 v2 해시 승인, 브랜드명, 게시·상품등록·광고·발주·결제

## 결과 바로가기

- [10개 모듈 HTML 미리보기](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/html/detail-page.html)
- [3초 GIF](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/content-assets/air-focus-loop.gif)
- [소재 manifest](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/content-assets/manifest.json)
- [소재별 QA](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/material-qa.json)
- [통합 QA](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/integration-qa.json)
- [HTML 타이포그래피 QA](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/typography-qa.json)
- [360·800px 모듈 캡처](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/typography-screenshots/)
- [프롬프트 기록](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/prompts.md)
- [출처·생성 계보](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/source-lineage.json)
- [콘텐츠 생성·조립 QA 체크리스트](../../../../docs/CONTENT-PRODUCTION-CHECKLIST.md)

## 제작 범위

| 구분 | 결과 |
|---|---|
| 가상 마스터 | 검은색 롱 페이스커버 1개, 실제 제품 근거 아님 |
| 페이지 시각 소재 | 히어로·선택 기준·근거 개요·타공·핏·치수·4색·마무리 8개 |
| 보존 문서 | 공급처 제공 Intertek `ITKD25025374` 3/7쪽 1개, byte-for-byte copy |
| 모션 | 600×900px·15프레임·3.0초 구조 초점 GIF 1개 |
| HTML | 360~800px 반응형 10개 모듈, 카피·치수·사양 네이티브 HTML |
| 인터랙션 | 현재 모듈 표시, 스크롤 등장, GIF 정지·정적 대체, 감소된 모션 대응 |

## 10개 모듈

1. 핵심 제안 — 햇빛 가림·호흡부 타공·25cm 롱커버
2. 선택 기준 — 가림과 호흡 구조
3. 근거 지도 — 시험·구조·실측 분리
4. UPF 근거 — 공급처 Intertek 원본과 제한 문구
5. 호흡부 — 타공 구조 GIF, 성능 단정 금지
6. 착용 구조 — 원단형 귀 구멍, 압박·흘러내림 미검증
7. 치수 — A~E 수치를 HTML로 분리
8. 색상 — 옵션명 4개를 HTML로 분리, 화면색은 콘셉트
9. 상품 정보 — 소재·제조 정보 HTML 표, 관리법 비노출
10. 요약 — 확인된 세 축만 재정리, 판매 CTA 제외

## QA 결과

| 항목 | 결과 |
|---|---|
| 모듈 수 | 10/10 |
| 360px 가로 넘침 | 0 |
| 800px 가로 넘침 | 0 |
| 실제 문자 좌표 타이포 QA | 360·800px 78개 요소·오류 0·경고 0 |
| 모듈별 viewport 캡처 | 360px 10개·800px 10개 |
| 제목 계층 | `h1` 1개·`h2` 9개 |
| 이미지 대체 텍스트 | 누락 0/10 |
| 스크롤 후 이미지 로드 | 성공 10/10·실패 0 |
| JavaScript 예외 | 0 |
| GIF 정지·정적 대체 | 통과 |
| 미승인 `에어베일` 노출 | 0 |
| 호흡 성능 확정 주장 | 0 |
| 실제 제품 동일성 | `BLOCKED` |

대표 육안 검수 이미지는 [QA screenshots](../../../../detail-page/projects/hdb1-sumteuim-phase1/output/prototypes/concept-only-v1/qa/screenshots/)에 보존했다. 인앱 브라우저는 Node 커널 경로 오류, `browser-use`는 기존 데몬 포트 파일 권한 오류로 연결되지 않아 독립 임시 프로필의 Edge 헤드리스 CDP로 localhost만 렌더링했다. 검수 뒤 서버와 브라우저는 종료했다.

줄바꿈 보완 검수에서는 일반 headless `--window-size=360`의 최소 창 폭 함정을 제외하고 CDP가 강제한 실제 360px·800px만 사용했다. 문자별 렌더 좌표를 수집해 단어 중간 분리, 한 글자 고아행, 제목 행수 초과, 가로·세로 잘림과 행 겹침을 자동 판정한 뒤 같은 viewport로 20개 모듈을 육안 확인했다.

## 품질 판단

이미지 안에 한글과 수치를 굽지 않아 카피·치수·사양·색상명 수정은 HTML만 바꾸면 된다. 10개 장면의 구매 흐름, 상업적 타이포, 모바일 가독성과 GIF 대체 동작은 다음 스킬의 대표 구조로 사용할 만하다.

다만 가상 장면 사이 타공 수, 귀 구멍과 하단 플레어 형상이 조금씩 달라 실제 제품 동일성은 통과하지 못한다. 4색과 착용 핏도 연출일 뿐이다. 따라서 이번 결과는 레이아웃·편집성·프롬프트·QA 계약의 품질 벤치마크이며 판매 상세페이지가 아니다.

## 스킬로 합칠 항목

- `concept_only` 명시 허용·격리·지속 고지·승격 차단 계약
- 제품 마스터 → 장별 소재 → 소재 QA → GIF → HTML → 통합 QA 순서
- asset ID·해시·alt·claim/evidence·계보 manifest
- 이미지 안 카피 금지와 네이티브 HTML 수정 필드
- 3~6초 GIF 빌더, 정적 대체와 감소된 모션
- 360·800px 반응형·접근성·가로 넘침·깨진 자산 자동 검사
- 실제 문자 좌표 기반 단어 중간 분리·고아행·행수·잘림·겹침 자동 검사와 모듈별 캡처
- 실제 원본 교체 시 소재 QA·통합 QA 전체 재실행

## 다음 실제 게이트

1. 자산 기반 콘텐츠기획 v2 해시를 사용자가 승인하거나 수정한다.
2. 사람 없는 실제 SKU 정·후·좌우·펼침·타공 매크로·4색·라벨·포장·A~E 실측을 확보한다.
3. 가상 마스터와 장면을 실제 제품 자산으로 교체한다.
4. 실제 착용·호흡·물빠짐 간이 QA와 실촬영 GIF를 추가한다.
5. 소재 QA와 통합 QA를 다시 실행한 뒤에만 채널 패키징을 검토한다.
