# AuditDesk

DART 전자공시(XBRL/DSD) 작성·검증 실무를 지원하는 **완전 로컬 데스크톱형 웹앱**.
최종 산출물은 금감원 편집기에 사람이 전사할 수 있는 **가이드 엑셀**이며,
편집기 업로드·IXD 직접 생성은 의도적으로 범위에서 제외한다.

> 이 폴더에는 별개 앱인 **AuditLink v2**(감사업무 관리, `backend/` + `frontend/`)도 함께 있다.
> 두 앱은 코드 연결이 없으며, AuditLink 통합은 시즌 후 큐에 있다. [아래 참고](#auditlink-v2-별개-앱).

## 기능 축 4개

| 축 | 내용 |
|---|---|
| **DSD ↔ Excel 양방향 변환** | DSD에서 재무제표·주석·표지를 Excel로 추출, 편집된 셀만 **XML 바이트 오프셋 기반으로 정밀 역교체(repack)**. 찾아치환이 아니라 오프셋 방식이므로 중복값 오교체가 구조적으로 불가능 |
| **검증 3종** | ① Footing(합계검증·주석대사) ② 전기대사(당기 보고서 전기열 ↔ 전기 보고서 당기열) ③ DSD ↔ XBRL 인스턴스 대사(태깅 최종 검증) |
| **XBRL 작성 지원** | 상장사 코퍼스 실증 기반 계정과목→element 추천(Top-4, LLM 미사용), 주석 role·축(axis)/member 매핑, 자기 기말 인스턴스 승계, 롤포워드 스캐폴드 |
| **DART 수신·탐색** | OpenDART API 공시 검색·XBRL 수신·차원표 렌더·택소노미 버전 diff/호환성 점검 |

## 설계 원칙

1. **수신 허용 / 송신 금지** — 고객사 데이터는 어떤 경로로도 외부에 나가지 않는다.
2. **신뢰 경계 분리** — `dsd_workbench`(고객사 데이터, 완전 오프라인) ↔ `dart_explorer`(공개 데이터 수신 전용).
   두 앱의 연결은 파일(캐시 경로)뿐이며 코드 import는 금지. 이 경계는
   `dsd_workbench/dsd_tool/tests/test_offline.py`가 네트워크 모듈 import를 소스 전수 스캔하여 **자동 강제**한다.
3. **자동은 추천, 확정은 회계사** — 워크시트에 `확정☐` 열을 두고, 미기입 상태는 "완성 아님"으로 취급한다.
4. **미매칭 ≠ 0** — 미매칭 항목을 숨기지 않고 노출한다.

## 빠른 시작

```bash
RUN.bat        # 원클릭: 프런트 자동 빌드 → 서버 기동(:8710) → 브라우저 오픈
```

수동 실행:

```bash
python -m auditdesk --port 8710      # host는 127.0.0.1 하드코딩 — 외부 바인딩 불가
# API 문서: http://127.0.0.1:8710/api/docs
```

관제 대시보드(읽기 전용):

```bash
python -m dashboard                  # http://127.0.0.1:8700
```

사전 요건: Python, Node/npm. `dart_explorer`는 `.env`에 `OPENDART_API_KEY`(무료 발급) 필요.

## CLI

웹 UI 없이 코어 엔진을 직접 쓸 수 있다.

```bash
cd dsd_workbench
python -m dsd_tool extract|repack|foot|map|map-eval|recon|worksheet|version-check|history ...

python -m dart_explorer search|xbrl|taxtree|dimtable|taxdiff|taxcheck|corpus ...
```

## 디렉터리 구조

```
auditdesk/          FastAPI 라우터층 (REST 43개) + 빌드된 SPA 서빙 — 하위 모듈의 얇은 래퍼
webui/              프런트엔드 (React 18 + TypeScript + Vite) → npm run build 시 auditdesk/static/
dsd_workbench/      오프라인 코어 엔진 (순수 Python + openpyxl 단일 의존성)
  └─ dsd_tool/      extract·repack·foot·recon·worksheet·succession·rollforward + 테스트
dart_explorer/      OpenDART 수신 앱 (requests·lxml·pandas) — 공시 캐시·매핑 코퍼스
dashboard/          E-0 읽기 전용 관제탑 (GATES·테스트결과·코퍼스 진행률 렌더)
docs/               사용설명서·스펙·추적 매트릭스 (아래 참고)
design/             standalone HTML 프로토타입 (참조 구현)
GATES.json          패치별 품질 게이트 대장 — 진척 상태의 단일 소스
backend/ frontend/  AuditLink v2 (별개 앱)
```

## 품질 관리

- **GATES.json** — 패치 단위 품질 게이트 대장(수동 기록). 게이트마다 정량 근거(홀드아웃 정확도, n수,
  바이트 일치 여부 등)를 남긴다. 대시보드와 `/api/status/gates`가 이 파일을 렌더한다.
- **테스트** — 코어(`dsd_tool` ≈97개, `dart_explorer` ≈44개)는 pytest로 두텁게 커버.
  라우터층·webui는 자동 테스트가 없고 브라우저 E2E 게이트(UI-1~5, 수동 기록)로 대체한다.
- **추적 매트릭스** — `docs/IMPL_CHECKLIST.md`가 요청 대장 ↔ 구현 파일 ↔ 게이트 ↔ 테스트를
  순방향/역방향으로 대조한다.

### 의도적 미구현 (스텁 아님)

- IXD 직접 생성 / 바닥부터 DSD 생성 / USERMARK 서식 → **제외 확정**
- 표 행 추가·삭제 → **보류** (repack은 값 교체만 수행)
- `dart4.xsd` 로컬 스키마 사전검증 → **백로그** (현행 안전장치는 바이트 보존 + 바이트 일치 게이트)

## 문서

| 문서 | 내용 |
|---|---|
| `docs/USER_GUIDE.md` | 업무 시나리오 기준 사용설명서 |
| `docs/IMPL_CHECKLIST.md` | 요청 ↔ 구현 ↔ 게이트 ↔ 테스트 추적 매트릭스 |
| `docs/REQUEST_LEDGER.md` | 요청 이력 대장 (단일 소스) |
| `docs/*_SPEC*.md` | 파이프라인·Footing·XBRL 작성지원 등 스펙 문서 |

---

## AuditLink v2 (별개 앱)

Linear 스타일 회계감사 관리 앱 — FastAPI + SQLAlchemy + SQLite 백엔드, Vite + React 19 + Tailwind 프론트엔드.

```bash
start-auditlink.bat    # 최초 1회 venv/npm 구성 → backend :8000 + frontend :5173
```

수동 실행:

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000
python seed.py                          # 데모 데이터 로드 (선택)
```

```bash
cd frontend
npm install
npm run dev                             # http://localhost:5173
```

**기능**: 대시보드(진척률·마감일·캘린더) / 감사업무(FY→Client→Engagement→Phase→Account 트리,
할일·PBC·인터뷰) / 내부회계(ICFR 테이블·RCM 편집) / 템플릿 / 설정 / Ctrl+K 전역 검색.
백엔드 pytest 29개.

**서버 강제 규칙**: 활성 FY는 항상 하나 · 모든 write 응답이 저장된 객체 반환 ·
빈 DB로 시작(mock 없음, `seed.py`로 별도 데모 로드) · `GET /api/engagement-tree`는 모든 FY 반환.
