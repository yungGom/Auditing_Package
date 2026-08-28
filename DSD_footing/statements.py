# -*- coding: utf-8 -*-
"""본표 전용 검증 — A5 가감구조 · B 본표간 연계 · C7 주석번호 (오프라인)"""
import re
from core import norm, parse, grid_info

# ── 라벨 계층 (한국 재무제표 관행) ─────────────────────────
ROMAN = re.compile(r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVX]{1,4})\s*[\.\)]")
ARABIC= re.compile(r"^\s*\d+\s*[\.\)]")
HANGUL= re.compile(r"^\s*[가나다라마바사아자차카타파하]\s*[\.\)]")

def label_depth(t):
    t = norm(t)
    if ROMAN.match(t):  return 3
    if ARABIC.match(t): return 2
    if HANGUL.match(t): return 1
    return 0

def key(t):
    """라벨 정규화 — 공백·괄호주석 제거"""
    t = norm(t)
    t = re.sub(r"^\s*(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]|[IVX]{1,4}|\d+|[가-하])\s*[\.\)]\s*", "", t)
    t = re.sub(r"\(.*?\)", "", t)
    return t.replace(" ", "")

# ── 기간 열 그룹핑: numcols를 (세부, 합계) 쌍으로 ──────────
TOTAL_KEY = re.compile(r"^(자산총계|부채총계|자본총계|부채와자본총계|합계|계|총계)$")

# 표제 접두어. 감사보고서는 '연결/별도'뿐이지만 중간재무보고(1034호)는
# '요약반기재무상태표'처럼 요약·반기·분기·중간이 붙는다. 순서·개수를 고정하지
# 않기 위해 반복 허용 그룹으로 둔다. 접미(계산서/표) 쪽은 건드리지 않는다.
_PFX = r"(?:요약|중간|반기|분기|연결|별도)*"
STMT = [("BS", re.compile(_PFX + r"재무상태표")),
        ("CI", re.compile(_PFX + r"포괄손익계산서")),
        ("IS", re.compile(_PFX + r"손익계산서")),
        ("CF", re.compile(_PFX + r"현금흐름표")),
        ("SCE",re.compile(_PFX + r"자본변동표"))]

def stmt_type(page_text):
    """본표 페이지만 인식: 제목이 첫 3줄 안(공백 제거 후 완전일치) + '과목/구분' 헤더"""
    txt = page_text or ""
    lines = [l.strip() for l in txt.split("\n") if l.strip()][:3]
    if not lines: return None
    flat = txt.replace(" ", "")
    if "과목" not in flat and "구분" not in flat: return None
    for l in lines:
        c = l.replace(" ", "")
        if re.match(r"^[\d가-하][\.\)]", c): continue    # '나. 연결손익계산서' 등 주석 소제목 제외
        for name, rx in STMT:
            if rx.fullmatch(c): return name
    return None

# 재무제표 유형별 적용 규칙 (고정 템플릿)
APPLY = {"BS": ("A3","A5"), "CF": ("A3","A5"), "IS": ("A5",),
         "CI": ("A5",), "SCE": (), None: ()}

def period_cols(numcols, K=None, hdr=0, nrow=0):
    """열 구조 판정: 동시 출현하면 별개 기간, 배타적이면 (세부,합계) 계층쌍.
    삼성식(합계 별도열)과 일반식(단일열)을 모두 지원한다."""
    if K is None or len(numcols) < 2:
        return [(c,) for c in numcols]
    def co(a, b):
        both = sum(1 for i in range(hdr, nrow) if K[i][a]=="NUM" and K[i][b]=="NUM")
        any_ = sum(1 for i in range(hdr, nrow) if K[i][a]=="NUM" or  K[i][b]=="NUM")
        return both / any_ if any_ else 0.0
    out = []; i = 0
    while i < len(numcols):
        a = numcols[i]
        if i+1 < len(numcols) and co(a, numcols[i+1]) < 0.15:
            out.append((a, numcols[i+1])); i += 2      # 배타적 = 계층쌍
        else:
            out.append((a,)); i += 1                    # 동시출현 = 독립 기간
    return out

