# -*- coding: utf-8 -*-
"""
DSD 풋팅 엔진 v2 — 격자(extract_tables) 기반
Tier 1: A1 세로합 / A2 가로합 / A3 계층합 / A7 단수차이 / F1 단위
완전 오프라인. 외부 통신 없음.
"""
import re, unicodedata

# ── 값 파싱 ────────────────────────────────────────────────
BLANKS = {"", "-", "–", "—", "‐", "ㅡ", "N/A", "해당없음"}
NUMRE  = re.compile(r"^\(\s*(?P<p>[\d,]+(?:\.\d+)?)\s*\)$|^(?P<s>[-△▲])?\s*(?P<n>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)$")

def norm(c):
    if c is None: return ""
    return unicodedata.normalize("NFKC", str(c)).replace("\n", "").strip()

def parse(cell):
    """→ (kind, value)  kind: NUM / BLANK / TEXT"""
    t = norm(cell)
    if t in BLANKS: return "BLANK", 0.0
    t2 = t.replace(" ", "")
    m = NUMRE.match(t2)
    if not m: return "TEXT", None
    if m.group("p"): return "NUM", -float(m.group("p").replace(",", ""))
    v = float(m.group("n").replace(",", ""))
    return "NUM", (-v if m.group("s") else v)

# ── 라벨 판정 ──────────────────────────────────────────────
TOTAL_LAB = re.compile(r"^(합\s*계|계|총\s*계|소\s*계|합|Total|계\(.*\)|.*총\s*계)$", re.I)
SUB_LAB   = re.compile(r"^(소\s*계)$")

def is_total_label(t):
    """조선내화 교차검증에서 확장: '비파생상품 합계'처럼 짧은 수식어가 붙는 구간
    합계행을 총계행으로 인식 ([가-힣]{0,6}). 미인식 시 구간 검증이 침묵 소실되고
    말미 총합이 구간 합계를 이중 합산한다 (LGES p21)."""
    t = norm(t).replace(" ", "")
    return bool(re.fullmatch(r"(합계|계|총계|소계|Total|[가-힣]{0,6}(총계|합계))", t, re.I))

def is_sub_label(t):
    return norm(t).replace(" ", "") == "소계"

# ── 단위 (F1) ──────────────────────────────────────────────
UNIT = re.compile(r"\(\s*단위\s*[:：]?\s*([^)]+?)\s*\)")
UNIT_MULT = {"원":1, "천원":1_000, "백만원":1_000_000, "억원":100_000_000,
             "천주":1_000, "주":1, "%":None, "USD":None, "천USD":None}

def find_unit(page_text):
    m = UNIT.findall(page_text or "")
    return m[0] if m else None

# ── 표 구조 분석 ───────────────────────────────────────────
NOTE_HDR = re.compile(r"^(주\s*석|비\s*고|참\s*조|Note|Ref)$", re.I)

def is_note_col(G, K, V, hdr, nrow, j):
    """주석번호·연번 열 판정 → 금액열에서 배제"""
    for i in range(hdr):
        if NOTE_HDR.match(norm(G[i][j]).replace(" ", "")): return True
    cells = [(G[i][j], V[i][j]) for i in range(hdr, nrow) if K[i][j] == "NUM"]
    if not cells: return False
    nocomma = sum(1 for t, v in cells if "," not in t)
    small   = all(abs(v) < 100 for t, v in cells)
    return (nocomma / len(cells) >= 0.8) and small

def grid_info(tb):
    """헤더행 수, 열별 숫자셀 수"""
    nrow = len(tb); ncol = max(len(r) for r in tb)
    G = [[norm(c) for c in r] + [""]*(ncol-len(r)) for r in tb]
    K = [[parse(c)[0] for c in r] for r in G]
    V = [[parse(c)[1] for c in r] for r in G]
    hdr = 0
    for i in range(min(3, nrow)):
        if sum(1 for k in K[i] if k == "NUM") == 0: hdr = i+1
        else: break
    numcols = [j for j in range(ncol) if sum(1 for i in range(hdr, nrow) if K[i][j] == "NUM") >= 2]
    numcols = [j for j in numcols if not is_note_col(G, K, V, hdr, nrow, j)]
    return G, K, V, hdr, ncol, nrow, numcols

