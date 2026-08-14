# -*- coding: utf-8 -*-
"""DSD 풋팅 엔진 — 통합 실행 (A1·A2·A3·A5·A7·B·C7·F1). 완전 오프라인."""
import argparse, datetime, io, os, subprocess, sys, collections
import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from core import check_table, verdict, find_unit, grid_info, mixed_currency, is_total_label
from statements import foot_hier, foot_a5, stmt_type, APPLY
import tieout, notes, prose, refmap, consist

_ap = argparse.ArgumentParser(prog="foot",
    description="DSD 풋팅 — 표시 수치 정합성 검증 → <원본>_틱마크.pdf / <원본>_예외색인.xlsx "
                "(완전 오프라인 · 자동은 추천, 확정은 회계사 — candidate only)")
_ap.add_argument("pdf", nargs="?", help="감사보고서 PDF 경로")
_ap.add_argument("tol_pos", nargs="?", type=float, help=argparse.SUPPRESS)  # 구형: final.py 보고서.pdf 0
_ap.add_argument("--tol", type=float, default=None, help="A7 허용오차 (기본 0)")
_ap.add_argument("--round-steps", dest="round_steps", type=int, default=1,
                 help="표 단위 스텝 허용 — 백만원 표=1백만원, 천원 표=1천원 (기본 1, 2026-08-09 확정)")
_ap.add_argument("--min-won", dest="min_won", type=float, default=refmap.MIN_WON,
                 help="C 대사 소액 제외, 원 환산 절대금액 (기본 1억)")
_ap.add_argument("--out", default=None, help="산출물 폴더 (기본: 입력 PDF와 같은 폴더)")
_ap.add_argument("--terms", default=None,
                 help="F2 기준 표현 CSV (한 줄에 표현 하나, # 주석). 미지정 시 빈도 기준")
_ap.add_argument("--quiet", action="store_true", help="요약 출력 생략")
_cli, _ = _ap.parse_known_args()                 # --update-gates 등은 gates.py가 처리
if not _cli.pdf:
    _ap.print_help(); sys.exit(2)

PDF = _cli.pdf
TOL = _cli.tol if _cli.tol is not None else (_cli.tol_pos if _cli.tol_pos is not None else 0.0)
RSTEPS = _cli.round_steps
MINWON = _cli.min_won
QUIET = _cli.quiet

# ── 입력 검증 ──
if not os.path.isfile(PDF):
    print(f"[오류] 파일이 없습니다: {PDF}"); sys.exit(2)
if not PDF.lower().endswith(".pdf"):
    print(f"[오류] PDF 파일이 아닙니다: {PDF}"); sys.exit(2)
with pdfplumber.open(PDF) as _p:
    _chars = sum(len(pg.extract_text() or "") for pg in _p.pages[:5])
if _chars < 100:
    print("[오류] 텍스트 레이어가 없습니다(스캔본 추정). OCR은 조용히 틀리므로 설계상 "
          "사용하지 않습니다 — 이 파일은 처리를 거부합니다."); sys.exit(2)

_base = os.path.splitext(os.path.basename(PDF))[0]
_outdir = _cli.out or (os.path.dirname(os.path.abspath(PDF)) or ".")
os.makedirs(_outdir, exist_ok=True)
OUT_PDF = os.path.join(_outdir, _base + "_틱마크.pdf")
OUT_XLSX = os.path.join(_outdir, _base + "_예외색인.xlsx")

# ── 버전 스탬프 (감사조서 추적성) ──
try:
    VER = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True,
                         text=True, cwd=os.path.dirname(os.path.abspath(__file__))
                         ).stdout.strip() or "nogit"
except Exception:
    VER = "nogit"
