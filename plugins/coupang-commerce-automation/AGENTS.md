# 플러그인 패키지 지침

이 디렉터리는 배포 사본이다. 스킬 정본은 저장소 루트의 `coupang-product-sourcing/`과 `coupang-detail-page-generator/`다.

- 플러그인 안의 스킬 사본을 직접 기능 개발하지 않는다. 루트 원본을 테스트한 뒤 동기화한다.
- `.codex-plugin/plugin.json`의 이름과 외부 폴더 이름을 일치시킨다.
- 지원하지 않는 manifest 필드를 추측으로 추가하지 않는다.
- 동기화 후 `python ../../scripts/tdd.py verify plugin`을 실행한다.
- 플러그인 구조·스킬·훅이 바뀌면 `../../docs/COUPANG-COMMERCE-AUTOMATION-PLUGIN-PLAN.md`와 README를 갱신한다.

원본 동기화 명령은 이 디렉터리의 `README.md`를 따른다.
