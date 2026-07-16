# layout-spec.json

`render_commercial_pages.py`는 `output/layout-spec.json`을 읽어 `output/images/01.png`~`10.png`를 만든다.

## 기본 구조

```json
{
  "version": "5.2",
  "canvas": {"mode": "fixed", "width": 800, "height": 2400, "min_height": 2400, "max_height": 2400},
  "fonts": {
    "hook": {"path": "C:/Windows/Fonts/NotoSansKR-VF.ttf", "variation": "Black"},
    "title": {"path": "C:/Windows/Fonts/NotoSansKR-VF.ttf", "variation": "Black"},
    "body": {"path": "C:/Windows/Fonts/NotoSansKR-VF.ttf", "variation": "Regular"},
    "badge": {"path": "C:/Windows/Fonts/arialbd.ttf"}
  },
  "pages": []
}
```

페이지는 01~10 순서로 정확히 10개다. 각 페이지는 `page`, `role`, `height`, `background`, `layout`, `purchase_reason`, `asset_ids`, `elements`를 가진다.

## 생성 비주얼

각 페이지는 같은 번호의 생성 비주얼을 사용한다.

```json
{
  "type": "image",
  "path": "output/generated-pages/PG-01.png",
  "asset_id": "PG-01",
  "source_kind": "generated_page",
  "box": [0, 0, 800, 2020],
  "fit": "cover"
}
```

실제 사람이 포함된 raw 경로를 이미지 요소로 넣지 않는다. `source_kind: raw_product_only`는 사람 픽셀이 없는 제품 전용 이미지에만 허용한다.

## 텍스트 합성

이 레이아웃 사양은 비주얼 구조 검토와 레거시 프로젝트에만 사용한다. 워크플로 5.2에서는 로컬 타이포그래피 폴백을 허용하지 않는다. 1차 ImageGen 비주얼을 무문자로 만들고, 이를 조건 이미지로 다시 입력해 최종 타이포그래피를 생성하며 한글 영역 부분 편집은 총 3회까지만 수행한다.

- 히어로 후킹: 74~94px, Noto Sans KR Black
- 섹션 제목: 60~78px, Noto Sans KR Black
- 파란 강조: `#5C94D6`
- 본문: 26~34px, `#303946`
- 캡션·칩: 19~25px, Bold
- 카드 배경: `#FFFFFF` 또는 `#F7FAFE`
- 페이지 배경: `#FAF8F2`

텍스트를 사진의 중요한 제품·얼굴·손 위에 올리지 않는다. ImageGen 프롬프트의 안전 여백과 `overlay-copy.md`의 `safe_area`를 맞춘다.
각 제목 요소에는 선택적으로 `highlight`와 `highlight_color`를 둘 수 있다. `highlight`는 반드시 제목 안에 한 번 포함된 `emphasis` 구절이며 같은 글자로 중복 렌더링하지 않는다.

## 밀도

- 첫 콘텐츠 y ≤ 140px
- 콘텐츠 세로 점유율 ≥ 70%
- 시각 요소 면적 55~85%
- 빈 하단이 페이지 높이의 15%를 넘지 않음
- 같은 레이아웃 연속 사용 금지

생성 비주얼 한 장을 단순 배경으로만 반복하지 않는다. 크롭, 카드, 확대, 여백 방향을 페이지 역할에 맞게 달리한다.
