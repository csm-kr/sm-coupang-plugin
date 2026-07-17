# 콘텐츠 생성·조립 QA 체크리스트

이 문서는 상품기획과 콘텐츠기획이 승인된 뒤 시각 소재, GIF·영상, 편집 가능한 HTML을 제작하고 검수하는 공통 절차다. `concept_only`는 품질 프리뷰를 위한 예외 경로이며 실제 제품 근거나 게시 승인을 대신하지 않는다.

## 1. 입력과 승인 게이트

- [ ] 상품기획 버전·SHA-256·사용자 승인 기록이 있다.
- [ ] 콘텐츠기획 버전·SHA-256·사용자 승인 기록이 있다.
- [ ] 실제 제작인지 `concept_only` 예외인지 manifest에 고정했다.
- [ ] 제품명, 브랜드명, 오퍼, 가격, 허용 주장과 금지 주장을 분리했다.
- [ ] 발주·결제·상품 등록·게시·광고는 별도 사용자 승인 없이는 실행하지 않는다.

`concept_only`이면 다음을 추가한다.

- [ ] 사용자가 가상 원본 생성과 품질 프리뷰 범위를 명시적으로 허용했다.
- [ ] 모든 가상 자산에 `연출용 콘셉트 이미지` 계보와 표시 규칙이 있다.
- [ ] 가상 마스터·장면을 동일성, 치수, 사양, 시험, 성능 근거로 사용하지 않는다.
- [ ] 실제 자산 교체 전 `promotion_status=blocked`를 유지한다.

## 2. 제품 사실과 자산 계보

- [ ] 사실마다 `fact_id`, 원문, 출처, 확인일, 검증 상태가 있다.
- [ ] 자산마다 `asset_id`, 경로, 파일 형식, 폭·높이, SHA-256을 기록했다.
- [ ] 자산마다 원본·보정·생성 마스터·생성 장면·문서 증거 중 유형을 지정했다.
- [ ] 자산마다 연결할 `claim_id`, `evidence_id`, 모듈 ID와 대체 텍스트가 있다.
- [ ] 공급처 인물 사진의 사람 픽셀은 ImageGen 입력·최종 합성에서 제외했다.
- [ ] 시험서·라벨·사양표는 원본 보존과 변환본을 구분했다.
- [ ] 제품 동일성을 잠글 canonical source와 장별 reference routing이 있다.

## 3. 가상 또는 실제 마스터 준비

- [ ] 정면, 후면, 좌우, 펼침, 핵심 구조 매크로의 요구 목록이 있다.
- [ ] 마스터의 형태, 봉제선, 구멍 수·위치, 귀 구조, 하단 길이를 잠갔다.
- [ ] 색상별 동일 구도와 조명 기준을 정했다.
- [ ] 실제 제품 마스터는 무관한 보정·재구성을 하지 않았다.
- [ ] 가상 마스터는 `trusted_for_identity=false`이며 실제 원본과 별도 폴더에 둔다.

## 4. 장별 소재 명세

각 모듈은 아래 필드를 가진다.

| 필드 | 필수 내용 |
|---|---|
| 목적 | 문제 인식, 근거, 구조, 치수, 옵션, 사양, 요약 중 역할 |
| 카피 | 헤드라인, 보조문, 출처·제한 문구 |
| 시각 자산 | asset ID, 구도, 배경, 제품 잠금, 금지 요소 |
| HTML | 수정 가능한 텍스트·숫자·표·배지·버튼 |
| 근거 | claim ID와 evidence ID, 근거 강도 |
| QA | 기술·카피·시각·제품 동일성 판정 기준 |
| 실패 처리 | 재생성 대상과 유지할 자산 |

### 시각 스토리보드와 수치형 AC

- [ ] `visual-storyboard.json`에 전체 모듈 순서와 핵심 주장 ID가 있다.
- [ ] 모든 모듈에 `claim_ids`, `evidence_ids`, `asset_ids`, `visual_thesis`, `required_visual_cues`가 있다.
- [ ] 모델 장면은 합성/실제 여부, 인원 수, 포즈·카메라 차이와 상단선·타공·귀·목 하단 안전영역을 명시했다.
- [ ] 치수 장면은 A~E 값·단위·시작점·끝점·검증 상태를 가지고, 숫자와 기준선은 HTML/SVG로 분리했다.
- [ ] ImageGen 프롬프트에 용도, 자산 유형, 주 요청, 피사체, 구도, 주장 연결, 치수 가이드, 제약, 회피 항목이 있다.
- [ ] 주장-근거 연결률·핵심 주장 직접 시각화율·모듈 순서 일치율 목표가 각각 100%다.
- [ ] 주 피사체 가시율 95% 이상, 핵심 부위 가시율 100%, 주장-이미지 연관성 80/100 이상을 AC로 기록했다.

