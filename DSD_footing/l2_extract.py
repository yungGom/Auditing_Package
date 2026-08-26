# -*- coding: utf-8 -*-
"""l2_extract — PDF → 표간 대사용 원시 튜플 추출 (raw_label 단계).

canonical_label 변환(사전 매칭)은 하지 않는다 — 그건 l2_labels.py의 몫이다.
여기는 순수 파싱: 표에서 (raw_label, column_key, period_key, doc_key, value,
mult, page, table_id, bbox) 튜플을 뽑아내는 것까지만 한다.

기존 코드 재사용: core.grid_info(격자) · statements.stmt_type/key(본표 판정·라벨
정규화) · refmap.table_units(표 귀속 단위) · notes.NOTE_HEAD/AMT(주석 헤더 탐지) ·
tieout.SCE_END/SCE_BEG(자본변동표 시점 라벨). 완전 오프라인.

주석 구간은 refmap.note_ranges(페이지 단위)를 쓰지 않는다 — 두 주석이 같은 페이지에서
시작하면(조선내화 실측: 6·7 둘 다 p20) 앞 주석의 페이지 범위가 (20, 19)처럼 역전되어
그 페이지의 표가 통째로 다음 주석에 잘못 귀속된다. 대신 각 주석 헤더의 세로 좌표(top)를
직접 찾아 표 bbox와 (page, top) 순서로 비교한다 — 같은 페이지 안에서도 어느 주석
헤더가 그 표보다 위에 있는지로 정확히 가른다.
"""
import re
import pdfplumber
from core import grid_info, norm, is_total_label
from statements import stmt_type, key as skey
from refmap import table_units
from notes import NOTE_HEAD, AMT
from tieout import SCE_END, SCE_BEG

# ── period_key 신호 어휘 (statements.py와 동일 정규식 재사용) ──────────────
SIDE_CUR = re.compile(r"\(\s*당\s*\)|당\s*(?:기|반기|분기|회계연도)")
SIDE_PRV = re.compile(r"\(\s*전\s*\)|전\s*(?:기|반기|분기|회계연도)")
SPAN_3M  = re.compile(r"3\s*개\s*월|삼\s*개\s*월")
SPAN_CUM = re.compile(r"누\s*적")
POINT_END = re.compile(r"(반기|분기)?\s*기?\s*말")
POINT_BEG = re.compile(r"(반기|분기)?\s*기?\s*초")

PERIOD_KEYS = ("CY-3M", "CY-CUM", "PY-3M", "PY-CUM", "CY-END", "PY-END")


def _fill_merged(row, start, ncol):
    """헤더행 병합셀 전파 (statements._fill_merged과 동일 로직, 중복 임포트 대신 재구현
    — statements.py 쪽 함수가 private(_로 시작)이라 직접 import하지 않는다)."""
    out = list(row); last = ""
    for j in range(start, ncol):
        v = out[j] if j < len(out) else ""
        if v: last = v
        else: out[j] = last
    return out


def _col_period(text):
    """열 헤더 합친 텍스트 → period_key 또는 None(판정 불가/배제).

    설계안 2-2절 판정 순서 그대로:
    1. 당/전 감지, 둘 다면 또는 둘 다 아니면 판정 불가
    2. 시점(말/초) 마커 우선 — 당기초는 회계 항등(당기초=전기말)으로 PY-END 정규화,
       전기초는 슬롯이 없어(PPY-END 없음) 의도적으로 배제(None)
    3. 시점 없으면 흐름(구간) 마커 — 3개월/누적
    4. 마커 전혀 없이 당기/전기만 있으면(연차보고서 관행) 누적으로 기본 처리
    """
    cur, prv = bool(SIDE_CUR.search(text)), bool(SIDE_PRV.search(text))
    if cur == prv:
        return None
    side = "CY" if cur else "PY"
    if POINT_END.search(text):
        return f"{side}-END"
    if POINT_BEG.search(text):
        return "PY-END" if side == "CY" else None  # 전기초 배제 — 안 되는 것을 안 한다
    if SPAN_3M.search(text):
        return f"{side}-3M"
    if SPAN_CUM.search(text):
        return f"{side}-CUM"
    return f"{side}-CUM"


