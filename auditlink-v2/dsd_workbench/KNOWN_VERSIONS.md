# DART 편집기 버전 관리 (KNOWN_VERSIONS)

dsd_tool이 G2(무변경 바이트 동일)를 검증한 DART 편집기 버전 목록.
아래 표는 `python -m dsd_tool.tests.batch_validate` 실행 시 자동 갱신된다.
extract 시 이 목록에 없는 editver를 만나면 경고가 출력된다.

<!-- AUTO-TABLE-START -->
| editver | 확인 파일 수 | G2(무변경 바이트 동일) | 최근 확인 |
|---------|-------------|------------------------|-----------|
| 5.049 | 12 | PASS | 2026-07-08 |
<!-- AUTO-TABLE-END -->

## 수동 메모

- 지시서에 언급된 5.106 / 5.107은 아직 픽스처 미확보 — 해당 버전 DSD 확보 시 fixtures/real에 넣고 batch_validate 재실행.
- docver는 문서 버전(4.1=구형, 3.5=DART 6.0 변환본에서 관찰)으로 editver와 별개.