## 5. 소재 생성 직후 개별 QA

### 기술

- [ ] 파일이 열리고 manifest의 크기·형식·SHA-256과 일치한다.
- [ ] 권장 색공간과 압축 품질을 충족하며 투명도·알파가 의도와 맞다.
- [ ] 이미지 안에 생성된 한글, 가짜 수치, 로고, 워터마크가 없다.
- [ ] 네이티브 HTML로 올릴 카피·치수·사양 영역의 여백이 충분하다.

### 카피와 근거

- [ ] 카피가 승인된 주장 범위를 넘지 않는다.
- [ ] 시험 결과는 기관·문서번호·출처·시료 매핑 상태를 함께 표시한다.
- [ ] 구조 관찰을 성능 결과로 바꾸지 않는다.
- [ ] 미검증 관리법, 냉감, 의학적 효능, 정량 성능을 노출하지 않는다.

### 시각과 제품 동일성

- [ ] 장면 사이 형태·봉제선·타공·귀 구조·길이·색이 일관된다.
- [ ] 실제 제품과 다른 부품·기능·옵션을 추가하지 않았다.
- [ ] 사람 손·얼굴·착용 자세에 왜곡이나 비현실적 결합이 없다.
- [ ] `concept_only`이면 일관성만 판정하고 실제 동일성은 `blocked`로 둔다.

판정은 `pass`, `pass_with_limit`, `fail`, `blocked`를 사용한다. 실패한 소재만 재생성하고 통과한 소재는 유지한다.

## 6. GIF·짧은 영상 QA

- [ ] 길이는 기본 3~6초이며 시작·끝 프레임이 자연스럽게 이어진다.
- [ ] 프레임마다 제품 정체성과 핵심 구조가 유지된다.
- [ ] 동작이 실제 성능을 과장하거나 존재하지 않는 기능을 연출하지 않는다.
- [ ] 실험 영상은 조건·횟수·결과·한계를 함께 기록한다.
- [ ] GIF에는 정적 대체 이미지와 모션 정지 수단이 있다.
- [ ] `prefers-reduced-motion`에서 자동 정지 또는 정적 자산을 제공한다.
- [ ] 실제 제품 동작을 보여주는 모션은 최종적으로 실촬영 원본으로 교체한다.

## 7. HTML 조립

- [ ] 시각 소재는 외부 파일, 카피·수치·표·배지는 네이티브 HTML로 분리했다.
- [ ] 각 모듈은 `data-module-id` 또는 `data-module`, `data-claim-ids`를 가지며 각 미디어는 `data-asset-id`, `data-claim-ids`를 가진다.
- [ ] 360~800px에서 가로 스크롤과 잘림이 없다.
- [ ] 제목·중요 본문에 역할과 허용 행수(`data-typography-max-lines`)를 기록했다.
- [ ] 한글 제목은 `word-break: keep-all`, 본문은 긴 토큰용 안전한 폴백을 사용한다.
- [ ] 강제 줄바꿈은 단어 내부가 아닌 승인 카피의 의미 단위 사이에만 있다.
- [ ] `h1`은 1개이고 모듈 제목의 계층이 연속적이다.
- [ ] 모든 정보 이미지에 의미 있는 `alt`가 있다.
- [ ] 버튼과 링크는 키보드로 조작되고 포커스가 보인다.
- [ ] 모션 정지, 감소된 모션, 명도 대비, 본문 글자 크기를 확인했다.
- [ ] lazy load 후 모든 자산이 로드되고 깨진 링크가 없다.
- [ ] 쿠팡 정적 대체본에 필요한 핵심 정보가 JS 없이도 남는다.

### 실제 렌더 줄바꿈 검증

- [ ] QA 전용 Chromium/Edge에서 캐시를 끄고 360x900·800x1000 viewport를 실제로 수집했다.
- [ ] `typography-metrics.json`에 두 viewport와 대상 요소가 모두 있다.
- [ ] 가로 넘침, 단어·숫자 중간 분리, 한 글자 고아행, 행수 초과가 0건이다.
- [ ] 글자 세로 잘림, 행 겹침, 깨진 대체문자, strict 경고가 0건이다.
- [ ] viewport별 10개 모듈 캡처를 육안 확인했다.
- [ ] HTML·CSS·카피 수정 후 캐시된 결과를 재사용하지 않고 다시 측정했다.

```powershell
node <skill-dir>/scripts/collect_html_typography_metrics.mjs --cdp <endpoint> --url <detail-page-url> --viewports 360x900,800x1000 --screenshots <project-root>/output/qa/typography-screenshots --output <project-root>/output/qa/typography-metrics.json
python <skill-dir>/scripts/validate_html_typography.py --metrics <project-root>/output/qa/typography-metrics.json --report <project-root>/output/qa/typography-qa.json --strict
```