def _row_period_sce(label, interim):
    """자본변동표 행 라벨(당기초/당기말 등) → period_key. tieout.SCE_END/SCE_BEG 재사용,
    동일한 당기초→PY-END 정규화·전기초 배제 규칙 적용(열 판정과 규칙을 통일).

    interim(중간보고서)이면 '전기말' 행은 PY-END가 아니다 — 반기·분기 보고서의
    SCE는 '전기' 구간이 전기 연차말이 아니라 전기 동기간(예: 작년 반기말)이라,
    BS의 '전기말'(전기 연차말)과 시점이 다르다(tieout.py의 WHY 가드와 동일 문제).
    이 조합에서 PY-END와 실제로 같은 시점을 갖는 행은 '당기초' 하나뿐이다."""
    m = SCE_END.search(label)
    if m:
        if m.group(1) == "당":
            return "CY-END"
        return None if interim else "PY-END"
    m = SCE_BEG.search(label)
    if m:
        return "PY-END" if m.group(1) == "당" else None
    return None


def _row_label(G, K, nrow, first_num, i):
    """행 라벨 = 첫 금액열 왼쪽의 첫 TEXT 셀 (core.check_table의 LC 판정과 동일 규약)."""
    for j in range(first_num):
        if G[i][j] and K[i][j] == "TEXT":
            return G[i][j], j
    return "", 0


def _locate_headings(pdf):
    """전 페이지에서 주석 헤더 위치를 (page, top, note_num) 리스트로 수집, 정렬해 반환.
    notes.NOTE_HEAD/AMT 그대로 재사용 — refmap.note_ranges와 같은 판정 규칙, 좌표만 추가."""
    out = []
    for pi, page in enumerate(pdf.pages, 1):
        for ln in page.extract_text_lines():
            t = ln["text"].strip()
            if AMT.search(t):
                continue
            m = NOTE_HEAD.match(t)
            if m:
                out.append((pi, ln["top"], int(m.group(1))))
    out.sort(key=lambda x: (x[0], x[1]))
    return out


def _note_for(headings, pi, top):
    """(page, top) 이전(≤)에 등장한 마지막 주석 헤더 번호. 못 찾으면 None."""
    best = None
    for p, t0, n in headings:
        if (p, t0) <= (pi, top):
            best = n
        else:
            break
    return best


def _note_prefix(table_id):
    m = re.match(r"n(\d+)", table_id or "")
    return m.group(1) if m else None


def _table_id_for_note(headings, seq_counter, pi, top):
    n = _note_for(headings, pi, top)
    if n is None:
        return None
    seq_counter[n] = seq_counter.get(n, 0) + 1
    return f"n{n}-t{seq_counter[n]}"


