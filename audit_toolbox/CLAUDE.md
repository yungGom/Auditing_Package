# K-IFRS 16 Toolbox (audit_toolbox) — 리스·감가상각 재계산 및 의사록 OCR 감사 도구 모음

## 프로젝트 컨텍스트

Streamlit 멀티페이지 데스크톱 도구. 감사인이 로컬 PC에서 실행한다. 12개
페이지로 구성된다 — 리스 식별·면제·할인율·기본재계산·변동리스료·리스변경·
리스제공자·판매후리스·전대리스(1~9), 감가상각 재계산(10), PDF 도구(11),
의사록 OCR(12).

공통 흐름: 회사 원장 엑셀 업로드 → 컬럼 매핑 → K-IFRS 재계산 →
회사값과 차이 분석 → 워크페이퍼용 엑셀 다운로드.

진입점은 `audit_toolbox.py`(런처), 각 도구는 `pages/N_Name.py`.

## 데이터 보안 (절대 준수)

한국 회계법상 고객 기밀 유지 의무에 따라 다음을 절대 준수한다.

- 모든 처리는 로컬에서 수행한다. 외부 API·클라우드·텔레메트리로
  데이터를 전송하지 않는다.
- 네트워크 서버는 127.0.0.1에만 바인딩한다. 이 repo는 `run.bat`에서
  `--server.address localhost --browser.gatherUsageStats false`로
  8501 포트를 localhost 전용으로 띄운다. 이 옵션을 제거하거나 약화하지 않는다.
- 절대경로·OS 사용자명·실제 클라이언트명을 코드에 하드코딩하지 않는다.
  `CONFIG`의 `input_dir`/`output_dir` 같은 경로는 빈 문자열로 두고
  런타임에 입력받는다. batch는 `cd /d "%~dp0"`로 상대경로를 쓴다.
- 임시 산출물(PDF→PNG 변환 이미지 등)은 `tempfile.TemporaryDirectory()`로
  생성하고, with 블록을 벗어나면 예외 발생 시에도 자동 삭제되게 한다.
  피감 데이터를 디스크에 잔존시키지 않는다.
- 사용자 입력 파일명은 `sanitize_filename()`으로 경로 구분자·위험 문자를
  제거한 뒤 사용한다. 파일 rename 시 `.resolve()` 비교로 원본 폴더를
  벗어나는 경로를 차단한다.
- 고객 데이터 파일(원본 입력, 산출물 등)은 커밋하지 않는다.
  `.gitignore`에 반드시 반영한다. (현재 repo에 `.gitignore`가 없다 —
  아래 "수정 대상" 참고)
- 코드·테스트·시드·예시 데이터 어디에도 실제 고객 데이터를 넣지 않는다.
- OCR은 로컬 EasyOCR 엔진을 쓴다. 모델 최초 1회 다운로드 외에는
  네트워크를 사용하지 않는다.
- 외부 라이브러리를 추가하기 전에 반드시 확인을 받는다.

## 폴더 구조

```
audit_toolbox.py      진입점 / 런처
pages/                1~12 도구 페이지 (N_Name.py)
run.bat               환경 구성 + localhost 실행 스크립트
.venv/                가상환경 (커밋 금지)
```

`shared/`·`utils/` 공통 모듈 폴더가 없다. `tests/`도 없다.
공통 코드(`parse_dt`, 엑셀 스타일 상수 등)가 페이지마다 복붙된 상태다 —
아래 "수정 대상" 참고.

## 기술 스택

Python / Windows / Streamlit 멀티페이지.

의존성은 통합 `requirements.txt` 없이 `run.bat` 안에서 직접
`pip install`된다. batch 기준 핵심 패키지: streamlit, pandas, openpyxl,
python-dateutil, PyMuPDF, easyocr, pdf2image, Pillow, tqdm.

버전 핀이 확인된 것: streamlit 1.44.1, pandas 2.2.3, openpyxl 3.1.5.
(XlsxWriter, holidays가 일부 페이지에서 추가로 쓰일 가능성이 있으나
미확인 — 해당 페이지 확인 전까지 표준으로 간주하지 않는다.)

외부 시스템 의존성으로 Poppler가 필요하다
(`winget install oschwartz10612.Poppler`).

## 표준 결정 (변경 시 확인 필요)

**엑셀 생성 표준** — 이 repo에서 가장 일관되게 굳어진 부분이다.
새 페이지를 만들거나 기존 페이지를 고칠 때 이 규약을 따른다.