def total_col_idx(G, hdr, ncol, numcols):
    """헤더에 계/합계가 있는 열"""
    out = []
    for j in numcols:
        for i in range(hdr):
            if is_total_label(G[i][j]): out.append(j); break
    return out

# ── 적용 부적합 제외 ───────────────────────────────────────
EXCL_TABLE = ("시간", "인원")        # 감사시간·투입인원 표 → 풋팅 대상 아님 (SKIP)
# EXCL_LABEL(법인세효과·세후 데이터 행 라벨 트리거)은 폐지됨 — 4축 SKIP 감사에서
# 조선내화 이연법인세 일시적차이 표(단순 가산) 12건을 과잉 제외한 것이 확인됨.
# 제외 트리거는 헤더 열 구성으로 판정한다는 원칙. 종전 대상이던 삼성 p38(세효과
# 가감 표)은 역방향 역산(기말 = 기초+평가+대체 커버)이 대신 정확히 검증한다.

def _excl_table(G, hdr, ncol, nrow, labels=None):
    """헤더나 라벨에 시간·인원이 있는 표 — 검증은 등재하되 미검증(SKIP)"""
    lab = labels if labels is not None else [G[i][0] for i in range(nrow)]
    return any(kw in G[i][j] for kw in EXCL_TABLE for i in range(hdr) for j in range(ncol)) \
        or any(kw in lab[i] for kw in EXCL_TABLE for i in range(hdr, nrow))

# 전기 재작성(정책 변경·오류 수정) 내역표 — 영향 계정과 그 상위 계층만 발췌된 표라
# 표시 행이 완전한 가산 집합이 아니다(상위+하위 이중 합산 → 정확히 2배 서명).
# 헤더에 아래 신호 2개 이상 공존할 때만 발화(단일 라벨 트리거 금지).
RESTATE_HDR = ("이전보고금액", "수정금액", "재작성후금액")

def _restate_table(G, hdr, ncol):
    flat = [G[i][j].replace(" ", "") for i in range(hdr) for j in range(ncol) if G[i][j]]
    return sum(1 for kw in RESTATE_HDR if any(kw in c for c in flat)) >= 2

# 복합 통화 표 — 단위 문자열에 통화 토큰이 2종 이상이면 발화 (표 단위 신호).
# 서로 다른 통화를 더한 값은 어떤 단위로도 존재하지 않는 수다 → A2 가로합 제외.
CUR_TOK = re.compile(r"(USD|VND|PLN|EUR|JPY|CNY|GBP|원)")

def mixed_currency(unit_text):
    return len(set(CUR_TOK.findall(norm(unit_text or "")))) >= 2

# ── 검증 ───────────────────────────────────────────────────
def absorb_subtotal(vals):
    """성분 값 배열에서 '앞 연속 구간의 합 = 그 다음 성분'인 중간 소계의 위치를 찾는다.

    두 단계로 조판된 표에서 평면 합산이 중간 소계를 이중계상하는 것을 막는다.
    실물은 충당부채 롤포워드다 — `기초 + 전입 − 사용액 = 기말`, `기말 − 차감:유동항목
    = 합계`(K-IFRS 1037.84가 요구하는 표준 양식이라 회사마다 바뀌지 않는다).
    `statements._absorbed`(A5 커버리지 점검)와 같은 성질이고, 여기는 성분 배열
    인덱스 기반이라 구현만 다르다.

    ⚠ **구간에 0이 아닌 값이 2개 이상**일 것을 요구한다(2026-08-28 승인). 소계는
    최소 두 개의 실제 금액을 요약한 것이기 때문이다. 이 조건이 없으면 값이 대부분
    '-'인 표에서 `3 + 0 = 3` 같은 우연의 일치가 소계로 잡힌다 — 삼성 p102 종속기업
    거래내역(기업 25개 × 독립 금액, 소계 구조 자체가 없음)에서 정상 OK가 DIFF로
    깨지는 것을 실측했다. 금액 임계값(예: 1,000 미만 무시)을 쓰지 않은 이유는 표시
    숫자 기준 임계값이 단위에 따라 100만 배 다르게 작동하기 때문이다(결정 10과 같은
    함정). '소계는 둘 이상을 요약한다'는 구조 조건이라 금액 크기·단위와 무관하다.
    """
    out = set(); n = len(vals)
    for i in range(n):
        s = 0.0; nz = 0
        for j in range(i, n):
            s += vals[j]
            if abs(vals[j]) > 0: nz += 1
            k = j + 1
            if j - i + 1 < 2 or k >= n or nz < 2: continue
            if abs(s - vals[k]) < 0.5 and abs(vals[k]) > 0:
                out.add(k)
    return out

