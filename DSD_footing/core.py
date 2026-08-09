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
EXCL_LABEL = ("법인세효과", "세후")   # 세효과 가감 구조 → 단순 합산 부적합 (SKIP)

def _excl_table(G, hdr, ncol, nrow):
    """헤더나 첫 열 라벨에 시간·인원이 있는 표 — 검증은 등재하되 미검증(SKIP)"""
    return any(kw in G[i][j] for kw in EXCL_TABLE for i in range(hdr) for j in range(ncol)) \
        or any(kw in G[i][0] for kw in EXCL_TABLE for i in range(hdr, nrow))

# ── 검증 ───────────────────────────────────────────────────
def check_table(tb, tol=0.0, x0s=None, sublog=None, ctx=None):
    """A1 세로합 · A2 가로합 · A3 계층합 수행 → 결과 리스트

    x0s    : 행별 첫 열 라벨의 x0 좌표 (들여쓰기 하위항목 판정용, 없으면 None)
    sublog : 하위항목 판정 로그 수집 리스트 (경로별 검증용)
    ctx    : (page, table) — 로그 표기용
    """
    G, K, V, hdr, ncol, nrow, numcols = grid_info(tb)
    res = []
    if not numcols: return res
    excl_tab = _excl_table(G, hdr, ncol, nrow)
    tcols = total_col_idx(G, hdr, ncol, numcols)

    # ── A2 가로합 ──
    # 성분열은 numcols(NUM≥2)가 아니라 가로합 전용 완화 기준으로 재구성한다.
    # 가로합은 성분 열이 하나만 빠져도 조용히 틀린 차이가 나오므로(희소 열 탈락 오탐)
    # NUM 1개짜리 열도 포함한다. 단 텍스트 섞인 열(라벨·비고)과 주석열은 여전히 제외.
    # numcols 조건 자체는 완화하지 않는다 — A1 세로합·A3/A5에 파급 금지.
    if tcols:
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
                parts = [V[i][j] for j in a2cols if lo < j < tj and K[i][j] in ("NUM","BLANK")]
                if len(parts) < 2: continue
                s = sum(parts)
                res.append(dict(kind="A2", row=i, label=G[i][0][:24],
                                disp=V[i][tj], calc=s, n=(0 if excl_tab else len(parts))))

    # ── A1 세로합 (계 행) ──
    trows = [i for i in range(hdr, nrow) if is_total_label(G[i][0])]
    subs  = [i for i in trows if is_sub_label(G[i][0])]
    mains = [i for i in trows if i not in subs]
    # 구간 제목행(라벨만 있고 숫자 없음) = 하위그룹 시작 경계
    secs  = [i for i in range(hdr, nrow)
             if G[i][0] and all(K[i][j] != "NUM" for j in numcols)]

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
        lab = G[i][0]
        if not lab: return None
        if len(lab) > 1 and lab[0] in PRE: return "접두"
        raw = ""
        try: raw = str(tb[i][0] or "")
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
                                   label=G[i][0][:24], parent=G[R][0][:24]))

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

    # 콜론 구간 경계 — ':'로 끝나는 라벨 행은 '계' 자유행 합산의 시작 경계
    # (예: '단기차입금:' 구간의 행이 다음 구간 계에 합산되는 것을 차단)
    colon = [i for i in range(hdr, nrow) if G[i][0].endswith(":")]

    for ti in trows:
        if ti in subs:
            body = sub_body(ti)
        else:
            prevm = max([t for t in mains if t < ti], default=hdr-1)
            # 콜론 구간이 소계로 마감되지 않고 '계'와 바로 만나면(열린 구간) 그 콜론을
            # 자유행 창의 시작 경계로 쓴다. 소계로 마감된 콜론 구간은 covered가 이미
            # 격리하므로 경계로 쓰지 않는다 — 경계로 쓰면 구간 앞의 정당한 합산 행이
            # 잘려나간다 (예: 연체되지 않은 채권 + 연체채권 소계 = 계).
            open_cols = [c for c in colon if prevm < c < ti
                         and not any(c < s < ti for s in subs)]
            prev = max([prevm] + open_cols)
            inner = [i for i in subs if prevm < i < ti]
            free  = [i for i in range(prev+1, ti)
                     if i not in trows and i not in secs and i not in covered]
            body = sorted(inner + free)
        for j in numcols:
            if K[ti][j] != "NUM": continue
            parts = [V[i][j] for i in body if K[i][j] in ("NUM","BLANK")]
            if len(parts) < 2: continue
            # 적용 부적합: 시간·인원 표, 또는 합산 대상에 법인세효과·세후 라벨 포함
            skip = excl_tab or any(kw in G[i][0] for i in body for kw in EXCL_LABEL)
            res.append(dict(kind="A1", row=ti, col=j, label=G[ti][0][:24] or "계",
                            disp=V[ti][j], calc=sum(parts), n=(0 if skip else len(parts))))

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

def verdict(r, tol=0.0):
    """A7 단수차이 분류 포함"""
    if r["n"] == 0: return "SKIP"
    d = r["calc"] - r["disp"]
    if abs(d) < 1e-9: return "OK"
    if abs(d) <= tol: return "ROUND"
    return "DIFF"