일반 headless 브라우저의 `--window-size=360`은 구현에 따라 최소 창 폭이 적용될 수 있으므로 360px 증거로 쓰지 않는다. CDP의 `Emulation.setDeviceMetricsOverride` 결과만 자동 판정과 캡처에 사용한다.

### 실제 렌더 순서·주장·크롭 검증

- [ ] 360x900·800x1000에서 모듈 순서가 스토리보드와 100% 일치한다.
- [ ] 모듈 주장과 미디어 주장·자산의 연결률이 100%다.
- [ ] 주 피사체는 정규화 안전영역의 95% 이상, 모든 핵심 부위는 100% 보인다.
- [ ] 모듈별 주장-이미지 연관성 육안 점수가 80/100 이상이다.
- [ ] 실패 시 임계값을 낮추지 않고 구도·`object-fit`·`object-position`·그리드·패딩을 수정한 뒤 다시 측정한다.

```powershell
node <skill-dir>/scripts/collect_visual_layout_metrics.mjs --cdp <endpoint> --url <detail-page-url> --storyboard <project-root>/output/planning/visual-storyboard.json --viewports 360x900,800x1000 --screenshots <project-root>/output/qa/visual-layout-screenshots --output <project-root>/output/qa/visual-layout-metrics.json
python <skill-dir>/scripts/validate_visual_layout.py --storyboard <project-root>/output/planning/visual-storyboard.json --metrics <project-root>/output/qa/visual-layout-metrics.json --report <project-root>/output/qa/visual-layout-qa.json --strict
```

## 8. 조립 후 통합 QA

- [ ] 10개 모듈의 문제→기준→근거→구조→핏→치수→옵션→사양→요약 흐름이 끊기지 않는다.
- [ ] 반복 카피와 반복 비주얼을 제거했다.
- [ ] 제품명과 승인 브랜드가 모든 장에서 일관된다.
- [ ] 장별 근거 범위가 조립 과정에서 확대되지 않았다.
- [ ] GIF·이미지·HTML의 색상과 제품 형태가 서로 충돌하지 않는다.
- [ ] 360px과 800px 대표 스크린샷을 육안 검수했다.
- [ ] `typography-qa.json`이 오류·경고 0건으로 통과했고 현재 HTML·CSS·카피와 같은 실행에서 생성됐다.
- [ ] 소재 QA 실패가 0건이고 통합 QA 실패가 0건이다.
- [ ] 실제 자산 교체 뒤 소재 QA와 통합 QA를 모두 다시 실행한다.

## 9. 승격과 패키징

- [ ] 실제 SKU 동일성, 라벨, 치수, 옵션, 시험 시료 매핑이 잠겼다.
- [ ] 미검증 주장은 삭제하거나 명확한 제한 문구가 있다.
- [ ] 소재·통합 자동 QA와 육안 QA가 모두 통과했다.
- [ ] 채널별 이미지 크기·파일 크기·금지 표현·링크·접근성을 검사했다.
- [ ] manifest, 해시, 승인 기록, QA 결과, 재생성 로그가 패키지에 포함됐다.
- [ ] `concept_only`, `blocked`, `pending` 항목이 하나라도 있으면 게시 패키지로 승격하지 않는다.

## 10. 실제 원본 교체 체크포인트

가상 프리뷰 뒤에는 다음 순서로 교체한다.

1. 실제 제품 단독 원본을 수집하고 제품 동일성을 잠근다.
2. 가상 마스터를 실제 canonical product master로 교체한다.
3. 정면·착용·타공·치수·4색·라벨·포장 소재를 다시 만든다.
4. GIF를 실제 착용·구조·간이 실험 영상으로 교체한다.
5. 장별 소재 QA를 다시 실행한다.
6. HTML 조립 후 통합 QA와 채널별 게시 전 QA를 다시 실행한다.

## 11. 최소 산출물

```text
prototype-or-project/
├── prototype-manifest.json 또는 project-manifest.yaml
├── source-lineage.json
├── prompts.md
├── experiment-plan.json
├── planning/
│   └── visual-storyboard.json
├── content-assets/
│   ├── manifest.json
│   └── 이미지·GIF·영상
├── html/
│   ├── detail-page.html
│   ├── styles.css
│   ├── interactions.js
│   └── package-manifest.json
└── qa/
    ├── material-qa.json
    ├── integration-qa.json
    ├── visual-storyboard-qa.json
    ├── visual-layout-metrics.json
    ├── visual-layout-qa.json
    ├── claim-visual-qa.json
    ├── typography-metrics.json
    ├── typography-qa.json
    └── screenshots/
```