def check_table(tb, tol=0.0, x0s=None, sublog=None, ctx=None, excl_a2=False):
    """A1 세로합 · A2 가로합 · A3 계층합 수행 → 결과 리스트

    x0s    : 행별 첫 열 라벨의 x0 좌표 (들여쓰기 하위항목 판정용, 없으면 None)
    sublog : 하위항목 판정 로그 수집 리스트 (경로별 검증용)
    ctx    : (page, table) — 로그 표기용
    excl_a2: 복합 통화 표 — A2 가로합만 미검증(SKIP), A1 세로합은 유지
    """
    G, K, V, hdr, ncol, nrow, numcols = grid_info(tb)
    res = []
    if not numcols: return res
    # 라벨 좌표 병합 — 라벨을 c0 고정이 아니라 '첫 금액열 왼쪽의 첫 TEXT 셀'로 정한다.
    # 구분류가 c0(병합·희소)이고 계정·소계가 c1인 조판(조선내화 p48~50)에서 c1의
    # '소 계'가 보이게 한다. c0에 라벨이 있으면 종전과 완전히 동일하게 동작한다.
    first_num = min(numcols)
    LC = []
    for i in range(nrow):
        lj = 0
        for j in range(first_num):
            if G[i][j] and K[i][j] == "TEXT": lj = j; break
        LC.append(lj)
    LBL = [G[i][LC[i]] for i in range(nrow)]
    # 미검증 사유 — n=0으로 떨어뜨릴 때 '왜'를 함께 실어 보낸다. 종전에는 verdict="SKIP"만
    # 남고 사유가 버려져 화면·조서에 쓸 문장을 만들 수 없었다(2026-08-25 승인).
    # ⚠ 판정값(n)은 바꾸지 않는다 — 아래 excl_tab의 불리언 값은 종전과 완전히 동일하다.
    excl_reason = None
    if _excl_table(G, hdr, ncol, nrow, LBL): excl_reason = "AUDIT_HOURS"
    elif _restate_table(G, hdr, ncol):       excl_reason = "RESTATEMENT"
    # 복합 통화 + '통화' 헤더 열 = 행별 통화 표(합계행도 통화별 분리) — 세로합도
    # 통화를 섞으므로 표 전체 SKIP. 헤더 열 구성 판정 원칙 부합 (휴맥스 실측:
    # 복합 표 전원이 이 구조, 열별 통화 표는 0개).
    cur_col = any(re.fullmatch(r"통\s*화", G[i][j]) for i in range(hdr) for j in range(ncol))
    if excl_a2 and cur_col and excl_reason is None: excl_reason = "MIXED_CURRENCY"
    # 민감도 분석 표 — 상승시/하락시가 '행'으로 섞이면 부호 대칭 쌍이라 세로합
    # 부적합 (SKIP). 헤더 '열'로 분리된 민감도 표(10% 상승시 | 10% 하락시)는 열 내
    # 단일 시나리오라 세로합 유효 — 본문 행에서만 신호를 찾는다.
    if any("상승" in G[i][j] for i in range(hdr, nrow) for j in range(ncol)) and \
       any("하락" in G[i][j] for i in range(hdr, nrow) for j in range(ncol)):
        if excl_reason is None: excl_reason = "SENSITIVITY"
    # 지표 산정 표 — 라벨에 '비율'이 있으면 총계류 라벨(차입금총계 등)이 합계행이
    # 아니라 비율 계산의 입력 항목이다 (참조형 총계, 휴맥스 p144 순차입금비율)
    if any("비율" in LBL[i] for i in range(hdr, nrow)):
        if excl_reason is None: excl_reason = "RATIO_TABLE"
    excl_tab = excl_reason is not None      # 종전 불리언과 동일 — 판정 불변
    tcols = total_col_idx(G, hdr, ncol, numcols)

    # ── A2 가로합 ──
    # 성분열은 numcols(NUM≥2)가 아니라 가로합 전용 완화 기준으로 재구성한다.
    # 가로합은 성분 열이 하나만 빠져도 조용히 틀린 차이가 나오므로(희소 열 탈락 오탐)
    # NUM 1개짜리 열도 포함한다. 단 텍스트 섞인 열(라벨·비고)과 주석열은 여전히 제외.
    # numcols 조건 자체는 완화하지 않는다 — A1 세로합·A3/A5에 파급 금지.
    if tcols:
        # 요약 재무현황 표 — 자산·부채·자본 계열 열이 헤더에 공존하면 자본 열은
        # 자산 − 부채 가감구조라 가로합 부적합 (IS에 A3 미적용과 같은 논리,
        # 휴맥스 p18 종속기업 현황표). 헤더 열 구성 판정 — 데이터 행 라벨 미사용.
        hs = [G[i][j] for i in range(hdr) for j in range(ncol) if G[i][j]]
        a2_off = excl_a2 or (any("자산" in h for h in hs) and any("부채" in h for h in hs)
                             and any("자본" in h for h in hs))
        a2cols = [j for j in range(ncol) if j not in tcols
                  and sum(1 for i in range(hdr, nrow) if K[i][j] == "NUM") >= 1
                  and not any(K[i][j] == "TEXT" for i in range(hdr, nrow))
                  and not is_note_col(G, K, V, hdr, nrow, j)]
        for i in range(hdr, nrow):
            for tj in tcols:
                if K[i][tj] != "NUM": continue
                # 이중 합계열: 각 합계열의 성분은 직전 합계열 이후 ~ 현재 합계열 이전.
                # (특수관계자 채권·채무표처럼 '계' 열이 2개면 서로의 성분을 침범한다)
                lo = max([tc for tc in tcols if tc < tj], default=-1)
                pcols = [j for j in a2cols if lo < j < tj and K[i][j] in ("NUM","BLANK")]
                parts = [V[i][j] for j in pcols]
                if len(parts) < 2: continue
                # % 행 — 금액과 비율의 가로합은 무의미. 주 신호(전 값이 콤마 없는
                # |v|<=100) + 보조 신호(라벨에 률·율·비율·%)를 모두 요구한다.
                # 주 신호 단독은 소액 금액 행을 오발화한다 (LGES 특수관계자 표 실측 9건)
                cells_ = [(G[i][j], V[i][j]) for j in a2cols if lo < j < tj and K[i][j] == "NUM"]
                pct = (bool(cells_)
                       and all(abs(v) <= 100 and "," not in t_
                               for t_, v in cells_ + [(G[i][tj], V[i][tj])])
                       and any(tk in LBL[i] for tk in ("률", "율", "비율", "%")))
                s = sum(parts)
                if   excl_tab: _rsn = excl_reason
                elif excl_a2:  _rsn = "MIXED_CURRENCY"
                elif a2_off:   _rsn = "SUMMARY_FINANCIALS"
                elif pct:      _rsn = "PCT_ROW"
                else:          _rsn = None
                # tcol: 표시 금액이 실제로 놓인 합계 열. bbox 산출에 쓰는 col과 분리한다 —
                # A2 마크 위치는 종전대로 '행의 마지막 비어있지 않은 셀'을 쓰므로(final.py)
                # 여기에 col을 넣으면 마크가 이동해 R-1이 깨진다. 원문 표기 조회 전용.
                res.append(dict(kind="A2", row=i, label=LBL[i][:24],
                                disp=V[i][tj], calc=s, tcol=tj,
                                operands=[dict(row=i, col=j) for j in pcols],
                                reason=_rsn,
                                n=(0 if (excl_tab or a2_off or pct) else len(parts))))

    # ── A1 세로합 (계 행) ──
    trows = [i for i in range(hdr, nrow) if is_total_label(LBL[i])]
    subs  = [i for i in trows if is_sub_label(LBL[i])]
    mains = [i for i in trows if i not in subs]
    # 구간 제목행(라벨만 있고 숫자 없음) = 하위그룹 시작 경계
    secs  = [i for i in range(hdr, nrow)
             if LBL[i] and all(K[i][j] != "NUM" for j in numcols)]

    def sub_body(si):
        lo = max([x+1 for x in subs+mains+secs if x < si] + [hdr])
        return [i for i in range(lo, si) if i not in trows and i not in secs]

    covered = set()
    for si in subs: covered |= set(sub_body(si)); covered.add(si)

    # 구조 표기 하위항목 — (a) 접두 기호  (b) 들여쓰기(선행 공백 / x0 좌표).
    # 하위항목 행은 바로 위 비하위 행(소계 역할)에 귀속시켜 covered에 넣는다.
    # 구조가 명시적이므로 n=1 허용. 들여쓰기 판정은 오탐 위험이 있어 sublog에 경로를 남긴다.
    PRE = ("-", "‐", "–", "—", "ㆍ", "ᆞ", "·")          # ᆞ = ㆍ의 NFKC 정규화형
    base = None
    if x0s:
        xs = sorted(x0s[i] for i in range(hdr, nrow)
                    if i < len(x0s) and x0s[i] is not None and G[i][0])
        if len(xs) >= 2:
            left = [x for x in xs if x <= xs[0] + 1.5]     # 가장 왼쪽 군집 = 기준선
            base = sum(left) / len(left)

    def sub_path(i):
        lab = LBL[i]
        if not lab: return None
        if len(lab) > 1 and lab[0] in PRE: return "접두"
        raw = ""
        try: raw = str(tb[i][LC[i]] or "")
        except Exception: pass
        if raw[:1].isspace() and raw.strip(): return "들여쓰기(공백)"
        if base is not None and x0s and i < len(x0s) and x0s[i] is not None \
           and x0s[i] >= base + 3.0: return "들여쓰기(x0)"
        return None

    # 접두 기호는 구조가 명시적이라 그대로 채택한다. 들여쓰기(공백·x0)는 정렬 목적
    # 오탐이 많아(재고·사채 병렬 항목) 독립 판정 경로가 아니라 경계 '추정기'다:
    # 좌표는 후보만 제안하고, 수치 정합(부모 = 하위 연속행 합)을 통과할 때만 채택한다.
    cur_parent = None; grp = {}
    for i in range(hdr, nrow):
        if i in trows or i in secs: cur_parent = None; continue
        p = sub_path(i)
        if p:
            if cur_parent is not None: grp.setdefault(cur_parent, []).append((i, p))
        else:
            cur_parent = i
    for R, members in grp.items():
        take = [(i, p) for i, p in members if p == "접두"]
        ind = [(i, p) for i, p in members if p != "접두"]
        if ind:
            cand = [i for i, _ in members]           # 부모 = 접두+들여쓰기 전체 합 검증
            rcols = [j for j in numcols if K[R][j] == "NUM"]
            fit = bool(rcols) and all(
                any(K[x][j] == "NUM" for x in cand) and
                abs(sum(V[x][j] for x in cand if K[x][j] in ("NUM","BLANK")) - V[R][j]) < 1e-9
                for j in rcols)
            if fit: take = members
        for i, p in take:
            covered.add(i)
            if sublog is not None:
                sublog.append(dict(ctx=ctx, row=i, path=p,
                                   label=LBL[i][:24], parent=LBL[R][:24]))

    # 역산 소계 — '소계' 라벨 없이 계정과목명이 소계 역할을 하는 행 (라벨 방식과 병행).
    # 행 R의 값이 바로 아래 연속 n개 행(n>=2)의 합과 R의 모든 금액열에서 일치하면
    # 그 n개 행을 covered에 넣어 상위 '계' 합산에서 제외한다 (R 자신은 합산에 남긴다).
    # 우연 일치 방지: n>=2, 검사 열마다 |R값|>=1000. 후보가 겹치면 커버 행 많은 쪽 우선.
    cand = []
    for R in range(hdr, nrow):
        if R in trows or R in secs: continue
        rcols = [j for j in numcols if K[R][j] == "NUM"]
        if not rcols or any(abs(V[R][j]) < 1000 for j in rcols): continue
        comps = []
        for i in range(R+1, nrow):
            if i in trows or i in secs: break
            comps.append(i)
            if len(comps) < 2: continue
            if all(any(K[x][j] == "NUM" for x in comps) and
                   abs(sum(V[x][j] for x in comps if K[x][j] in ("NUM","BLANK")) - V[R][j]) < 1e-9
                   for j in rcols):
                cand.append((R, tuple(comps)))
    used = set(covered)
    for R, comps in sorted(cand, key=lambda c: (-len(c[1]), c[0])):
        cs = set(comps)
        if R in used or cs & used: continue
        covered |= cs; used |= cs | {R}

    # 역방향 역산 — 순액 3행 그룹 (gross − 차감 = 순액, 예: 매출채권/차감: 손실충당금/
    # 매출채권(순액)). 행 R의 값이 바로 위 연속 n개 행(n>=2)의 합과 R의 모든 금액열에서
    # 일치하면 위 행들을 covered에 넣고 R(순액)을 합산에 남긴다. '차감:' 라벨은 신호일
    # 뿐 단독 트리거가 아니다 — 수치 정합이 확정한다 (들여쓰기 격하와 같은 필터 패턴).
    cand_up = []
    for R in range(hdr, nrow):
        if R in trows or R in secs: continue
        rcols = [j for j in numcols if K[R][j] == "NUM"]
        if not rcols or any(abs(V[R][j]) < 1000 for j in rcols): continue
        comps = []
        for i in range(R-1, hdr-1, -1):
            if i in trows or i in secs: break
            comps.append(i)
            if len(comps) < 2: continue
            if all(any(K[x][j] == "NUM" for x in comps) and
                   abs(sum(V[x][j] for x in comps if K[x][j] in ("NUM","BLANK")) - V[R][j]) < 1e-9
                   for j in rcols):
                cand_up.append((R, tuple(comps)))
    for R, comps in sorted(cand_up, key=lambda c: (-len(c[1]), c[0])):
        cs = set(comps)
        if R in used or cs & used: continue
        covered |= cs; used |= cs | {R}

    # 콜론 구간 경계 — ':'로 끝나는 라벨 행은 '계' 자유행 합산의 시작 경계
    # (예: '단기차입금:' 구간의 행이 다음 구간 계에 합산되는 것을 차단)
    colon = [i for i in range(hdr, nrow) if LBL[i].endswith(":")]

    # 구간 마감행 존재 신호(순수 구조, 표 단위): 콜론 구간(콜론~다음 콜론 직전,
    # 마지막은 표 끝까지) 중 마감행(계·소계 trow)이 없는 구간이 하나라도 있으면
    # 콜론은 단순 구분이므로 이 표에서 경계로 쓰지 않고 free로 흘려보낸다
    # (LGES 특수관계자 표: 나열 구간 + 말미 합 계 1개 → 표 전체가 합산 단위).
    # 전 구간이 마감되면 진짜 구간 경계다(삼성 p51 — 구간별 계).
    colon_bound = bool(colon)
    for _ci, _c in enumerate(colon):
        _end = colon[_ci+1] if _ci+1 < len(colon) else nrow
        if not any(t in trows for t in range(_c+1, _end)):
            colon_bound = False; break
    secs_eff = secs if colon_bound else [i for i in secs if i not in colon]

    for ti in trows:
        if ti in subs:
            body = sub_body(ti)
        else:
            prevm = max([t for t in mains if t < ti], default=hdr-1)
            # 콜론 구간이 소계로 마감되지 않고 '계'와 바로 만나면(열린 구간) 그 콜론을
            # 자유행 창의 시작 경계로 쓴다. 소계로 마감된 콜론 구간은 covered가 이미
            # 격리하므로 경계로 쓰지 않는다 — 경계로 쓰면 구간 앞의 정당한 합산 행이
            # 잘려나간다 (예: 연체되지 않은 채권 + 연체채권 소계 = 계).
            open_cols = ([c for c in colon if prevm < c < ti
                          and not any(c < s < ti for s in subs)] if colon_bound else [])
            prev = max([prevm] + open_cols)
            inner = [i for i in subs if prevm < i < ti]
            free  = [i for i in range(prev+1, ti)
                     if i not in trows and i not in secs_eff and i not in covered]
            body = sorted(inner + free)
        # 이중 분해 표 — 계 아래 소계 중 전 금액열에서 서로 같은 값의 쌍이 있으면
        # 같은 총액을 두 관점(유형별·시기별)으로 분해한 것: 둘 다 합산하면 이중계상
        # → 미검증. (유형별 소계 = 시기별 소계 자체의 검증은 별도 과제)
        dual = False
        if ti not in subs and len(inner) >= 2:
            dual = any(
                all(K[a][j] != "NUM" or K[b][j] != "NUM" or abs(V[a][j]-V[b][j]) < 1e-9
                    for j in numcols)
                and any(K[a][j] == "NUM" and K[b][j] == "NUM" for j in numcols)
                for x_, a in enumerate(inner) for b in inner[x_+1:])
        for j in numcols:
            if K[ti][j] != "NUM": continue
            prows = [i for i in body if K[i][j] in ("NUM","BLANK")]
            parts = [V[i][j] for i in prows]
            if len(parts) < 2: continue
            # 두 단계 조판 흡수 — 성분 안에 중간 소계가 섞여 있으면 평면 합산이
            # 그 소계를 이중계상한다(충당부채 롤포워드 등, absorb_subtotal 참고).
            _abs = absorb_subtotal(parts)
            # 흡수한 소계의 행 이름 — 지면은 깨끗한 체크로 나가지만 이 판정을 나중에
            # 의심할 때 근거가 필요하다(2026-08-28 승인). 성분 목록(operands)에서는
            # 빼서 '성분 합 = calc' 관계를 유지한다.
            absorbed = [LBL[prows[x]][:24] for x in sorted(_abs)]
            if _abs:
                prows = [r for x, r in enumerate(prows) if x not in _abs]
                parts = [v for x, v in enumerate(parts) if x not in _abs]
                if len(parts) < 2: continue
            skip = excl_tab or dual
            res.append(dict(kind="A1", row=ti, col=j, label=LBL[ti][:24] or "계",
                            disp=V[ti][j], calc=sum(parts),
                            operands=[dict(row=i, col=j) for i in prows],
                            absorbed=absorbed,
                            reason=(excl_reason if excl_tab else ("DUAL_BREAKDOWN" if dual else None)),
                            n=(0 if skip else len(parts))))

    # ── A3 계층합 (합계가 별도 열인 본표형) ──
    if not trows and len(numcols) >= 2:
        # 같은 행에서 동시 출현하지 않는 열쌍 = (세부, 합계)
        for a in numcols:
            for b in numcols:
                if b != a + 1: continue
                co = sum(1 for i in range(hdr, nrow) if K[i][a]=="NUM" and K[i][b]=="NUM")
                if co: continue
                na = sum(1 for i in range(hdr,nrow) if K[i][a]=="NUM")
                nb = sum(1 for i in range(hdr,nrow) if K[i][b]=="NUM")
                if na < 3 or nb < 2 or nb >= na: continue
                def emit(p, ac):
                    mixed = any(x > 0 for x in ac) and any(x < 0 for x in ac)
                    res.append(dict(kind="A3", row=p[0], label=p[1], disp=p[2],
                                    calc=sum(ac), n=(0 if (len(ac) < 2 or mixed) else len(ac)),
                                    note=("가감구조 추정" if mixed else "")))
                pend=None; acc=[]
                for i in range(hdr, nrow):
                    if K[i][b] == "NUM":
                        if pend is not None: emit(pend, acc)
                        pend=(i, G[i][0][:24], V[i][b]); acc=[]
                    elif K[i][a] == "NUM":
                        acc.append(V[i][a])
                if pend is not None: emit(pend, acc)
    return res