RUN_TS = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ── F2 기준 표현 (고정 템플릿, 선택) ──
# 회계법인/조서 관행상 기준 표현이 정해져 있으면 빈도 대신 그 표현을 주된 표기로 쓴다.
# 파일이 없거나 미지정이면 현행(빈도 기준) 동작 그대로.
TERMS = set()
if _cli.terms:
    try:
        with open(_cli.terms, encoding="utf-8-sig") as _tf:
            for _ln in _tf:
                _t = _ln.split(",")[0].strip()
                if _t and not _t.startswith("#"):
                    TERMS.add(_t.replace(" ", ""))
    except OSError:
        print(f"[경고] --terms 파일을 열 수 없습니다: {_cli.terms} — 빈도 기준으로 진행")
RED=Color(0.78,0.08,0.08)          # 감사조서 관행: 빨간펜 단일
GRN=RED; AMB=RED                   # 구분은 색이 아니라 마크 모양으로

def tick(c,x,y,col,s=6.5):
    c.setStrokeColor(col); c.setLineWidth(1.4); c.setLineCap(1)
    p=c.beginPath(); p.moveTo(x,y+s*0.32); p.lineTo(x+s*0.36,y); p.lineTo(x+s*1.05,y+s*0.95)
    c.drawPath(p,stroke=1,fill=0)
def slash(c, x_end, t0, b0, H, col):
    """검토 완료 사선(/) — 줄글 문단 마지막 줄 끝에 표시"""
    yb, yt = H-b0, H-t0
    h = max(yt-yb, 8.0)
    c.setStrokeColor(col); c.setLineCap(1); c.setLineWidth(1.2)
    c.line(x_end+3.5, yb+0.2, x_end+3.5+h*0.40, yb+h*0.95)

def circle(c, x0, t0, x1, b0, H, col):
    """레퍼 성립 — 본표 주석번호에 타원"""
    cx=(x0+x1)/2; cy=H-(t0+b0)/2; rx=(x1-x0)/2+2.8; ry=(b0-t0)/2+1.8
    c.setStrokeColor(col); c.setLineWidth(0.8)
    c.ellipse(cx-rx, cy-ry, cx+rx, cy+ry, stroke=1, fill=0)

def reftag(c, x1, t0, b0, H, col, text, W):
    """레퍼 성립 — 주석 숫자 위쪽에 /BS, FN6 (지면 밖 방지)"""
    c.setFillColor(col); c.setFont("Helvetica-Bold", 5.2)
    w = c.stringWidth(text, "Helvetica-Bold", 5.2)
    x = min(x1 + 2.0, W - w - 6.0)
    c.drawString(x, H - t0 - 5.2, text)

def flag_word(c, x0, t0, x1, b0, H, col):
    """표기 지적 — 어절에 밑줄 + X"""
    yb, yt = H-b0, H-t0
    c.setStrokeColor(col); c.setLineCap(1)
    c.setLineWidth(0.6); c.line(x0, yb+0.6, x1, yb+0.6)
    cross(c, x1+3.0, yb+1.0, col, 5.0)

def cross(c,x,y,col,s=6.5):
    c.setStrokeColor(col); c.setLineWidth(1.5); c.setLineCap(1)
    c.line(x,y,x+s,y+s); c.line(x,y+s,x+s,y)

FCON = consist.report(PDF)
CIR, TAGS, RDIFF, RLINKS, RUN, RMAIN, REXCL = refmap.marks(PDF, TOL, MINWON)
TUNIT = refmap.unit_texts(PDF)                 # 표 귀속 단위 원문 — 복합 통화 A2 제외용
cirmap=collections.defaultdict(list); dmap=collections.defaultdict(list)
for x in CIR: cirmap[(x["page"], x["table"])].append(x)
for x in RDIFF: dmap[(x["page"], x["table"])].append(x)
tagmap=collections.defaultdict(list)
for (pg_,tb_,rw_,cl_), lbls in TAGS.items(): tagmap[(pg_,tb_)].append((rw_,cl_,lbls))

