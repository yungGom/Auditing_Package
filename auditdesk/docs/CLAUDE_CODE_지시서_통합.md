# [Claude Code 작업 지시서 · 통합본] 아키텍처 재편 + Footing 검증 + OpenDART 연동

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

## 3. [패치 A-4] Footing 검증 — DSDbreaker VBA 로직 분석 기반

> 원전: DSDbreaker(실무 검증된 엑셀 풋팅 매크로) CB1_Footing.bas 역분석. 알고리즘은 아래에 완역되어 있으므로 원본 xlam 파일은 불필요.
> 목표: dsd_workbench에 합계검증·주석대사 기능 추가 (시장 검증된 기능군 — KPMG Footing Master 대응)

---

### 3-1. DSDbreaker 핵심 알고리즘 (검증된 실무 로직 — 그대로 채택)

#### 1.1 값 기반 계층 역추론 (키워드 불사용!) ★핵심
"합계/총계" 같은 계정명 키워드에 의존하지 않는다. 대신:

```
subTotal = 0
for i in 노드들(위→아래):
    if 노드i가 아직 부모 없음 and 값 있음:
        subTotal += 노드i.값
    if |subTotal - 노드(i+1).값| <= limit:   # limit = 2 (단수차 한도)
        노드(i+1)이 부모(합계행) → 누적된 노드들을 자식으로 연결
        subTotal 리셋, 계속
# 트리 미발견 시 시작 노드를 하나씩 뒤로 밀며(targetNode+1) 재시도
# 전제: 합계가 아래에 오는 "하단 합계" 방식 (한국 재무제표 관행)
```
- 반복 적용으로 다단 계층(소계→중계→총계) 트리 완성, depth 인버스 → 레벨
- **행·열 양방향 각각 수행** (row 트리 + column 트리 → 교차 검증)

#### 1.2 수동 오버라이드 + 판정 결과 노출 (UX 핵심)
- 자동 판정한 레벨을 표 우측(행)/하단(열)에 **숫자로 기록해 보여줌**
- 사용자가 그 숫자를 수정하면 다음 실행 때 수동 레벨 우선 (getNodeTreeByLevel)
- → "자동은 추천, 최종 판단은 회계사" 원칙의 교과서적 구현

#### 1.3 허용 오차 정책
- 합계검증 단수차 한도: **±2**
- 값 매칭(주석대사): **±2**, 절대값 비교 `|abs(a)-abs(b)| <= 2`
  → 괄호음수/부호 표기 차이를 자동 흡수

#### 1.4 주석대사 (getSameValueCell + getRefComment)
- 검증 대상 값과 같은 값(±2)을 가진 셀을 다른 시트(BS/PL/CE/CF 우선)에서 탐색
- 참조 발견 시 코멘트 생성: `{시트/헤더}\n-{행라벨}/{열라벨}: {값}`
- 행/열 라벨은 병합셀(MergeArea) 고려, 2단 헤더면 "라벨1-라벨2" 결합

---

### 3-2. 우리 구현의 구조적 이점 (DSDbreaker 대비)

| 항목 | DSDbreaker (엑셀 애드인) | 우리 (dsd_tool 위) |
|------|--------------------------|--------------------|
| 테이블 탐지 | 시각 구조에서 추측 (getTableRanges, isLeftTop 등 400줄) | **불필요** — XML TR/TD/THEAD로 구조 확정 |
| 값 영역 탐지 | findValueRegionInTable 휴리스틱 | **불필요** — try_number로 이미 판별 |
| 주석 매핑 | 값으로만 추측 | 값 + **주석참조 텍스트("5", "6, 23")** 결합 가능 → 더 정확 |
| 결과 표시 | 시트에 직접 기입 | 별도 검증 리포트 시트 + 레벨 컬럼 (원본 오염 없음) |
| 역변환 | 없음 (검증 전용) | 검증 통과 후 repack까지 일관 |

---

### 3-3. 구현 스펙

#### 3.1 CLI
```
python -m dsd_tool foot 편집용.xlsx [--limit 2] [--report]
```
- 대상: FS 시트(BS/PL/PL1/CE/CF) + 주석 시트의 테이블
- 출력: `_FOOT` 리포트 시트 생성 + 콘솔 요약 (일치 N / 단수차 M / 불일치 K)

#### 3.2 검증 3종
1. **합계검증**: §1.1 알고리즘으로 행·열 트리 추론 → 각 부모 = Σ자식 재검산
   - 결과: 일치(무표시) / 단수차 ±limit 이내(노랑) / 불일치(빨강 + 차이액)
2. **주석대사**: FS 셀의 주석참조("5", "6, 23") → 해당 주석 시트에서 같은 값(±2) 탐색
   - 참조 텍스트가 없으면 DSDbreaker 방식(전 시트 값 탐색)으로 폴백
   - 결과: 찾음(참조 위치 기록) / 못찾음(플래그)
3. **전기대사** (2개 파일 모드): `foot 당기.xlsx --prior 전기.xlsx`
   - 당기 파일의 "전기 열" ↔ 전기 파일의 "당기 열" 계정명 매칭 비교

#### 3.3 레벨 오버라이드
- _FOOT 시트에 행별 추론 레벨 기록. 사용자가 수정 후 재실행하면 수동 레벨 우선
- DSDbreaker와 동일한 워크플로우, 단 원본 시트가 아닌 _FOOT 시트에서

#### 3.4 게이트
- G-F1: 한빛정밀 데이터(대사 완결 설계)로 전 항목 "일치" 판정
- G-F2: 한빛정밀에서 셀 1개를 +1 변조 → 해당 트리만 단수차 검출, 나머지 무영향
- G-F3: 삼성전자 실파일 BS/PL 합계검증 통과율 리포트 (실패 케이스는 원인 분류)
- G-F4: 주석대사 — BS "주석 5" 현금 ↔ 주석5 합계 매칭 확인

#### 3.5 스코프 제외 (이번 패치에서 안 함)
- 웹 UI (Footing Master식 대시보드) — Phase C에서
- 상단 합계 방식, 가로 누적 합계 등 비표준 배치 — 실파일에서 발견 시 후속


---

## 4. OpenDART 연동 — 공시 데이터 수집 (로드맵 항목 2·5)

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

## 5. 이후 단계 (지금 구현하지 않음 — 스코프 밖)

- **웹 UI (항목 4)**: 패치 A·B 전부 게이트 통과 후. FastAPI 라우터로 두 앱을 흡수하고
  React 화면 설계는 Claude Design 브리프로 별도 진행 예정. 지금 UI 코드를 만들지 말 것.
- **신규 계정과목 택사노미 매핑 (항목 6)**: 금감원 택사노미 엑셀 수령 후 별도 패치.
  방향만 기록: xbrlTaxonomy.json API + 한글라벨 유사도 매칭으로 후보 추천,
  최종 선택은 회계사 (자동 확정 금지)
- **기타 (항목 7)**: C3(입력값↔원본 대사), C4(사용중단 요소 점검)가 XBRL 지도상
  개발 1순위 후보 — B-3 완료 후 논의

---

## 6. 작업 순서 요약

```
A-1 (재편) → A-2 (수정이력) → A-3 (버전관리) → A-4 (Footing 검증)
→ B-1 (클라이언트) → B-2 (공시원본; 구조대조 먼저) → B-3 (XBRL)
```

각 패치는 게이트 통과 → 커밋(Conventional Commits) → 다음 패치.
게이트 실패 또는 구조 대조에서 예상 밖 차이 발견 시 진행을 멈추고 리포트로 회신할 것.