# 미검증 사유 코드 → 회계사가 읽을 문장. 코드와 같은 파일에 둔다(둘이 떨어지면
# 코드를 늘릴 때 문장을 빠뜨린다). 여기 없는 코드가 나오면 호출부가 UNRESOLVED_REASON으로
# 표면화한다 — 빈 문자열로 조용히 흘리지 않는다(2026-08-25 승인 조건).
SKIP_REASON_TEXT = {
    "AUDIT_HOURS":        "감사 투입시간·인원 표라 금액 합계 검증 대상이 아닙니다",
    "RESTATEMENT":        "전기 재작성 내역표라 표시된 항목이 완전한 가산 집합이 아닙니다",
    "MIXED_CURRENCY":     "통화가 섞인 표라 합계를 계산할 수 없습니다",
    "SENSITIVITY":        "민감도 분석 표(상승·하락 대칭 행)라 세로 합계가 성립하지 않습니다",
    "RATIO_TABLE":        "비율 산정 표라 총계 라벨이 합계행이 아닙니다",
    "SUMMARY_FINANCIALS": "자산·부채·자본 열이 함께 있는 요약 표라 가로 합계가 성립하지 않습니다",
    "PCT_ROW":            "비율(%) 행이라 가로 합계가 무의미합니다",
    "DUAL_BREAKDOWN":     "같은 총액을 두 관점으로 분해한 표라 소계를 합산하면 이중계상됩니다",
    "A3_SPLIT_INCOMPLETE":"페이지 분할로 하위 항목이 잘려 합계를 검증할 수 없습니다",
    "A3_TOO_FEW_PARTS":   "하위 항목이 2개 미만이라 합계를 검증할 수 없습니다",
    "SIGN_CONVENTION":    "소계와 성분의 부호 규약이 달라 검증하지 못했습니다",
    "REF_NOT_FOUND":      "주석에서 동일 금액을 찾지 못했습니다",
    # A5 커버리지 점검 — 고정 산식이 그 표의 구조를 못 덮을 때. 두 사유 모두
    # 뒤에 구체적인 행·항목 이름이 붙는다(final.py의 reason_detail). 이름 없이
    # 물음표만 내면 회계사가 무엇을 확인해야 할지 알 수 없다.
    "A5_TERM_NOT_FOUND":  "산식 항목을 이 표에서 찾지 못했습니다",
    "A5_UNCOVERED_ROW":   "산식에 포함되지 않은 행이 있습니다",
}