exc=[]; overlays={}; carry=None; stat=collections.Counter(); nounit=[]; pros=[]; npara=0
SUBLOG=[]                              # 하위항목(소계 귀속) 판정 로그 — 경로별 검증용
with pdfplumber.open(PDF) as pdf:
    for pi,page in enumerate(pdf.pages,1):
        W,H=page.width,page.height
        txt=page.extract_text() or ""
        unit=find_unit(txt); st=stmt_type(txt)
        tobjs=page.find_tables()
        pr=prose.check_page(page); paras=prose.paragraphs(page)
        if not tobjs and not pr and not paras: carry=None; continue
        if not unit: nounit.append(pi)
        buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=(W,H)); drew=False
        for gp in [g for g in FCON["F4_다중공백"] if g["page"]==pi]:
            x0,t0,x1,b0 = gp["bbox"]
            c.setStrokeColor(RED); c.setLineWidth(0.9); c.setLineCap(1)
            c.line(x0+0.5, H-b0+1.0, x1-0.5, H-t0-1.0)
            c.line(x0+0.5, H-t0-1.0, x1-0.5, H-b0+1.0); drew=True
        for pg_ in paras:
            slash(c, pg_["bbox"][0], pg_["bbox"][1], pg_["bbox"][2], H, RED); drew=True
            npara += 1
        for pz in pr:
            flag_word(c, *pz["bbox"], H, RED); drew=True
            pros.append([pi, pz["text"], pz["msg"], pz["level"]])
        for ti,t in enumerate(tobjs,1):
            data=t.extract()
            if not data or len(data)<2: continue
            off=0
            if ti==1 and carry is not None:
                try:
                    _,_,_,h0,nc0,_,_=grid_info(data)
                    if h0==0 and nc0==carry[1]: off=len(carry[0]); data=carry[0]+data
                except Exception: pass
            x0s=[]                                       # 첫 열 라벨 x0 — 들여쓰기 하위항목 판정용
            pwords = page.extract_words()
            for rr in t.rows:
                bb = rr.cells[0] if rr.cells else None
                xw = None
                if bb:
                    ws_=[w["x0"] for w in pwords
                         if bb[0]-1 <= w["x0"] and w["x1"] <= bb[2]+1
                         and bb[1]-1 <= w["top"] and w["bottom"] <= bb[3]+1]
                    xw = min(ws_) if ws_ else None
                x0s.append(xw)
            if off: x0s = [None]*off + x0s               # carry 병합 행은 좌표 미상
            rs = check_table(data, x0s=x0s, sublog=SUBLOG, ctx=(pi,ti),
                             excl_a2=mixed_currency(TUNIT.get((pi,ti))))  # A1·A2 (+구형 A3 제거됨)
            rs = [r for r in rs if r["kind"] in ("A1","A2")]
            if "A3" in APPLY.get(st, ()): rs += foot_hier(data)
            if "A5" in APPLY.get(st,()):      rs += foot_a5(data)
            def cellbox(gi, cj):
                gi -= off
                if not (0 <= gi < len(t.rows)): return None
                cells = t.rows[gi].cells
                if cj is not None and cj < len(cells) and cells[cj]: return cells[cj]
                for cc in reversed(cells):
                    if cc: return cc
                return None
            for x in cirmap.get((pi,ti), []):
                bb = cellbox(x["row"]+off, x["ncol"])
                if not bb: continue
                want = {str(n) for n in x["notes"]}
                for wd in page.extract_words():
                    if not (bb[0]-1 <= wd["x0"] and wd["x1"] <= bb[2]+1
                            and bb[1]-1 <= wd["top"] and wd["bottom"] <= bb[3]+1): continue
                    txt = wd["text"].strip()
                    if txt.rstrip(",") in want:
                        x1w = wd["x1"]
                        if txt.endswith(","):            # 뒤 쉼표는 원 밖으로
                            x1w -= (wd["x1"]-wd["x0"]) / max(len(txt),1) * 0.75
                        circle(c, wd["x0"], wd["top"], x1w, wd["bottom"], H, RED)
                        drew=True
            for rw_, cl_, lbls in tagmap.get((pi,ti), []):
                bb = cellbox(rw_+off, cl_)
                if bb:
                    seen=[]; [seen.append(l) for l in lbls if l not in seen]
                    reftag(c, bb[2], bb[1], bb[3], H, RED, " ".join(seen[:2]), W); drew=True
            for x in dmap.get((pi,ti), []):
                bb = cellbox(x["row"]+off, x["col"])
                if bb:
                    cross(c, bb[2]+2.0, H-bb[3]+1.5, RED, 5.0); drew=True
                    c.setFont("Helvetica-Bold",5.4); c.setFillColor(RED)
                    c.drawString(bb[2]+9, H-bb[3]+2.0, f"{x['diff']:+,.0f} {x['where']}")
            for r in rs:
                v=verdict(r,TOL,RSTEPS); stat[v]+=1
                gi=r.get("row"); bbox=None
                if gi is not None:
                    gi-=off
                    if 0<=gi<len(t.rows):
                        cells=t.rows[gi].cells; cj=r.get("col")
                        if cj is not None and cj<len(cells) and cells[cj]: bbox=cells[cj]
                        else:
                            for cc in reversed(cells):
                                if cc: bbox=cc; break
                if bbox:
                    x0,t0,x1,b0=bbox; y=H-b0+2.0; x=x1-1.5
                    if v=="OK": tick(c,x,y,GRN); drew=True
                    elif v=="ROUND": tick(c,x,y,AMB); drew=True
                    elif v=="DIFF":
                        cross(c,x,y,RED); drew=True
                        c.setFont("Helvetica-Bold",5.6); c.setFillColor(RED)
                        c.drawString(x+9,y+0.6,f"{r['calc']-r['disp']:+,.0f}")
                    else:
                        c.setFont("Helvetica-Bold",7.5); c.setFillColor(AMB)
                        c.drawString(x,y,"?"); drew=True
                if v in ("DIFF","ROUND","SKIP","SIGN"):
                    # '1원차이' 태그 — 원 단위 표에서 |차이|<=1이면 일괄 확인용 표시.
                    # 판정은 바꾸지 않는다 (원 단위는 반올림이 없어 흡수 금지 — 회계사 확인 대상)
                    tg = ("부호규약" if v == "SIGN" else
                          "1원차이" if v == "DIFF" and abs(r["calc"]-r["disp"]) <= 1
                          and (TUNIT.get((pi,ti)) or "").strip() == "원" else "")
                    exc.append([pi,ti,r["kind"],r["label"],unit or "미표기",
                                r["disp"],r["calc"],r["calc"]-r["disp"],r["n"],
                                {"DIFF":"차이","ROUND":"단수차이","SKIP":"미검증","SIGN":"미검증"}[v],tg])
        try:
            _,_,_,_,ncL,_,_=grid_info(tobjs[-1].extract()); carry=(tobjs[-1].extract(),ncL)
        except Exception: carry=None
        if drew:
            c.setFillColor(Color(0.35,0.35,0.35)); c.setFont("Helvetica",5.4)
            c.drawString(36,10,"tick=agreed  X=difference/wording  ?=not tested  /=narrative reviewed | local offline, candidate only"
                         f" | v{VER} {RUN_TS} tol={TOL:g} steps={RSTEPS}")
            c.save(); overlays[pi]=buf.getvalue()

