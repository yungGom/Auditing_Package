# 당기 DSD 원문 해석 — Issue #12

이 기능은 원문과 구조를 읽는 제한된 오프라인 입력 해석기입니다. 회계 항목 추천·확정, 수치 환산, 원본 수정, 업무 수용을 수행하지 않습니다. 실제 보고서 전반의 호환성은 별도 확인 대상입니다.

## 사용

AuditDesk 디렉터리를 import 기준으로 사용합니다.

```python
from pathlib import Path
from auditdesk.xbrl_v2.dsd import DsdReportContext
from auditdesk.xbrl_v2.dsd_structure import parse_dsd_structure

result = parse_dsd_structure(
    Path('current.dsd').read_bytes(),
    logical_uri='current.dsd',
    report=DsdReportContext(scope='CONNECTED', period_end='2026-06-30'),
)
```

`report`는 요청한 문맥이고, `result.document.metadata.observed`는 DSD에서 관찰한 문맥입니다. 요청을 넣었다고 원문 확인이 완료되지는 않습니다. 두 값이 충돌하면 `CONFLICT:*`, 원문 선언이 없으면 `UNKNOWN:*`가 남습니다. 파일명이나 최신 연도에서 보고 문맥을 추정하지 않습니다.

## 독립 입력·출력 계약

- 입력: 당기 DSD ZIP bytes, 선택적인 요청 문맥, 표시용 logical_uri, 양의 정수 크기 제한.
- 출력: immutable `DsdStructuredDocument`. 내부 `document`는 기존 `DsdDocument`이며 `structures`, `sections`, `notes`, `unclassified`, `clues`, `cell_owners`, `coverage`, `diagnostics`가 별도로 붙습니다.
- 공통 `model.py`, `ports.py` 등 V2-1 계약은 PR #13과 바이트 동일합니다. taxonomy, recommendation, legacy binding/golden/orchestration을 import하지 않습니다. Issue #11의 미병합 구현이 필요하지 않습니다.
- 원본 bytes의 SHA-256이 snapshot과 모든 ID의 근거입니다. 표시용 경로를 바꿔도 ID는 같습니다. 내용 변경 또는 parser profile 변경은 결과 재사용을 무효화합니다. 원문 parser profile은 `bounded-dsd-v2`, 추가 구조 profile은 `issue12-structure-v1`입니다. 후보 순위는 입력하지 않습니다.
- 모든 locator는 `document.raw_xml` 안의 **문자 오프셋**이며 byte 오프셋이 아닙니다. `source_span`/`source_spans`는 시작 포함·끝 제외입니다. 열은 여러 불연속 셀 span을 가질 수 있습니다. 원본 XML bytes 해시는 `xml_sha256`입니다.

## 해석하는 구조

루트 `contents.xml` 한 개를 가진 ZIP, UTF-8/EUC-KR/CP949, XML 1.0, DART `&cr;`, P/TITLE 본문, SECTION-N 구역, TABLE/TR/TD/TH/TE/TU와 ROWSPAN/COLSPAN 앵커를 읽습니다. 표는 THEAD/TBODY 같은 래퍼 안의 TR도 포함합니다. 표 밖 표·문단·빈 문단도 보존합니다.

명시적인 제목 `주석`을 가진 SECTION-N 안에서 숫자와 마침표로 시작하는 `SPAN USERMARK="B"`를 주석 경계로 사용합니다. 빈 주석도 남깁니다. 일반 번호 문단·명시적 구역 없는 주석·한 문단 안의 복수 주석 제목은 임의로 확정하지 않습니다. 표 전체와 행·열은 별도 ID를 가지며 병합 내부 좌표는 같은 물리 셀을 참조합니다. ROW/COLUMN의 cell_ids는 중복 물리 값 생성이 아닌 앵커 연결입니다.

`주석` 구역끼리 중첩되면 해당 범위의 의미 주석을 확정하지 않고 `UNKNOWN:nested_note_scopes`를 반환합니다. 구역·원문 블록은 그대로 남습니다. `table.title`/셀의 `table_title`은 이전 TITLE의 문맥 문자열이며 확정된 표 제목이 아닙니다. 실제 DSD의 재무제표 제목은 TD 표에 있을 수도 있으므로 `UNKNOWN:table_title_semantics:*`를 확인하고 #9가 이를 확정 표 의미로 사용하지 않아야 합니다.

`document.subjects`는 원문 셀·P/TITLE이고, 새 `structures`는 구조 관계입니다. 동일 내용을 담은 BLOCK이나 COLUMN을 별도 수치 fact로 세지 않습니다. `coverage`는 물리 셀 수·연결된 셀 수·미분류 텍스트 소유 요소 수이며, 업무 의미를 모두 해석했다는 정확도 비율이 아닙니다. 미분류 원문은 `unclassified`와 전체 raw_xml로 확인할 수 있습니다.

## 미확인·거절 처리

숫자는 원문 문자열입니다. `(1,000)`, 음수, `-`, nil, 빈칸을 숫자 0으로 바꾸지 않습니다. 단위·배율·기간 단서는 원문 범위와 함께 남기되 셀에 환산 배율을 적용하지 않습니다. 당기/전기와 명시적 3개월·누적 열 제목은 비교 역할만 표시하며 실제 날짜·기간 길이를 확정하지 않습니다. “전기오류수정” 같은 계정명은 전기 기간 근거가 아닙니다.

중첩 표, 잘못된 XML/선언, 중복 ZIP 항목, 경로 이탈, 암호화·심볼릭 링크, 과도한 크기/압축률/깊이/셀 span 등은 `DsdParseError`로 거절합니다. 네트워크 호출·파일 추출·DB 기록이 없습니다. 불균일 표, 이어진 표·전치 의미는 진단으로 남깁니다. 전체 문서 크기 제한이 있어도 production 성능 또는 모든 DSD 세대 호환성을 보증하지 않습니다.

## Issue #9 연결

추천기는 먼저 원문 메타 충돌·UNKNOWN과 구조 진단을 검토해야 합니다. 기존 #9 경로의 `DsdDocument` 입력은 `result.document`로 접근할 수 있지만, 이번 브랜치에서 taxonomy·추천 통합은 실행하지 않았습니다. 새 구조 관계·단서·coverage를 추천기에 전달하는 adapter와 충돌/미확인 처리를 독립적인 통합 작업으로 검증해야 합니다. 공통 모델 변경이 필요하다면 #11 담당 작업과 의존관계를 기록하고 Owner Decision을 받아야 합니다. 실제 DSD, 당기 taxonomy 적용성, 3개월/누적과 단위의 최종 해석, DART 편집기 호환성 및 회계적 수용은 별도입니다.
