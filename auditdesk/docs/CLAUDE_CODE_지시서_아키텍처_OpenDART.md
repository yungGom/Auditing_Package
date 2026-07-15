# [Claude Code 작업 지시] DSD 파이프라인 이후 단계: 아키텍처 재편 + OpenDART 연동

> 이 문서는 claude.ai 기획 세션의 결정사항을 통합한 것이다.
> 기존 참조 문서: DSD_PIPELINE_SPEC.md (구조 불변식·검증 게이트), 한빛정밀_검증데이터셋.md
> 원칙: 패치 하나를 완전히 검증한 후 다음으로 넘어간다. 각 단계의 게이트를 통과하기 전에 다음 단계를 시작하지 않는다.

---

## 0. 보안 원칙 개정 (프로젝트 지침 해석 기준)

기존 지침 "외부 서버 통신 코드는 어떤 이유로도 생성하지 않는다"를 아래와 같이 정밀화한다.
취지는 "고객사 데이터가 밖으로 나가면 안 된다"이다.

- **허용**: 공개 데이터의 **수신** — OpenDART API 호출로 공시·XBRL 데이터를 다운로드하는 것
- **금지**: 고객사 데이터의 **송신** — 업로드, 웹훅, 클라우드 연동, 텔레메트리 일체
- API 키는 로컬 `.env`에만 저장하고 `.gitignore`에 등록한다. 레포에 커밋 금지.
- 이 허용은 아래 ② dart_explorer 앱에만 적용된다. ① dsd_workbench에는 네트워크 코드가 일절 없어야 한다.

---

## 1. 아키텍처 재편: 2-앱 분리 (신뢰 경계 기준)

레포를 아래 구조로 재편한다. 분리 기준은 "다루는 데이터의 기밀성"이다.

```
Auditing_Package/
├── dsd_workbench/          # ① 고객사 DSD 편집 — 완전 오프라인
│   ├── dsd_tool/           #    기존 dsd_tool 코드 이동 (extract/repack/clean)
│   ├── history/            #    수정이력 SQLite
│   └── requirements.txt    #    openpyxl 등 로컬 라이브러리만.
│                           #    requests/httpx 등 네트워크 라이브러리 의존 금지 (주석으로 명시)
└── dart_explorer/          # ② 공개 공시 검색·수집 — OpenDART 수신 전용
    ├── client/             #    OpenDART API 클라이언트
    │                       #    (기존 dart_benchmark_finder.py의 API 코드를 모듈로 분리)
    ├── converters/         #    수신물 → 엑셀/DSD 저장 (dsd_workbench의 파서 재사용 가능하나
    │                       #    import 방향은 explorer→workbench 단방향만 허용)
    ├── cache/              #    다운로드 캐시 (.gitignore)
    └── .env.example        #    OPENDART_API_KEY= (실키는 .env, gitignore)
```

두 앱의 연결은 "폴더에 저장된 파일"로만 한다 (예: explorer로 받은 유사회사 DSD를
workbench의 입력으로 사용). 코드 결합·공유 상태 금지.

**[패치 A-1] 재편 작업**
1. 기존 dsd_tool을 dsd_workbench/ 밑으로 이동, import 경로·테스트 경로 수정
2. dsd_workbench에 네트워크 라이브러리 의존이 없음을 확인하는 테스트 추가
   (requirements 파싱 또는 import 스캔)
3. 게이트: 기존 전체 테스트 통과 + batch_validate 10/10 유지

**[패치 A-2] 수정이력 관리 (감사조서 증빙용)**
1. repack 실행 시마다 history/history.sqlite에 기록:
   - 실행시각, 원본 DSD 경로+SHA1, 출력 경로, 옵션(clean-cr 등)
   - 변경 셀 목록: 시트/행/열/변경전/변경후/reason(edit|clean-cr|note-dedup)
2. CLI: `python -m dsd_tool history [원본.dsd]` — 해당 파일의 수정이력 조회
3. 게이트: repack 2회 실행 후 이력 2건 정확 조회, --dry-run은 기록하지 않음

---

## 2. DART 편집기 버전 관리 (로드맵 항목 1)

**[패치 A-3]**
1. extract 시 meta.xml의 `editver`를 읽어 콘솔 출력 + _MAP 시트 메타영역에 기록
2. `dsd_workbench/KNOWN_VERSIONS.md` 생성: 지금까지 확인된 editver 목록
   (5.049, 5.106, 5.107 등 fixtures에서 수집)과 각 버전에서 G2 통과 여부 표
3. 미확인 editver 감지 시: 경고 출력 + "batch_validate를 재실행하여 KNOWN_VERSIONS.md를
   갱신하라"는 안내 메시지
4. 게이트: fixtures/real 10개에서 editver 정확 추출, 가짜 버전 픽스처로 경고 발동 확인

