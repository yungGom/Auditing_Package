# 설계안 — UI 셸 U-2 (좌측 목록) · 승인 대기, 구현 착수 전

> 상태: **설계안만. 승인 전 구현 금지.**
> 범위: `marks.json`을 읽어 좌측 목록만 그린다. 지면 연동(클릭→점프)은 U-3,
> 좌표 매칭은 U-4, 상세 패널·판단 버튼은 U-5.
> `marks.py`/`render.py`/`final.py`/`core.py` 등 **무수정** — `ui/` 아래만 건드린다.

---

## 0. 확인한 데이터 (조선내화 반기, 이 설계의 근거)

```
document.counts = {ok: 130, diff: 14, unverified: 4, recon: 58, prose: 109, typo: 2}
marks[] = 18건 (전부 status="pending" — 판단 버튼이 아직 없어 당연함)
annotations[] = 299건
L2 마크(l2_class 있는 것) = 10건, 전부 counterparts 있음
```

---

## 1. marks.json 조달 — 브리지 재사용

`ui/api.py`의 `Api`에 `get_marks()`를 추가한다. `get_pdf()`와 같은 패턴(프로세스 내
호출, HTTP 아님) — 게이트 5에 영향 없다.

파일 경로는 `foot.py`의 명명 규칙(`<원본>_marks.json` / `<원본>_틱마크.pdf`, 둘 다
같은 `<원본>` 베이스)에서 역산한다: `app.py`가 받는 인자가 `..._틱마크.pdf`로
끝난다는 전제로 그 접미사를 떼고 `_marks.json`을 붙인다.

```python
# app.py
if pdf_path.endswith("_틱마크.pdf"):
    marks_path = pdf_path[: -len("_틱마크.pdf")] + "_marks.json"
else:
    marks_path = None   # foot.py 산출물이 아닌 PDF로 실행된 경우 — 목록 없이 지면만
```

marks.json이 없거나(구형 산출물, 또는 원본 PDF를 직접 넘긴 경우) 못 읽으면
`get_marks()`가 `{"error": ...}`를 낸다. **PDF 표시는 목록과 독립**이다 — 목록을
못 읽어도 지면은 그대로 보여야 한다(사이드바에 "목록을 불러올 수 없습니다"만
표시, 전체 화면이 죽지 않음).

---

## 2. 레이아웃 — 기존 index.html/viewer.css 확장

```
┌──────────────┬───────────────────────────┐
│ 사이드바(좌)  │  기존 U-1 툴바 + 캔버스      │
│ 카운터        │                            │
│ 필터 탭       │                            │
│ 목록(스크롤)   │                            │
└──────────────┴───────────────────────────┘
```
U-1의 `#toolbar`/`#canvasWrap`는 그대로 두고, `<aside id="sidebar">`를 추가해
flex row로 좌우 배치한다(폭 약 300px 고정, 본문이 나머지). 신규 파일
`ui/web/sidebar.js`(목록 로드·렌더·필터)로 관심사를 분리한다 — `viewer.js`(지면)는
건드리지 않는다.

---

## 3. 카운터 — 확인 필요한 매핑 1건

요청하신 3줄:
```
"차이 N건 중 M건 미검토"
"확인 필요 N건"
"대사 완료 N건"
```

- **"확인 필요 N건"** = `document.counts.unverified` (4건) — 그대로.
- **"차이 N건 중 M건 미검토"** — N은 `document.counts.diff`(14건, 지시대로 배열을
  안 세고 이 값을 씀). **M(미검토)은 document.counts에 없는 값이다** — `status`별
  세부 집계는 애초에 marks.py가 만들지 않는다(분석 시점엔 전부 `pending`이라
  의미가 없고, `status`는 화면에서 바뀌는 UI 상태라 분석 산출물에 박아둘 수 없는
  값이다). U-5(판단 버튼) 전까지는 실질적으로 M=N이지만, 그래도 지금부터 구조를
  맞춰 둔다: **M은 로드된 `marks[]`를 `status==="pending"`으로 세는 것으로
  계산한다.** "배열을 세지 마라"는 지시는 document.counts에 이미 있는 총계를
  중복 계산하지 말라는 뜻으로 이해했고, status 세부값은 애초에 그 총계에 없으므로
  예외로 다룬다 — 이 해석이 맞는지 확인 부탁드린다.