B,cons = tieout.run(PDF)
decl,refs,miss,unref,gap = notes.run(PDF)

src=PdfReader(PDF); w=PdfWriter()
for i,pg in enumerate(src.pages,1):
    if i in overlays: pg.merge_page(PdfReader(io.BytesIO(overlays[i])).pages[0])
    w.add_page(pg)
with open(OUT_PDF,"wb") as f: w.write(f)

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
wb=openpyxl.Workbook()
def sheet(name, hdr, rows, widths):
    ws=wb.create_sheet(name); ws.append(hdr)
    for cc in ws[1]:
        cc.font=Font(bold=True,color="FFFFFF"); cc.fill=PatternFill("solid",fgColor="404040")
        cc.alignment=Alignment(horizontal="center")
    for r in rows: ws.append(r)
    for i,wd in enumerate(widths,1): ws.column_dimensions[chr(64+i)].width=wd
    ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
    return ws
wb.remove(wb.active)
ws=sheet("A_예외색인",["페이지","표","유형","항목","단위","표시금액","계산금액","차이","항목수","판정","태그"],
         exc,[8,6,8,30,10,18,18,16,8,10,10])
for row in ws.iter_rows(min_row=2):
    for cc in row[5:8]: cc.number_format="#,##0"
    if row[9].value=="차이": row[9].fill=PatternFill("solid",fgColor="FFC7CE")
    elif row[9].value=="미검증": row[9].fill=PatternFill("solid",fgColor="FFEB9C")