def verdict(r, tol=0.0, round_steps=0):
    """A7 단수차이 분류 포함.

    round_steps: '표 단위 스텝' 허용 개수 — 표시 숫자 공간에서 1스텝 = 1
    (백만원 표 = 1백만원, 천원 표 = 1천원, 원 표 = 1원). 전역 절대값 tol과 달리
    단위가 달라도 같은 강도로 작동한다. 기본 0 = 현행 동작 보존 (확정은 회계사)."""
    if r["n"] == 0: return "SKIP"
    d = r["calc"] - r["disp"]
    if abs(d) < 1e-9: return "OK"
    # 부호 규약 상이 — 소계와 성분합의 부호가 반대인데 절대값이 일치 (예: 휴맥스 CF
    # 유출액 소계는 음수 표기, 성분은 양수 표기). 절대값 비교로 OK 처리하면 진짜
    # 부호 오류를 영원히 못 잡으므로 별도 판정으로 분리한다: 지면은 ?(미검증),
    # 예외 색인에 '부호규약' 태그. 절대값이 다르면 여기 안 걸리고 DIFF로 남는다.
    if r["disp"] * r["calc"] < 0 and abs(abs(r["calc"]) - abs(r["disp"])) < 1e-9:
        return "SIGN"
    if abs(d) <= tol: return "ROUND"
    if round_steps and abs(d) <= round_steps: return "ROUND"
    return "DIFF"