def read_rows(tb):
    """→ [(depth, key, raw, {periodIdx: value})]  본표형(세부/합계 2열) 전용"""
    G,K,V,hdr,ncol,nrow,numcols = grid_info(tb)
    if len(numcols) < 2: return [], 0
    pcs = period_cols(numcols, K, hdr, nrow)
    out = []
    for i in range(hdr, nrow):
        lab = G[i][0]
        if not lab: continue
        vals = {}; coldep = 0; colof = {}
        for pi, cols in enumerate(pcs):
            for ci, j in enumerate(cols):
                if K[i][j] == "NUM":
                    vals[pi] = V[i][j]; colof[pi] = j
                    coldep = max(coldep, ci + 1)   # 합계열이면 2
        if not vals: continue
        d = (coldep - 1) * 10 + label_depth(lab)   # 열 위치 우선, 라벨계층 보조
        out.append([d, key(lab), lab, vals, False, bool(TOTAL_KEY.match(key(lab))), i, colof])
    # 부모 판정: 다음 항목의 depth가 더 얕으면 부모, 아니면 말단
    for i in range(len(out)):
        nxt = out[i+1][0] if i+1 < len(out) else -1
        out[i][4] = nxt < out[i][0]
    return out, len(pcs)

# ── 기간 축 판정: (당/전) × (3개월/누적) ───────────────────
# 연차보고서는 기간 축이 (당,전) 1차원이라 위치(0=당, 1=전)로 충분했지만,
# 중간재무보고는 손익계산서·포괄손익계산서가 (당/전) × (3개월/누적) 2차원이다.
# 위치 가정을 유지하면 '전기' 자리에 당반기 누적이 들어와 조용히 틀린다.
SIDE_CUR = re.compile(r"\(\s*당\s*\)|당\s*(?:기|반기|분기|회계연도)")
SIDE_PRV = re.compile(r"\(\s*전\s*\)|전\s*(?:기|반기|분기|회계연도)")
SPAN_3M  = re.compile(r"3\s*개\s*월|삼\s*개\s*월")
SPAN_CUM = re.compile(r"누\s*적")

def _fill_merged(row, start, ncol):
    """헤더행 병합셀 전파. '제6(당)기 반기'가 첫 열에만 있고 '누적' 열은 비어 있으므로
    왼쪽 값을 오른쪽으로 흘려야 각 기간의 당/전을 읽을 수 있다.
    라벨열이 새어들지 않도록 첫 숫자열부터만 채운다."""
    out = list(row); last = ""
    for j in range(start, ncol):
        v = out[j] if j < len(out) else ""
        if v: last = v
        else:  out[j] = last
    return out

def period_axis(tb):
    """→ ({(side, span): periodIdx}, nper)
    side∈{'당','전'} · span∈{'3M','누적',None}. 판정 불가한 기간은 넣지 않는다(추측 금지)."""
    G, K, V, hdr, ncol, nrow, numcols = grid_info(tb)
    if not numcols: return {}, 0
    pcs = period_cols(numcols, K, hdr, nrow)
    rows = [_fill_merged(G[i], min(numcols), ncol) for i in range(hdr)]
    axis = {}
    for p, cols in enumerate(pcs):
        txt = " ".join(rows[i][j] for i in range(hdr) for j in cols)
        cur, prv = bool(SIDE_CUR.search(txt)), bool(SIDE_PRV.search(txt))
        if cur == prv: continue                      # 표시 없음 또는 양쪽 다 → 판정 불가
        side = "당" if cur else "전"
        span = "3M" if SPAN_3M.search(txt) else ("누적" if SPAN_CUM.search(txt) else None)
        axis.setdefault((side, span), p)
    return axis, len(pcs)

def pick_period(axis, nper, side):
    """본표 간 대사에 쓸 기간 인덱스.
    3개월 열은 재무상태표(시점)·현금흐름표(누적)와 대사 대상이 아니므로 절대 고르지 않는다."""
    for span in ("누적", None):
        if (side, span) in axis: return axis[(side, span)]
    if not axis and nper == 2:                       # 헤더 판독 실패 + 연차 2기간 관행
        return 0 if side == "당" else 1
    return None                                      # 미매칭≠0 — 0/1로 추측하지 않는다