wsb=sheet("B_본표간연계",["번호","검증항목","값1","값2","판정"],
          [[a,b,c_,d_,e] for a,b,c_,d_,e,_ in B],[8,52,18,18,10])
for row in wsb.iter_rows(min_row=2):
    for cc in row[2:4]: cc.number_format="#,##0"
    if row[4].value=="차이": row[4].fill=PatternFill("solid",fgColor="FFC7CE")
    elif row[4].value=="미검증": row[4].fill=PatternFill("solid",fgColor="FFEB9C")
sheet("C_본표주석레퍼",["구분","페이지","항목","금액","대상","비고"],
      [["성립",m["page"],m["label"],m["val"],
        " ".join(sorted({f"FN{n}" for c_ in cs for n in (c_["notes"] & m["refs"])})),
        f"주석 p{sorted({c_['page'] for c_ in cs})}"] for m,cs in RLINKS]
    + [["미성립",m["page"],m["label"],m["val"],
        " ".join(f"FN{n}" for n in sorted(m["refs"])),"주석에서 동일 금액 미발견"] for m,_ in RUN]
    + [["단위제외",m["page"],m["label"],m["val"],
        " ".join(f"FN{n}" for n in sorted(m["refs"])),"복합·판독 불가 단위 — 대사 미수행(?)"] for m in REXCL],
      [10,8,28,18,16,30])
_frows=[]
for p_ in FCON["F1_단위누락"]:
    _frows.append(["F1 단위누락", p_, "-", "금액 표가 있으나 (단위: ) 표기 없음", ""])
for g_, forms in FCON["F2_표현불일치"]:
    _pref = [f_ for f_ in forms if f_ in TERMS]       # 기준 표현 지정 시 빈도보다 우선
    if _pref:
        dom = (_pref[0], forms[_pref[0]]); _why = f"기준 표현 '{dom[0]}'(지정)과 불일치"
    else:
        dom = max(forms.items(), key=lambda x: x[1][0])
        _why = f"주된 표현 '{dom[0]}'({dom[1][0]}회)과 불일치"
    for f_, (n_, ps_) in sorted(forms.items(), key=lambda x: -x[1][0]):
        if f_ == dom[0]: continue
        _frows.append(["F2 표현불일치", ps_[0] if ps_ else "-", f_,
                       f"{_why} — {n_}회",
                       " ".join(f"p{x}" for x in ps_)])
for k_, forms, tot in FCON["F3_라벨불일치"]:
    dom = max(forms.items(), key=lambda x: x[1][0])
    for f_, (n_, ps_) in sorted(forms.items(), key=lambda x: -x[1][0]):
        if f_ == dom[0]: continue
        _frows.append(["F3 라벨불일치", ps_[0] if ps_ else "-", f_,
                       f"주된 표기 '{dom[0]}'({dom[1][0]}회)과 불일치 — {n_}회",
                       " ".join(f"p{x}" for x in ps_)])
for g_ in FCON["F4_다중공백"]:
    _frows.append(["F4 다중공백", g_["page"], f"{g_['before']} | {g_['after']}",
                   "어절 간격이 통상보다 넓음", ""])