- **"대사 완료 N건"** — ★애매함이 있다. 후보 둘:
  - `document.counts.recon`(58건, C 레퍼·L2 대사 성립 — "대사"라는 용어를
    프로젝트 전체가 이 의미로 씀, 설계안_marks_스키마_v2.md도 recon을 "대사 표시"로
    정의)
  - `document.counts.ok`(130건, A1/A2 세로합 체크)
  **recon으로 제안합니다** — "대사"라는 단어가 이 프로젝트에서 줄곧 B/C/L2
  표간·레퍼 대사를 가리켜 왔고(L2 표간 대사, C 본표주석 레퍼 대사), 세로합
  체크(ok)는 보통 "검산 완료"라고 부르지 "대사 완료"라 안 부릅니다. 다른 뜻이면
  바로잡아 주십시오.

---

## 4. 필터·정렬

- 탭: 차이 / 확인 필요 / 모두. 클릭 시 `marks[]`를 `type`으로 필터(클라이언트
  메모리 내 배열 필터 — 이건 "목록 표시"를 위한 정상적 동작이지, 카운터 재계산이
  아니다).
- "모두" 탭 정렬: **차이 그룹 전체 → 확인 필요 그룹 전체**, 그룹 내부는 `page`
  오름차순(지면 순서와 일치, 다른 기준이 필요하면 알려주십시오).

---

## 5. 시각 사양 반영

| 요청 | 구현 |
|---|---|
| 라이트 UI, 색 3종 | 배경 흰색, UI 회색조(테두리·보조텍스트), 마크 표시만 빨강. CSS 변수 3개로 고정해 실수로 색이 늘어나는 걸 막는다 |
| 행 32~36px | `.row { min-height: 34px }` |
| 텍스트 2종 | `--fs-title`(account), `--fs-meta`(page·delta) 두 값만 정의, 그 외 크기 사용 금지 |
| 금액 고정폭 | `font-variant-numeric: tabular-nums` (별도 모노스페이스 폰트 없이 지원되는 폰트면 이걸로 충분 — Pretendard는 지원) |
| ✗ 원색 / ? 중간 강도 | 행 좌측에 작은 표시자: diff는 `--red`(불투명), unverified는 `--red`에 `opacity: .55` |
| 상태 = 점·취소선·회색 | `pending`(회색 점) / `approved`(취소선+회색 후퇴) / `removed`(목록에서 제외). **U-2 데이터엔 pending만 있어 approved·removed 경로는 코드는 넣되 실물로는 확인 못 함** — U-5에서 재확인 필요 |

### 폰트 — 승인 필요 (pdf.js와 같은 성격의 1회 조달)
Pretendard를 **로컬 임베딩**하려면 폰트 파일을 vendoring해야 한다(pdf.js를
GitHub 릴리스에서 받은 것과 같은 절차). 이번엔 목록 텍스트에 쓸 굵기 2개만
받는다(제목용 Medium/SemiBold, 본문용 Regular) — 가변폰트 전체(수 MB) 대신
정적 서브셋을 받아 용량을 줄인다. 출처는 Pretendard 공식 GitHub 릴리스(SIL
Open Font License, 재배포 자유). 본고딕(Noto Sans KR)·Apple SD Gothic Neo는
**별도로 받지 않고 CSS 폴백 이름으로만** 넣는다 — Pretendard 임베딩이 실패하는
극히 드문 경우의 안전망일 뿐이라, 그것까지 vendoring할 필요는 없다고 판단했다.
**이 조달(1회 다운로드) 진행해도 되는지 승인 요청.**

