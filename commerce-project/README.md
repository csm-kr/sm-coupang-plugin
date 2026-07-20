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
python commerce-project\scripts\project_store.py create --workspace . --id summer-mask-001 --name "여름 스포츠 마스크" --channel coupang
python commerce-project\scripts\project_store.py list --workspace .
python commerce-project\scripts\project_store.py legacy --workspace .
python commerce-project\scripts\project_store.py register-report --workspace . --id summer-mask-001 --path reports\2026\2026-07-17\sample-run\report.html
```

`detail-page/projects/`의 기존 폴더는 이동하지 않고 `legacy` 명령과 UI의 기존 작업 섹션에서 확인한다.

워크플로 UI의 `PROJECT EXPLORER`는 이 폴더의 실제 파일과 `links.reportRuns`의 보고서를 구분해 표시하고 HTML·이미지·JSON·텍스트를 인라인 미리보기한다. 이미지 드래그앤드롭은 `folderMap.sourceAssets`의 기본 경로 `40-assets/source`에 PNG·JPG·GIF·WEBP만 저장하며 파일당 20MB 제한, MIME·시그니처 일치, 안전한 파일명과 중복 덮어쓰기 금지를 적용한다.
