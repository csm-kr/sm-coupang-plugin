# Commerce Project Workspace

상품 하나의 현재 단계와 파일 위치를 한 폴더에서 찾기 위한 공통 작업 영역이다. 원본 실행 보고서는 기존 `reports/`에 보관하고 프로젝트에는 링크만 등록한다.

```text
projects/<project-id>/
├─ project.json
├─ 00-intake/
├─ 10-sourcing/
├─ 20-product-planning/
├─ 30-content-planning/
├─ 40-assets/{source,generated,motion}/
├─ 50-detail-page/{html,channel-packages}/
├─ 60-qa/
├─ 70-feedback/
└─ links/
```

```powershell
python commerce-project\scripts\project_store.py create --workspace . --id summer-mask-001 --name "여름 스포츠 마스크" --channel coupang --mode standard
python commerce-project\scripts\project_store.py list --workspace .
python commerce-project\scripts\project_store.py legacy --workspace .
python commerce-project\scripts\project_store.py register-report --workspace . --id summer-mask-001 --path reports\2026\2026-07-17\sample-run\report.html
```

`detail-page/projects/`의 기존 폴더는 이동하지 않고 `legacy` 명령과 UI의 기존 작업 섹션에서 확인한다.