# ── A3v2: 라벨계층 기반 누적 풋팅 ─────────────────────────
def foot_hier(tb):
    rows, nper = read_rows(tb)
    res = []

    def pop_to(stack, p, depth, force_skip=False):
        """depth 이하가 될 때까지 스택을 닫고 결과를 낸다. depth=None이면 전량 정산.

        acc 원소는 (값, 행, 열) 3튜플이다 — 합산에 들어간 자식 행을 operands로 넘기기
        위함(값만으로는 지면에서 어느 행이었는지 되짚을 수 없다). 합계는 첫 원소만 쓴다."""
        while stack and (depth is None or stack[-1][0] <= depth):
            dd, kk, rr, dv, acc, rri, rcj = stack.pop()
            n = 0 if force_skip else (len(acc) if len(acc) >= 2 else 0)
            res.append(dict(kind="A3", period=p, label=rr[:26], row=rri, col=rcj,
                            disp=dv, calc=sum(a[0] for a in acc),
                            operands=[dict(row=a[1], col=a[2]) for a in acc],
                            reason=("A3_SPLIT_INCOMPLETE" if force_skip
                                    else (None if len(acc) >= 2 else "A3_TOO_FEW_PARTS")),
                            n=n))
            if stack: stack[-1][4].append((dv, rri, rcj))

    for p in range(nper):
        stack = []
        last_ri = None
        for d, k, raw, vals, is_parent, is_tot, ri, colof in rows:
            # 총계행(자산총계·부채총계·자본총계…)은 구간의 끝이다. 값은 A1이 검증하므로
            # 여기서 집계하지 않되, 반드시 스택을 닫아야 한다. 닫지 않으면 다음 구간의
            # 항목이 직전 구간의 미정산 소계에 흡수된다(삼성 조판에서는 자본 항목이
            # 합계열에 있어 depth가 같아 우연히 pop됐고, 세부열에 찍는 조판에서 노출).
            if is_tot:
                pop_to(stack, p, None)
                continue
            if p not in vals: continue
            last_ri = ri
            pop_to(stack, p, d)
            if not is_parent:
                if stack: stack[-1][4].append((vals[p], ri, colof.get(p)))
            else:
                stack.append((d, k, raw, vals[p], [], ri, colof.get(p)))
        # 분할 미완결 — 표의 마지막 행이 부모로 판정됐고(다음 행이 없어 부모가 됨)
        # 자식을 하나도 받지 못했다면 페이지 분할로 잘린 표다. 그 행과 열린 조상
        # 전부를 미검증(?)으로 낸다 — 자식 일부만 받은 조상을 합산하면 오탐이 된다
        # (휴맥스 p8 유동부채: 충당부채가 페이지 마지막 행, p9의 구성 항목 누락).
        # 삼성 p10 'I.자본금'은 종전에도 acc<2로 n=0였고 사유만 '분할 미완결'로 정확해진다.
        incomplete = bool(stack) and not stack[-1][4] and stack[-1][5] == last_ri
        pop_to(stack, p, None, force_skip=incomplete)
    return res

# ── A5: 가감 관계식 (고정 템플릿) ─────────────────────────
A5_RULES = [
 ("매출총이익",              [("+","매출액"),("-","매출원가")]),
 ("영업이익",                [("+","매출총이익"),("-","판매비와관리비")]),
 ("법인세비용차감전순이익",   [("+","영업이익"),("+","기타수익"),("-","기타비용"),
                              ("+","금융수익"),("-","금융비용")]),
 ("당기순이익",              [("+","법인세비용차감전순이익"),("-","법인세비용")]),
 ("총포괄손익",              [("+","당기순이익"),("+","기타포괄손익")]),
 ("현금및현금성자산의증가",   [("+","영업활동현금흐름"),("+","투자활동현금흐름"),
                              ("+","재무활동현금흐름"),("+","외화환산으로인한현금의")]),
 ("기말의현금및현금성자산",   [("+","기초의현금및현금성자산"),("+","현금및현금성자산의증가")]),
 ("부채와자본총계",          [("+","부채총계"),("+","자본총계")]),
 ("자산총계",                [("+","유동자산"),("+","비유동자산")]),
 ("부채총계",                [("+","유동부채"),("+","비유동부채")]),
]