sheet("F_일관성",["유형","페이지","대상","내용","출현위치"],_frows,[14,8,26,44,30])
sheet("D_줄글표기",["페이지","지적어절","내용","신뢰도"],pros,[8,20,40,10])
sheet("C7_주석참조",["구분","내용"],
      [["선언된 주석 수",len(decl)],["본표 참조 수",len(refs)],
       ["참조됐으나 주석 없음",str(miss or "없음")],
       ["주석 있으나 본표 미참조",str(unref or "없음")],
       ["주석번호 결번",str(gap or "없음")]],[26,60])
tot=sum(stat.values())
sheet("요약",["항목","값"],
      [["A 산술검증 총건수",tot],["  OK",stat['OK']],["  단수차이(ROUND)",stat['ROUND']],
       ["  차이(DIFF)",stat['DIFF']],["  미검증(SKIP)",stat['SKIP']],
       ["  OK 비율",f"{stat['OK']/tot*100:.1f}%" if tot else "-"],
       ["B 연계검증 총건수",len(B)],["  OK",sum(1 for r in B if r[4]=='OK')],
       ["  차이",sum(1 for r in B if r[4]=='차이')],["  미검증",sum(1 for r in B if r[4]=='미검증')],
       ["D 검토완료(/) 문단 수",npara],["D 표기 지적 건수",len(pros)],
       ["허용오차(A7)",TOL],["round_steps(표 단위 스텝)",RSTEPS],
       ["min_won(C 소액 제외, 원)",MINWON],["연결 구조 감지",str(cons)],
       ["단위 미표기 페이지",str(nounit or "없음")],
       ["도구 버전(커밋)",VER],["실행 일시",RUN_TS],
       ["범위","표시 수치 상호 정합성 한정. 원장·조서 대사는 별도 절차."]],[30,60])
wb.save(OUT_XLSX)
if not QUIET:
    print(f"A 산술 {tot}건 → OK {stat['OK']} ({stat['OK']/tot*100:.1f}%) / ROUND {stat['ROUND']} / DIFF {stat['DIFF']} / SKIP {stat['SKIP']} / SIGN {stat['SIGN']}")
    print(f"B 연계 {len(B)}건 → OK {sum(1 for r in B if r[4]=='OK')} / 차이 {sum(1 for r in B if r[4]=='차이')} / 미검증 {sum(1 for r in B if r[4]=='미검증')}")
    print(f"C 레퍼 → 성립 {len(RLINKS)} / 미성립 {len(RUN)} / 차이 {len(RDIFF)}" +
          (f" · 단위제외 {len(REXCL)}건" if REXCL else ""))
    print(f"F 일관성 → 단위누락 {len(FCON['F1_단위누락'])}p / 표현불일치 {len(FCON['F2_표현불일치'])}그룹 / 라벨불일치 {len(FCON['F3_라벨불일치'])}건 / 다중공백 {len(FCON['F4_다중공백'])}건")
    print(f"D 줄글 → 검토완료(/) {npara}문단 / 표기 지적 {len(pros)}건")
    print(f"C7 주석 → 결번 {gap or '없음'} / 참조무주석 {miss or '없음'}")
    _sub_pre = sum(1 for e in SUBLOG if e["path"]=="접두")
    _sub_ind = [e for e in SUBLOG if e["path"].startswith("들여쓰기")]
    print(f"하위항목 인식 → 총 {len(SUBLOG)}건 (접두 {_sub_pre} / 들여쓰기 {len(_sub_ind)})")
    for e in _sub_ind:
        print(f"  [들여쓰기] p{e['ctx'][0]} 표{e['ctx'][1]} 행{e['row']} '{e['label']}' ← 상위 '{e['parent']}' ({e['path']})")
    print(f"연결 감지 {cons} · 단위 미표기 {nounit or '없음'} · 허용오차 ±{TOL:g}")
print(f"산출물: {OUT_PDF} · {OUT_XLSX}")