---

## 6. 게이트 자동화 — CDP로 대부분 확인 가능 ★U-1과의 차이

U-1은 "PDF가 눈으로 보기에 맞는가"라 화면 합성(스크린샷)이 꼭 필요했다. U-2는
"DOM에 옳은 값이 옳은 구조로 들어갔는가"라 **스크린샷 없이 CDP `Runtime.evaluate`
+ Playwright locator만으로 전부 자동 확인 가능**하다고 판단했다 — U-1에서 확인한
대로 CDP 접속·DOM 조회·클릭은 이 환경에서 정상 동작한다(안 되는 건 픽셀 캡처뿐).

| 게이트 | 확인 방법 | 자동/수동 |
|---|---|---|
| 1. marks 18건만(annotations 미혼입) | `document.querySelectorAll('[data-mark-id]').length === 18` | 자동 |
| 2. 상단 카운터 = document.counts | 브리지로 받은 원본 JSON의 counts와 DOM 텍스트/데이터속성 대조 | 자동 |
| 3. L2 10건에 counterparts 데이터 존재 | JS 메모리 상태를 `evaluate`로 꺼내 `l2_class` 있는 항목 전부 `counterparts.length>0` 확인 | 자동 |
| 4. 필터 전환 시 건수 일치 | 각 탭 클릭 → 보이는 행 수 vs 사전 계산값(14/4/18) | 자동 |
| 5. 네트워크 0건 | CDP Network 리스너를 **페이지 로드 전에** 등록(U-1 테스트가 로드 후 2.5초 뒤에 붙여 초기 요청을 놓쳤던 것 — 결정 15 보완, 이번엔 `page.on` 등록 후 `page.reload()`로 재현) | 자동 |
| 색·크기·폰트 사양(§5 표) | `getComputedStyle()`로 값 자체는 확인 가능(색상 hex, 폰트 로드 여부 `document.fonts.check()`, 행 높이 `getBoundingClientRect()`) | 자동(수치 확인) — "보기에 좋은가"라는 최종 인상만 사람 몫 |

**결론: 이번 라운드는 사람 눈으로 볼 체크리스트가 필요 없을 가능성이 높습니다.**
구현 후 위 표대로 자동 확인해 결과를 보고하고, 정 애매한 게 남으면(예: 색이
수치상 맞는데 실제로 이상해 보이는 경우) 그때만 스크린샷 대신 **"이 명령을
직접 실행해서 봐 주십시오"** 형태로 최소한만 요청하겠습니다.

---

## 7. 게이트 보호
- `marks.py`/`render.py`/`final.py`/`core.py`/`statements.py`/…(L1/L2/렌더 전체)
  무수정. `ui/` 아래 파일(신규 `sidebar.js`/`sidebar.css`/폰트, 기존 `api.py`/
  `app.py`/`index.html`/`viewer.css`에 추가만)만 바뀐다.
- `GATES.json`/`RENDER_GATES.json` 무수정 — 대상 코드 비접촉이라 재실행도
  이론상 불필요하지만, 완료 후 1회 실측 확인은 하겠습니다(관행 유지).

---

## 8. 승인 요청 정리

| # | 항목 | 권장 |
|---|---|---|
| A | "차이 N건 중 M건 미검토"의 M을 `marks[]` status 카운트로 계산(§3) | 진행, 해석 확인 요청 |
| B | "대사 완료 N건" = `counts.recon`인지 `counts.ok`인지(§3) | **recon 권장**, 확정 요청 |
| C | Pretendard 폰트 1회 다운로드(정적 2웨이트만, §5) 진행 여부 | 승인 요청 |
| D | "모두" 탭 그룹 내부 정렬 = page 오름차순(§4) | 다르면 지정 요청 |

승인해 주시면 착수하겠습니다.