def _absorbed(span, book, opvals):
    """구간 행 중 '연속 n(n>=2)개의 합 = 어느 성분의 값'인 묶음을 찾아 돌려준다.

    그 묶음은 누락된 항목이 아니라 그 성분의 하위 항목이다 — 자산총계 = 유동자산 +
    비유동자산 사이의 현금및현금성자산·매출채권은 빠진 게 아니라 유동자산에 이미
    들어 있다. A3 소관이지 A5 소관이 아니므로 커버리지 미포함으로 세지 않는다.

    core.check_table의 역산 검증(부모 = 아래 연속 n개 행의 합)과 같은 성질을 쓴다.
    새 발상이 아니라 4축에서 이미 검증된 기제의 재사용이다 — 규칙 목록을 손으로
    고르는 과적합을 피하기 위함(2026-08-28 승인)."""
    out = set(); n = len(span)
    for i in range(n):
        s = 0.0
        for j in range(i, n):
            s += book[span[j]]
            if j - i + 1 < 2: continue          # 1개짜리 일치는 모호하다(core와 같은 n>=2)
            if any(abs(s - v) < 0.5 and abs(v) > 0 for v in opvals):
                out.update(span[i:j+1])
    return out

def foot_a5(tb):
    rows, nper = read_rows(tb)
    res = []
    for p in range(nper):
        book = {}; rowof = {}; colof2 = {}; order = []; dep = {}
        for d,k,raw,vals,_ip,_it,ri,cof in rows:
            if p in vals and k not in book:
                book[k] = vals[p]; rowof[k] = ri; colof2[k] = cof.get(p)
                order.append(k); dep[k] = d
        for tgt, terms in A5_RULES:
            if tgt not in book: continue
            if not all(any(t.startswith(nm) or nm.startswith(t) for t in book) for _,nm in terms):
                pass
            s = 0.0; got = 0; ops = []; used = []; miss = []
            for sg, nm in terms:
                key_ = next((kk for kk in book if kk == nm), None)
                if key_ is None:
                    key_ = next((kk for kk in book if kk.startswith(nm)), None)
                if key_ is None: miss.append(nm); continue
                s += book[key_] if sg == "+" else -book[key_]
                got += 1; used.append(key_)
                ops.append(dict(row=rowof.get(key_), col=colof2.get(key_), sign=sg))
            def _skip(reason, detail):
                res.append(dict(kind="A5", period=p, label=tgt, row=rowof.get(tgt),
                                col=colof2.get(tgt), disp=book[tgt], calc=s, operands=ops,
                                reason=reason, reason_detail=detail, n=0))
            # ── 성분 누락 ───────────────────────────────────────────────
            # 종전에는 `if got < len(terms): continue`로 조용히 탈락시켰다. 그래서
            # 조선내화 연차(금융원가≠금융비용)·LGES(기타영업외수익≠기타수익)에서
            # 세전이익 풋팅이 한 번도 검증되지 않았는데 지면은 깨끗해 보였다 —
            # "미매칭 ≠ 0, 침묵 탈락 금지" 원칙이 이 한 줄에서 새고 있었다.
            # 단, 성분을 하나도 못 찾았으면 그 표에 애초에 해당 없는 규칙이다
            # (포괄손익계산서 지면의 당기순이익 규칙 등). 그건 종전처럼 안 낸다.
            if miss:
                if got: _skip("A5_TERM_NOT_FOUND", ", ".join(miss))
                continue
            # ── 커버리지 점검 ───────────────────────────────────────────
            # 성분을 다 찾았어도, 성분과 좌변 사이에 산식이 안 쓴 행이 남아 있으면
            # 산식이 이 표의 구조를 못 덮는 것이다. 수치가 우연히 맞아도 OK로 내지
            # 않는다 — 조선내화 반기연결 세전이익은 지분법이익이 산식에 없어 DIFF가
            # 났고, 그것이 진짜 차이가 아니라 산식 결함이었다.
            pos = {k: i for i, k in enumerate(order)}
            lo = min(pos[k] for k in used) if used else None
            hi = pos.get(tgt)
            if lo is not None and hi is not None and hi > lo:
                span = [k for k in order[lo+1:hi] if k not in set(used)]
                base = min(dep[k] for k in used + [tgt])
                span = [k for k in span if dep[k] >= base]      # 하위 항목 제외(계층)
                span = [k for k in span if k not in _absorbed(span, book, [book[k] for k in used])]
                if span:
                    _skip("A5_UNCOVERED_ROW", ", ".join(span)); continue
            res.append(dict(kind="A5", period=p, label=tgt, row=rowof.get(tgt), col=colof2.get(tgt),
                            disp=book[tgt], calc=s, operands=ops, reason=None, n=got))
    return res