def extract(pdf_path):
    """→ list[dict] 원시 튜플 전량. 소액 컷 없음(설계 확정, L2는 컷 없이 전건).

    각 dict: raw_label, column_key, period_key, doc_key, value, mult, page,
             table_id, bbox(x0,top,x1,bottom), weak_col(bool), row, col
    """
    tuples = []
    with pdfplumber.open(pdf_path) as pdf:
        headings = _locate_headings(pdf)
        units = table_units(pdf)
        # 중간보고(반기·분기) 판정 — tieout.py의 interim 판정과 같은 신호(3개월 열
        # 존재)를 페이지 텍스트에서 값싸게 먼저 훑는다. SCE의 '전기말' 시점 해석이
        # 이 값에 갈린다(위 _row_period_sce 참고).
        interim = any(SPAN_3M.search(pg.extract_text() or "") for pg in pdf.pages)
        seq_counter = {}
        carry = None   # 직전 '헤더 있는' 표 정보 — 페이지 분할 이어받기용 (final.py와 같은 관행)

        for pi, page in enumerate(pdf.pages, 1):
            txt = page.extract_text() or ""
            st = stmt_type(txt)
            tobjs = page.find_tables()
            if not tobjs:
                carry = None
                continue
            for ti, t in enumerate(tobjs, 1):
                data = t.extract()
                if not data:
                    continue
                # 1행짜리(헤더만 있고 데이터가 페이지 경계 너머로 넘어간 표)도 통과시킨다
                # — 아래 'numcols 없음' 구제 경로가 헤더만 carry로 남기고 넘어간다
                # (조선내화 주석7 실측: '구분 당반기말 전기말' 헤더 행 하나만 페이지
                # 끝에 남고 데이터는 다음 페이지에서 시작).
                try:
                    G, K, V, hdr, ncol, nrow, numcols = grid_info(data)
                except Exception:
                    continue
                # 페이지 분할 이어받기: 표 제목이 반복되지 않는 연속 표(hdr==0)는 직전
                # '헤더 있는' 표의 열 구조(carry)를 그대로 물려받는다 — 그러지 않으면
                # 헤더 없는 페이지의 행이 통째로 판독 불가로 버려진다(조선내화 BS p7
                # 실측: 이익잉여금·비지배지분 전기말 값이 이 표에만 있었음).
                cont = (ti == 1 and hdr == 0 and carry is not None and carry["ncol"] == ncol)
                if hdr == 0 and not cont:
                    continue  # 헤더도 없고 이어받을 것도 없음 — 판독 불가
                mult = units.get((pi, ti))

                if cont:
                    table_id = carry["table_id"]
                elif st in ("BS", "IS", "CI", "CF", "SCE"):
                    table_id = st
                else:
                    table_id = _table_id_for_note(headings, seq_counter, pi, t.bbox[1])
                    if table_id is None:
                        continue  # 본표도 주석 구간도 아닌 표 — L2 범위 밖

                if not numcols:
                    # 데이터 행이 1개뿐이면 core.grid_info의 numcols 문턱(열당 NUM>=2)을
                    # 못 넘어 '숫자 열 없음'으로 나온다. 이 표 자체의 값은 포기하되,
                    # 헤더(hdr>0, 진짜 헤더)만은 carry에 남겨야 다음 페이지 이어받기가
                    # 끊기지 않는다(조선내화 주석17① 조정표 실측: 첫 행 "외화환산손실"
                    # 1행짜리 표가 다음 페이지 18행 continuation의 헤더 공급원이었음).
                    if hdr > 0 and ncol >= 2 and table_id != "SCE" and not cont:
                        hdr_rows = [_fill_merged(G[i], 1, ncol) for i in range(hdr)]
                        col_text = {j: " ".join(hdr_rows[i][j] for i in range(hdr) if j < len(hdr_rows[i]))
                                    for j in range(1, ncol)}
                        carry = {"table_id": table_id, "ncol": ncol, "col_text": col_text}
                    continue

                first_num = min(numcols)

                if table_id == "SCE":
                    # 자본변동표는 두 패턴이 섞여 있다 — 표 유형 하나로 고정 분기할 수 없어
                    # 행 종류별로 다시 가른다(설계안 2-3절이 상정한 것보다 한 겹 더 깊다):
                    #  · 시점행(당기말/당기초 등): 항목명은 '열'(자본금·이익잉여금...),
                    #    시점은 '행' — BS와 같은 항목명으로 대사(정답셋 1~3).
                    #  · 변동행(지분법자본변동 등, SCE_END/BEG에 안 걸리는 행): 항목명은
                    #    '행' 자신 — CI 등 다른 표의 같은 라벨과 대사(정답셋 7·8). 열은
                    #    '합계'(지배지분 소계) 열만 CI의 단일값과 대응하므로 column_key=None,
                    #    나머지 자본항목별 열은 column_key로 남겨 서로 안 섞이게 한다.
                    if cont:
                        hdrs, tot_j, cur = carry["hdrs"], carry["tot_j"], carry.get("sce_cur")
                    else:
                        hdrs = [next((G[i][j] for i in reversed(range(hdr)) if G[i][j]), "")
                                for j in range(ncol)]
                        tot_j = next((j for j in numcols if is_total_label(hdrs[j])), None)
                        cur = None
                        carry = {"table_id": table_id, "ncol": ncol, "hdrs": hdrs,
                                 "tot_j": tot_j, "sce_cur": cur}
                    for i in range(hdr, nrow):
                        lab, _lj = _row_label(G, K, nrow, first_num, i)
                        m_end, m_beg = SCE_END.search(lab), SCE_BEG.search(lab)
                        if m_end or m_beg:
                            cur = "CY" if (m_end or m_beg).group(1) == "당" else "PY"
                            carry["sce_cur"] = cur
                            pk_point = _row_period_sce(lab, interim)
                            for j in numcols:
                                if K[i][j] != "NUM":
                                    continue
                                colname = hdrs[j] if j < len(hdrs) else ""
                                if not colname or pk_point is None:
                                    continue
                                bb = t.rows[i].cells[j] if i < len(t.rows) and j < len(t.rows[i].cells) else None
                                tuples.append(dict(
                                    raw_label=skey(colname), column_key=None, period_key=pk_point,
                                    doc_key="CUR", value=V[i][j], raw_text=G[i][j], mult=mult, page=pi, table_seq=ti,
                                    table_id=table_id, bbox=bb, weak_col=False, row=i, col=j))
                            continue
                        if cur is None or not lab:
                            continue
                        pk = f"{cur}-CUM"        # 변동행 = 현재 구간(직전 시점행)의 누적 증감
                        lab_n = skey(lab)
                        for j in numcols:
                            if K[i][j] != "NUM":
                                continue
                            ck = None if j == tot_j else f"{hdrs[j]}@c{j}"
                            bb = t.rows[i].cells[j] if i < len(t.rows) and j < len(t.rows[i].cells) else None
                            tuples.append(dict(
                                raw_label=lab_n, column_key=ck, period_key=pk,
                                doc_key="CUR", value=V[i][j], raw_text=G[i][j], mult=mult, page=pi, table_seq=ti,
                                table_id=table_id, bbox=bb, weak_col=False, row=i, col=j))
                    continue

                # ── 일반 표 (BS/IS/CI/CF/주석): 열이 기간, 행이 라벨 ──
                if cont:
                    col_text = carry["col_text"]
                else:
                    hdr_rows = [_fill_merged(G[i], first_num, ncol) for i in range(hdr)]
                    col_text = {j: " ".join(hdr_rows[i][j] for i in range(hdr) if j < len(hdr_rows[i]))
                                for j in numcols}
                    # 구간 제목행 오판 구제: hdr==1인데 그 행이 실제로는 '유동항목'처럼
                    # 첫 열만 채워진 구간 제목(core.check_table의 secs와 같은 성격)이면
                    # 진짜 기간 헤더는 이 표에 없다 — 페이지 분할로 앞 페이지에 남아있는데
                    # grid_info가 이 제목행을 헤더로 오판해 hdr=0이 아니게 된 경우다.
                    # carry가 같은 주석 번호를 이어받는 중이고 이 표 헤더에서 기간 신호가
                    # 하나도 안 잡히면 carry의 열 헤더를 대신 쓴다(조선내화 주석7 실측:
                    # '출자금 등' 당반기말 값이 이 경로가 아니면 WEAK_COL로 빠짐).
                    title_row = (hdr == 1 and G[0][0] and not any(G[0][j] for j in range(1, ncol)))
                    steal = (title_row and carry is not None and carry["ncol"] == ncol
                             and _note_prefix(carry["table_id"]) == _note_prefix(table_id)
                             and all(_col_period(col_text.get(j, "")) is None for j in numcols))
                    if steal:
                        col_text = carry["col_text"]
                    carry = {"table_id": table_id, "ncol": ncol, "col_text": col_text}

                # 주석 표 전용: 총계행(합계·계·소계 등)이 물리적으로 한 표 안에 두 번 이상
                # 나오면 그건 서로 다른 소계 두 벌이 괘선 구분 없이 나란히 붙은 것이다
                # (조선내화 주석9(2) 실측: 손익표+배분표가 find_tables()에서 표 하나로
                # 잡힘, 각자 '합계' 행이 1천원 다름). 표 단위가 아니라 '합계행 단위'로
                # 끊는다(L1 판정 단위 원칙과 동일) — 총계행을 지날 때마다 블록을 새로
                # 연다. 본표(BS 등 자산총계·부채총계처럼 한 표 안에 여러 총계행이 있는
                # 것이 정상인 표)는 대상에서 뺀다 — table_id를 BS|IS|CI|CF|SCE로 고정
                # 유지해야 하는 설계와 충돌하기 때문.
                row_block = {}
                if table_id.startswith("n"):
                    blk = 1
                    for i in range(hdr, nrow):
                        row_block[i] = blk
                        lab_i, _ = _row_label(G, K, nrow, first_num, i)
                        if lab_i and is_total_label(lab_i):
                            blk += 1
                nblocks = max(row_block.values()) if row_block else 1

                for i in range(hdr, nrow):
                    lab, _lj = _row_label(G, K, nrow, first_num, i)
                    if not lab:
                        continue
                    lab_n = skey(lab)
                    tid_row = f"{table_id}.b{row_block[i]}" if nblocks >= 2 else table_id
                    for j in numcols:
                        if K[i][j] != "NUM":
                            continue
                        htext = col_text.get(j, "")
                        pk = _col_period(htext)
                        if pk is not None:
                            ck, weak = None, False
                        elif htext:
                            ck, weak = f"{htext}@c{j}", False
                        else:
                            ck, weak = f"c{j}", True
                        bb = t.rows[i].cells[j] if i < len(t.rows) and j < len(t.rows[i].cells) else None
                        tuples.append(dict(
                            raw_label=lab_n, column_key=ck, period_key=pk,
                            doc_key="CUR", value=V[i][j], raw_text=G[i][j], mult=mult, page=pi, table_seq=ti,
                            table_id=tid_row, bbox=bb, weak_col=weak, row=i, col=j))
    return tuples


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python l2_extract.py <보고서.pdf>"); sys.exit(2)
    ts = extract(sys.argv[1])
    print(f"원시 튜플 {len(ts)}건")
    for t in ts[:20]:
        print(f"  p{t['page']:>3} {t['table_id']:8s} {t['raw_label'][:20]:20s} "
              f"col={str(t['column_key'])[:16]:16s} period={str(t['period_key']):8s} "
              f"val={t['value']:>14,.0f}")
