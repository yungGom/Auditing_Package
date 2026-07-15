# DART 편집기 버전 관리 (KNOWN_VERSIONS)

dsd_tool이 G2(무변경 바이트 동일)를 검증한 DART 편집기 버전 목록.
아래 표는 `python -m dsd_tool.tests.batch_validate` 실행 시 자동 갱신된다.
extract 시 이 목록에 없는 editver를 만나면 경고가 출력된다.

<!-- AUTO-TABLE-START -->
| editver | 확인 파일 수 | G2(무변경 바이트 동일) | 최근 확인 |
|---------|-------------|------------------------|-----------|
| 5.049 | 13 | PASS | 2026-07-15 |
| 5.106 | 1 | PASS | 2026-07-15 |
<!-- AUTO-TABLE-END -->

## 수동 메모

- 5.106은 2026-07-15 실물 확보(뷰티스킨 FY2025 별도 DSD)로 G2 검증·등재 완료. 5.107은 아직 픽스처 미확보 — 해당 버전 DSD 확보 시 fixtures/real에 넣고 batch_validate 재실행.
- docver는 문서 버전(4.1=구형, 3.5=DART 6.0 변환본에서 관찰)으로 editver와 별개. 6.0 변환본도 editver는 5.049로 동일(docver만 3.5로 바뀜) — 별도 세대가 아니라 같은 editver의 다른 직렬화.

## 새 편집기 버전 출시 시 절차

**방침(불변)**:
1. 우리 도구는 meta.xml의 editver/docver를 절대 수정·창작하지 않는다 (근거: 밑바닥 생성 DSD의 dart4.xsd 스키마 검증 실패 사례 — 버전 변환은 편집기 고유 기능).
2. repack 산출물은 항상 뼈대 DSD의 버전을 그대로 상속한다.
3. 위치 기반 extract는 직렬화 형식(줄바꿈·속성순서)에 무관하다 — 단, 신버전마다 G2로 확인한다.

**절차**:

```
1. 대표 DSD 1개(한빛정밀 클린본)를 새 편집기에서 열기 → 저장
   → 편집기가 변환한 파일 확보 (예: *_6_1변환.dsd)
2. 변환본을 fixtures/real/에 세대 추가
3. batch_validate: 변환본 extract → 무변경 repack → G2(내용 동일) 확인
4. 통과 → KNOWN_VERSIONS.md에 행 추가 (editver, 확인일, G2 결과)
   실패 → 직렬화 차이 리포트 후 진행 중단 (기획 세션 회신)
5. 이후 신버전 뼈대 사용 가능 (구버전 DSD는 편집기 하위호환으로 계속 열림)
```

새 파일을 처음 여는 순간 버전을 확인하려면: `python -m dsd_tool version-check <파일.dsd>` — editver가 미확인이면 이 절차를 그대로 콘솔에 안내하고, 그 파일에 대한 즉석 G2 스모크(무변경 왕복 내용 동일) 결과도 함께 보여준다.