---

## 3. OpenDART 연동 — 공시 데이터 수집 (로드맵 항목 2·5)

**[패치 B-1] 클라이언트 기반**
1. dart_benchmark_finder.py의 OpenDART 호출 코드를 dart_explorer/client/로 분리
   (corpCode.xml 다운로드·캐시, list.json 검색 포함)
2. 검색 파라미터: 회사명(→corp_code 변환), 조회기간(bgn_de/end_de),
   업종코드(induty_code), 공시유형(pblntf_detail_ty)
3. 캐시: corpCode는 7일, 검색결과는 1일, 다운로드 파일은 영구 (cache/ 하위)
4. 게이트: 실제 상장사 1곳 검색 → rcept_no 목록 정확 반환, 오프라인 재실행 시 캐시 히트

**[패치 B-2] 공시원본 다운로드 → 엑셀/DSD 산출 (항목 2)**
1. document.xml API로 공시서류 원본파일 수신 → cache/{corp_code}/{rcept_no}/
2. **첫 작업: 구조 대조** — OpenDART 원본파일이 기존 dartdb 제공 DSD와 동일 형식인지
   fixtures/real과 비교 리포트 작성 (ZIP 구성, meta.xml, XML 루트, 주석헤더 형식).
   ※ dartdb 특유의 주석번호 오염("N. N.")이 OpenDART 원본에는 없을 가능성이 크다 —
   그 경우 note-dedup 로직이 no-op으로 통과해야 정상 (회귀 테스트 추가)
3. 형식이 같으면: dsd_workbench의 extract를 호출해 엑셀 산출 + DSD 원본 보존
   형식이 다르면: 차이점 리포트만 내고 중단, 기획 세션으로 회신
4. CLI: `python -m dart_explorer fetch "회사명" --year 2025 --report annual --as excel|dsd|both`
5. 게이트: 실공시 3사 왕복 (다운로드→엑셀 변환→시트 구성이 스펙 §3.2와 일치)

**[패치 B-3] XBRL 다운로드 파이프라인 (항목 3)**
전제: 다른 채팅에서 만든 xbrl_extract.py, xbrl_diff.py를 dart_explorer/xbrl/로 복사해둘 것.
1. fnlttXbrl.xml API로 XBRL 원본 ZIP 수신
   - 주의 1: XBRL은 정기보고서(사업/반기/분기) 첨부다. list 검색 시 정기공시 필터로
     사업보고서 rcept_no를 찾아 요청한다 (감사보고서 접수번호 아님)
   - 주의 2: 비상장 소규모는 XBRL 미제출 → "결과 없음" 명확 처리
2. ZIP 압축해제 → 인스턴스 + lab-ko.xml이 같은 폴더에 위치
   → **xbrl_extract.py 무수정으로** 입력 가능 (이 도구는 폴더 내 *lab*ko*.xml을 자동 탐색)
3. 원클릭 CLI: `python -m dart_explorer xbrl "회사명" 2025 --diff 2024`
   (당기·전기 수신 → extract → xbrl_diff까지 자동)
4. 요청 한도 일 20,000건/키 — 캐시 히트 시 재다운로드 금지
5. 게이트: 실제 상장사 1곳의 XBRL을 DART 뷰어 수동 다운로드 파일과 **ZIP 바이트 동일** 확인
   + extract 결과 엑셀이 기존 수동 방식 산출물과 행 수 일치

---

## 4. 이후 단계 (지금 구현하지 않음 — 스코프 밖)

- **웹 UI (항목 4)**: 패치 A·B 전부 게이트 통과 후. FastAPI 라우터로 두 앱을 흡수하고
  React 화면 설계는 Claude Design 브리프로 별도 진행 예정. 지금 UI 코드를 만들지 말 것.
- **신규 계정과목 택사노미 매핑 (항목 6)**: 금감원 택사노미 엑셀 수령 후 별도 패치.
  방향만 기록: xbrlTaxonomy.json API + 한글라벨 유사도 매칭으로 후보 추천,
  최종 선택은 회계사 (자동 확정 금지)
- **기타 (항목 7)**: C3(입력값↔원본 대사), C4(사용중단 요소 점검)가 XBRL 지도상
  개발 1순위 후보 — B-3 완료 후 논의

---

## 5. 작업 순서 요약

```
A-1 (재편) → A-2 (수정이력) → A-3 (버전관리)
→ B-1 (클라이언트) → B-2 (공시원본; 구조대조 먼저) → B-3 (XBRL)
```

각 패치는 게이트 통과 → 커밋(Conventional Commits) → 다음 패치.
게이트 실패 또는 구조 대조에서 예상 밖 차이 발견 시 진행을 멈추고 리포트로 회신할 것.
