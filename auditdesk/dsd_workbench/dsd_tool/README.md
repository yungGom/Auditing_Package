# dsd_tool — DSD ↔ Excel 변환 파이프라인 (v3)

DART 전자공시 DSD 파일의 재무제표·주석·표지를 Excel로 추출하고,
편집된 값만 **위치(오프셋) 기반으로 정밀 역교체**하는 도구.
100% 로컬 실행 (외부 서버 업로드 없음).

기획서: 「DSD ↔ Excel 변환 파이프라인 기획서 v1.0」 (공시 DSD 10개 배치 분석 기반)

> **위치**: 이 패키지는 `dsd_workbench/`(고객사 DSD 편집 — **완전 오프라인**) 소속.
> 네트워크 코드 금지 원칙은 `tests/test_offline.py`가 강제한다.
> CLI는 `dsd_workbench/`에서 실행: `cd dsd_workbench && python -m dsd_tool ...`
> (외부 공시 수신은 별도 앱 `dart_explorer/` 담당 — 코드 결합 금지, 파일 교환만)

## 사용법

```bash
# 1. 추출: DSD → Excel (+ 숨김 _MAP/_META 시트)
python -m dsd_tool extract 삼성전자.dsd            # → 삼성전자.xlsx

# 2. Excel에서 값 편집 (행/열 추가·삭제, 시트명 변경 금지)

# 3. 역변환: 변경 셀만 DSD에 반영
python -m dsd_tool repack 삼성전자.xlsx 삼성전자.dsd  # → 삼성전자_수정.dsd
python -m dsd_tool repack 삼성전자.xlsx 삼성전자.dsd --dry-run  # 변경 목록만 확인

# 수정이력 조회 (repack마다 dsd_workbench/history/history.sqlite에 자동 기록)
python -m dsd_tool history [원본.dsd] [--changes] [--limit N]

# Footing 검증 (DSDbreaker 알고리즘 기반) → _FOOT 리포트 시트 생성
python -m dsd_tool foot 편집용.xlsx [--limit 2] [--prior 전기.xlsx] [--report]
#  합계검증: 값 기반 계층 역추론(하단합계+상단소계 양방향, 다단 계층)
#  주석대사: FS 주석참조("5", "6, 23") ↔ 주석 시트 값(±2), 무참조 시 전 시트 폴백
#  전기대사: --prior 지정 시 당기파일 전기열 ↔ 전기파일 당기열 계정명 매칭
#  레벨 오버라이드: _FOOT [레벨] 섹션 '수동' 열 기입 후 재실행하면 수동 우선

# 옵션 (정리 동작은 기본값 — 끌 때만 옵션 지정)
python -m dsd_tool extract 삼성전자.dsd --report      # &cr;-only 셀 개수 리포트
python -m dsd_tool extract ... --keep-note-numbers   # 주석 번호 중복 정리 끄기
python -m dsd_tool repack ... --keep-cr              # &cr;-only 셀 정리 끄기 (원문 보존)
```

repack 완료 시 `수정 셀 N / &cr; 정리 M / 주석번호 정리 K` 요약을 항상 출력하며,
정리를 껐는데 원본에 &cr;-only 셀이 남아 있으면 보존 경고를 표시한다.

기본 정리 동작 (한 셀에는 한 줄이 정상값):
- **주석 번호 중복**: dartdb 제공 DSD는 주석 헤더가 `1. 1. 일반적 사항`처럼
  번호가 중복 오염되어 있다(10개 파일 공통). extract가 기본으로 `1. 일반적 사항`으로
  정리해 기록하며(같은 번호 연속 중복일 때만), `_MAP`은 원본을 유지하므로 repack 시
  DSD 헤더도 자동 정리된다. `<SPAN USERMARK=" B">` 태그는 보존되어 재추출에도 안전.
- **&cr;-only 셀**: 내용이 `&cr;` 엔티티 반복뿐인 TD/TH/TE/TU 셀(원본 정규식
  `^(?:&amp;cr;)+$`)을 repack이 기본으로 빈 문자열로 정리한다. 값과 `&cr;`이
  섞인 셀(의도적 줄바꿈)과 P 문단은 절대 건드리지 않는다.

두 정리 모두 해당 셀에 사용자가 값을 입력한 경우 일반 수정(edit)이 우선한다.

## 시트 구성

```
사용안내 | 표지 | BS | PL | [PL1] | CE | CF | 1, 2, … (주석) | 외부감사 | _MAP | _META
```

- FS 시트는 감지된 만큼 동적 생성 (4종/5종), 연결·반기 접두사 반영 (예: `연결BS`)
- 숫자는 진짜 숫자로 저장 (콤마/괄호음수 서식). `"3,4,5"` 같은 주석 참조는 텍스트 유지
- 회색 글씨는 참조용(역변환 제외), 검은 셀만 수정 가능
- 빈 셀에 값을 넣으면 해당 XML 위치에 삽입됨

## 구현 핵심

| 모듈 | 역할 |
|------|------|
| `scanner.py` | contents.xml 정규식 스캔: TD/TH/TE/TU 오프셋, FS 제목 TD 테이블, 주석 헤더(`SPAN USERMARK=" B"` → `SPAN ID` → 평문 폴백) |
| `textutil.py` | clean_text / try_number(천단위 검증) / 이스케이프 순서(\n→`&cr;` → `&`→`&amp;`) / FS 제목 정규화 |
| `excel_out.py` | 시트 생성 + `_MAP`(sheet,row,col,xml_start,xml_end,orig_raw≤200) 기록 |
| `repack.py` | _MAP 비교(거짓변경 방지) → 변경 셀만 오프셋 역순 교체. `_META` SHA1로 원본 짝 검증 |
| `zipsplice.py` | contents.xml 엔트리만 교체, 나머지 바이트 보존 (LFH/CD/EOCD 수동 패치). 무변경 시 원본 그대로 복사 |

## 검증 게이트 (자동 테스트)

`python -m pytest dsd_tool/tests/ -q`

- G1 추출: FS/주석/외부감사/표지 시트 구성, 숫자화
- G2 무변경: 역변환 결과 = 원본 바이트 동일
- G3 단일변경: XML 정확히 1곳만 변경, 거짓변경 0
- G4 대량변경: 스타일 보존(괄호음수) 포함 전부 반영
- G5 빈셀삽입: 빈 `<TD></TD>`·`<TE>`에 값 삽입 후 재추출 왕복 확인
- 성능: 1.6MB / 38,000셀 합성 파일에서 추출 6초·역변환 10초 내외

### 실제 공시 DSD 10개 배치 검증

`python -m dsd_tool.tests.batch_validate [fixtures_dir] [work_dir]`
(기본: `dsd_tool/fixtures/real/`)

2026-07-03 기준 **10/10 완전 통과**: G1(전수 추출) + G2(무변경 바이트 동일) +
기획서 §1 표의 FS 종수·주석 수 전 파일 일치, 연결/반기 접두사 시트명 확인.
남은 수동 검증: 실제 파일 G3~G5(값 수정 후 DART 편집기 열림 확인).

## 남은 작업 (스펙 P3)

- K-GAAP DSD 확보 시 구조 분기 검증 (이익잉여금처분계산서 감지는 구현됨: `RE`/`DE` 시트)
- GUI (PyWebView) / EXE 패키징
- `원문` 통합 참조 시트
