# HTML 한글 타이포그래피 QA

## 목적

HTML의 편집 가능성을 유지하면서 한글 단어 중간 분리, 한 글자 고아행, 제목 행수 초과, 글자 잘림과 겹침을 게시 전에 차단한다. DOM의 글자 수나 일반 스크린샷 폭은 실제 CSS 줄바꿈을 보장하지 않으므로 Chromium 계열 브라우저의 문자별 렌더 좌표를 정본으로 사용한다.

## 필수 산출물

- `output/qa/typography-metrics.json`: 360px·800px 문자·행·요소 좌표
- `output/qa/typography-qa.json`: 오류·경고와 최종 `pass` 또는 `fail`
- `output/qa/typography-screenshots/`: viewport별 10개 모듈 캡처

HTML·CSS·카피·폰트가 하나라도 바뀌면 세 산출물은 오래된 상태이며 다시 수집한다.

## 측정 준비

1. 프로젝트 HTML 루트를 로컬 HTTP로 제공한다. `file://` 경로는 자산·폰트 정책 차이가 있으므로 쓰지 않는다.
2. Chromium 또는 Edge를 QA 전용 임시 프로필과 `--remote-debugging-port=9225`로 시작한다.
3. 사용자 브라우저 세션이나 기존 탭을 닫지 않는다. 이 QA가 시작한 브라우저·서버만 종료한다.
4. 수집기는 브라우저 캐시를 끄고 viewport마다 `typography_qa` 쿼리를 붙여 현재 파일을 다시 읽는다.
5. CSS 애니메이션·lazy load 모듈을 한 번씩 노출한 뒤 좌표를 수집한다.

```powershell
node <skill-dir>/scripts/collect_html_typography_metrics.mjs `
  --cdp http://127.0.0.1:9225 `
  --url http://127.0.0.1:8765/html/detail-page.html `
  --viewports 360x900,800x1000 `
  --settle-ms 250 `
  --screenshots <project-root>/output/qa/typography-screenshots `
  --output <project-root>/output/qa/typography-metrics.json

python <skill-dir>/scripts/validate_html_typography.py `
  --metrics <project-root>/output/qa/typography-metrics.json `
  --required-viewports 360 800 `
  --report <project-root>/output/qa/typography-qa.json `
  --strict
```

수집기는 기존 CDP 세션에 QA target만 만들고 닫는다. 브라우저와 로컬 서버를 직접 시작했다면 검수 완료 또는 실패 후에도 반드시 종료한다.

## 측정 대상 표시

수집기는 기본 제목·본문·캡션·사양값을 찾고, 중요한 사용자 정의 요소는 `data-typography`로 추가한다.

```html
<h2 data-typography-max-lines="2">햇빛은 가리고,<br><em>숨길은 열고</em></h2>
<p data-typography data-typography-role="body" data-typography-max-lines="3">승인된 본문</p>
```

- `data-typography-max-lines`: 허용 최대 행수
- `data-typography-role`: `headline`, `body`, `label`
- `data-typography-allow-short-last="true"`: 의도된 짧은 마지막 행만 경고 예외

예외 속성은 실패를 숨기는 용도가 아니다. 카피의 의미나 고정된 법정 표기 때문에 짧은 마지막 행이 의도된 경우에만 이유와 함께 사용한다.

## 자동 차단 기준

| 코드 | 의미 | 우선 수정 |
|---|---|---|
| `MISSING_VIEWPORT` | 360px 또는 800px 결과 누락 | 정확한 viewport로 재수집 |
| `DOCUMENT_OVERFLOW_X` | 페이지 전체 가로 넘침 | 고정 폭·transform·긴 토큰 확인 |
| `ELEMENT_OVERFLOW_X` | 개별 텍스트 요소 넘침 | 컨테이너 폭·패딩·폰트 조정 |
| `MID_TOKEN_BREAK` | 단어·숫자 중간 분리 | 의미 단위 카피·`keep-all` 확인 |
| `SINGLE_CHARACTER_LINE` | 한 글자만 남은 행 | 카피·폭·패딩 조정 |
| `TOO_MANY_LINES` | 허용 행수 초과 | 카피 축약 후 그리드·크기 조정 |
| `VERTICAL_CLIP` | 글리프가 요소 상하에서 잘림 | 고정 높이·line-height 제거 |
| `LINE_OVERLAP` | 행 간격이 CSS line-height보다 좁음 | line-height·absolute 배치 수정 |
| `BROKEN_GLYPH` | U+FFFD 대체문자 발생 | UTF-8·폰트·원문 수정 |
| `SHORT_LAST_LINE` | 마지막 행이 지나치게 짧음 | 균형·폭·카피 수정; strict에서 실패 |

## 수정 순서

1. 오타·불필요한 조사·중복어를 고치고 카피를 의미 단위로 줄인다.
2. 제목과 본문에 `word-break: keep-all`을 적용하고, 본문에만 긴 토큰용 `overflow-wrap` 폴백을 둔다.
3. 컨테이너의 고정 폭, 과도한 좌우 패딩, 좁은 그리드 열을 조정한다.
4. 제목의 크기·자간·행간을 디자인 토큰 범위 안에서 미세 조정한다.
5. 강제 `<br>`은 의미 단위 경계에만 사용한다.
6. `overflow: hidden`, 글자 축소, 예외 속성으로 문제를 감추지 않는다.
7. 자동 QA를 다시 실행하고 360px·800px 모듈별 캡처에서 제목 리듬, 대비, 여백, 인접 자산 충돌을 육안 확인한다.

자동 QA와 육안 QA가 모두 통과해야 `integration-qa`와 최종 승격을 허용한다.
