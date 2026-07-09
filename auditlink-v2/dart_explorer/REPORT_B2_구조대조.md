# [B-2 구조 대조 리포트] OpenDART 공시원본 vs dartdb DSD

> 지시서 §4 B-2-2에 따른 첫 작업. 결론이 "형식 상이"이므로 B-2-3 규칙대로
> **변환 파이프라인 구축을 중단하고 본 리포트로 기획 세션에 회신한다.**
>
> 대조 표본: 홈플러스 감사보고서 (2026.02) — **동일 문서의 양쪽 판본**
> - dartdb: `fixtures/real/[홈플러스 주식회사]_2025_[감사보고서 (2026.02)].dsd`
> - OpenDART: `document.xml` API, rcept_no `20260608000212`
>   (재현: `python -m dart_explorer search 홈플러스 --start 20260101 --end 20260701`)

## 1. 대조 결과 요약

| 항목 | dartdb DSD | OpenDART 원본 | 판정 |
|------|-----------|---------------|------|
| ZIP 구성 | `contents.xml` + `meta.xml` | `{rcept_no}_00760.xml` 단일 | **상이** |
| meta.xml (editver) | 있음 (5.049) | **없음** | **상이** |
| XML 루트 | `DOCUMENT` (dart4.xsd) | `DOCUMENT` (dart4.xsd) | 동일 |
| BODY/SECTION/TABLE 스키마 | dart4 본문 태그 체계 | 동일 태그 체계 (TABLE 289 vs 296) | 동일 |
| 감사보고서 본문 | INSERTION placeholder 12개 | **실제 본문 포함** (INSERTION 0) | 상이(완본) |
| 주석 헤더 마크업 | `SPAN USERMARK=" B"` × 41 (전 주석 일관) | `USERMARK="B"/"!B"/무마크업` 혼재, 제목+본문이 같은 P에 연결 | **상이** |
| 주석번호 오염 ("N. N.") | 41개 전부 오염 | **오염 없음** | 상이 (예상 적중) |
| &cr;-only 셀 | 137개 (`&amp;cr;`) | **0개** (&cr; 표기 자체 없음) | 상이 (예상 적중) |
| 개행 | LF | CRLF | 상이 |

## 2. 핵심 발견

1. **본문 스키마는 동일** — 루트·BODY·TABLE·TE(ACODE) 전부 dart4.xsd 체계.
   실험적으로 원본 XML을 `contents.xml`로 감싸 extract에 넣으면
   **FS 4종(BS/PL/CE/CF)·표지·외부감사 4테이블·매핑 4,149셀이 정상 추출**된다.
2. **주석 분할만 부정확** — 주석 헤더 마크업 규약이 달라(무마크업 다수 + `!B`)
   스캐너가 41개 중 12개만 감지. 단, P 선두 숫자헤더 후보는 40개 식별되므로
   **스캐너의 주석 감지 확장(무마크업 인라인 헤더 + `!B` 지원)으로 해결 가능**.
3. **지시서 예상 적중**: dartdb 특유의 "N. N." 주석번호 오염과 &cr; 오염이
   OpenDART 원본에는 없다 → 두 오염 모두 **dartdb 가공 아티팩트**로 확정.
   note-dedup가 OpenDART 원본에서 no-op으로 통과하는 회귀 테스트 추가함
   (`dart_explorer/tests/test_document_structure.py`).

> **[결정 2026-07-08]** (C) 채택 — repack 왕복은 dartdb/편집기 파일 전용,
> OpenDART 원본은 **읽기 전용 수신물**(참고용 엑셀 추출)로 취급한다.
> fetch CLI의 `--as dsd`는 폐기, 필요 시 `--as excel`만 후속 구현.

## 3. 기획 세션 결정 필요 사항 (→ 위 결정으로 종결)

- (A) 스캐너 주석 감지를 OpenDART 원본 마크업까지 확장할지
  (무마크업 인라인 헤더 분리 — 제목과 본문이 같은 P에 붙어 있어
  "헤더 셀 편집" 매핑 방식 재설계 필요)
- (B) OpenDART 원본의 용도를 "참고용 엑셀 추출(주석은 통짜)"로 한정할지
- (C) DSD 왕복(repack)은 dartdb/편집기 파일에만 허용하고,
  OpenDART 원본은 **읽기 전용 수신물**로 취급할지 (권장 — meta.xml이 없어
  DART 편집기 호환 DSD로의 재조립은 from-scratch 금지 원칙과 충돌)

## 4. 잠정 구현 상태 (중단 지점)

- `client/` fetch_binary로 document.xml 수신 + 영구 캐시 동작 확인
- `converters/document_wrap.py`: 원본 ZIP 해체·contents.xml 래핑 헬퍼 (실험/테스트용)
- fetch CLI(`--as excel|dsd|both`)와 3사 왕복 게이트는 **기획 결정 후 재개**