- 엑셀 스타일은 파일 상단에 모듈 상수로 고정한다:
  `HF`/`HN`(헤더 — 남색 `002060` 바탕 + 흰색 굵은 글씨), `TF`(제목),
  `SecF`/`SecN`(섹션 머리 — `D6DCE4`), `NF`(본문), `BF`(굵은 본문),
  `HL`(당해연도 강조 — 노랑 `FFF2CC`).
- 색 의미를 고정한다: 노랑 = 당해연도 행, 보라(`E8DAEF`) = 현재가치
  할인차금 스케줄, 초록(`E2EFDA`) = 복구충당부채 스케줄,
  빨강 글씨(`FF0000`) = 차이 과소, 파랑 글씨(`0000FF`) = 차이 과대
  또는 입력값.
- 숫자 서식도 상수로 고정한다: `NM='#,##0'`, `DT='YYYY-MM-DD'`,
  `PC='0.00%'`.
- 폰트는 전부 맑은 고딕. 테두리는 thin, 색 `B0B0B0`.
- 헬퍼 함수 규약: `shdr`(헤더행), `scell`(서식셀), `sec`(섹션 머리),
  `ir`(정보행).
- 엑셀 산출물은 `BytesIO` 버퍼로 만들어 `st.download_button`으로만
  내보낸다. 디스크에 쓰지 않는다. (12_OCR.py는 현재 디스크에도 저장 —
  아래 "수정 대상" 참고)
- 재계산 결과는 `st.session_state`에 저장한다.
- 기준일 입력 기본값은 `date(2025,12,31)`.
- 날짜 파싱은 `parse_dt()`를 쓴다 — `%Y-%m-%d`, `%Y/%m/%d`,
  `%Y.%m.%d`, `%Y%m%d` 4형식 지원.
- OCR 라이브러리: 자유형 한글 텍스트는 EasyOCR(이 repo 채택),
  표 중심 문서는 PaddleOCR PP-Structure.

## 명령어

- 실행: `run.bat`
  (최초 실행 시 `.venv` 생성 + 패키지 설치를 자동 수행)
- 직접 실행: `streamlit run audit_toolbox.py --server.address localhost`
- Poppler 설치: `winget install oschwartz10612.Poppler`
- 검증: 이 repo에는 현재 자동화 테스트가 없다. 재계산 로직
  (`calc_lease`, `calc_dep` 등)에 대한 검증 루프를 세우는 것이
  우선 과제다. 테스트가 생기기 전까지는 기준 케이스 수기 대조로
  검증한다.

## 코드 스타일

- UI 텍스트·주석·docstring은 한국어로 작성한다.
- 페이지 파일은 `pages/N_Name.py` 번호 접두사 규칙을 지킨다.
- 계산 로직 파일은 압축 스타일(세미콜론 다중문, 짧은 변수명)을
  허용한다 — 기존 코드와의 일관성을 우선한다.
- 비싼 초기화는 `@st.cache_resource`로 감싼다
  (OCR 리더, 의존성 체크 등).
- 표준 페이지 흐름: `file_uploader` → 컬럼 매핑 `selectbox` →
  재계산 버튼 → 결과 `metric` + `dataframe` → 엑셀 `download_button`.

## 수정 대상 (코드에서 발견)

1. **`.gitignore` 없음.** `.venv/`가 repo 최상위에 있는데 `.gitignore`가
   없다. 이 상태로 GitHub에 올리면 수백 MB 가상환경이 통째로 커밋된다.
   GitHub 업로드 전에 `.gitignore`를 만들어 `.venv/`, 피감 데이터 파일,
   산출물을 제외해야 한다.

2. **중복 코드 — 공통 모듈 추출 후보.** `parse_dt()`와 엑셀 스타일
   상수(`HF`, `HN`, `NM`, `shdr`, `scell` 등)가 `4_Lessee_Basic`·
   `10_Depreciation`·`12_OCR`에 그대로 복붙돼 있다. 12페이지 전체라면
   같은 코드가 10번 넘게 반복된다. `shared/excel_style.py` +
   `shared/dateutil.py` 같은 공통 모듈로 빼는 것이 맞다.

3. **12_OCR.py의 디스크 저장.** 다른 페이지는 엑셀을 `BytesIO`로만
   내보내는데, 12_OCR은 `download_button`과 별개로 `output_dir`에
   파일로도 저장한다. 피감 의사록 OCR 원문이 사용자 지정 폴더에
   남는다는 뜻이라 "피감 데이터 디스크 잔존 최소화" 원칙과 부딪힐 수
   있다. 의도된 동작인지 확인이 필요하다.

4. **통합 requirements.txt 없음.** 의존성이 `run.bat`의 `pip install`
   줄에만 존재한다. 버전 관리·재현성·GitHub 가독성을 위해
   `requirements.txt`로 분리하는 것이 좋다.
