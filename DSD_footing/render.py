# -*- coding: utf-8 -*-
"""render — marks.json + 원본 PDF → 틱마크 PDF. Phase 1: 판정/렌더 분리(렌더러 단일).

분석(final.py)과 완전히 분리되어 pdfplumber를 쓰지 않는다 — 페이지 크기는 pypdf의
mediabox에서 읽는다(4축 실측: pdfplumber page.width/height와 오차 0, 2026-08-14).
그리기 함수는 Phase 1 이전 final.py에서 그대로 옮겼다 — 바이트를 바꾸지 않는다.
완전 오프라인.

R-1(바이트 동등)이 관문이다: 마크를 seq(원래 그리기 순서) 그대로 재생하므로,
같은 marks.json이면 이 파일이 만드는 오버레이 바이트가 분리 이전 코드와 동일하다.
"""
import argparse, io, json, os, sys, time
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from pypdf import PdfReader, PdfWriter
import marks as marksio

RED = Color(0.78, 0.08, 0.08)          # 감사조서 관행: 빨간펜 단일 (설계 결정 #5, 고정)
GRN = RED; AMB = RED                   # 구분은 색이 아니라 마크 모양으로
GRAY_NOTE = Color(0.55, 0.55, 0.55)    # 분할 의심 참고 문구
GRAY_FOOTER = Color(0.35, 0.35, 0.35)  # 지면 하단 범례

# ── 그리기 원시함수 (Phase 1 이전 final.py에서 그대로 이관) ──────────────────
def tick(c, x, y, col, s=6.5):
    c.setStrokeColor(col); c.setLineWidth(1.4); c.setLineCap(1)
    p = c.beginPath(); p.moveTo(x, y+s*0.32); p.lineTo(x+s*0.36, y); p.lineTo(x+s*1.05, y+s*0.95)
    c.drawPath(p, stroke=1, fill=0)

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

def cross(c, x, y, col, s=6.5):
    c.setStrokeColor(col); c.setLineWidth(1.5); c.setLineCap(1)
    c.line(x, y, x+s, y+s); c.line(x, y+s, x+s, y)


def draw_mark(c, m, H, W):
    """box(pdfplumber 좌상단 원점, x0/top/x1/bottom)에서 kind별 절대 좌표를 유도해 그린다.
    box만으로 모든 kind를 그린다 — reportlab 하단 원점 변환은 여기(렌더러)가 전담한다.

    kind='cross'는 소스 체크에 따라 두 가지 서로 다른 유도식을 쓴다 — A1/A2/A3/A5의
    차이(DIFF)와 C(레퍼 차이)가 원래 다른 위치·크기로 그려졌다(Phase 1 이전 final.py의
    두 호출부). 마크 정의를 바꾸지 않으려면 이 구분을 유지해야 한다.
    """
    b = m["box"]; x0, t0, x1, b0 = b["x0"], b["top"], b["x1"], b["bottom"]
    kind = m["kind"]; check = (m.get("source") or {}).get("check")
    if kind == "tick":
        x = x1-1.5; y = H-b0+2.0
        tick(c, x, y, GRN)
    elif kind == "question":
        x = x1-1.5; y = H-b0+2.0
        c.setFont("Helvetica-Bold", 7.5); c.setFillColor(AMB)
        c.drawString(x, y, "?")
    elif kind == "cross" and check == "C":
        cross(c, x1+2.0, H-b0+1.5, RED, 5.0)
        if m.get("text"):
            c.setFont("Helvetica-Bold", 5.4); c.setFillColor(RED)
            c.drawString(x1+9, H-b0+2.0, m["text"])
    elif kind == "cross":
        x = x1-1.5; y = H-b0+2.0
        cross(c, x, y, RED)
        if m.get("text"):
            c.setFont("Helvetica-Bold", 5.6); c.setFillColor(RED)
            c.drawString(x+9, y+0.6, m["text"])
    elif kind == "slash":
        # box.x0에 x_end가 들어 있다(slash 원래 좌표가 x_end/top/bottom 3필드라 x1은 미사용
        # — marks.py의 box4 저장 규약 주석 참조)
        slash(c, x0, t0, b0, H, RED)
    elif kind == "circle":
        circle(c, x0, t0, x1, b0, H, RED)
    elif kind == "reftag":
        reftag(c, x1, t0, b0, H, RED, m.get("text") or "", W)
    elif kind == "flagword":
        flag_word(c, x0, t0, x1, b0, H, RED)
    elif kind == "gapx":
        c.setStrokeColor(RED); c.setLineWidth(0.9); c.setLineCap(1)
        c.line(x0+0.5, H-b0+1.0, x1-0.5, H-t0-1.0)
        c.line(x0+0.5, H-t0-1.0, x1-0.5, H-b0+1.0)
    else:
        raise ValueError(f"알 수 없는 kind: {kind!r}")


def _footer_text(run_meta):
    p = run_meta["params"]
    return ("tick=agreed  X=difference/wording  ?=not tested  /=narrative reviewed | "
            "local offline, candidate only"
            f" | v{run_meta['commit']} {run_meta['at']} tol={p['tol']:g} steps={p['round_steps']}")


def render_page(marks_for_page, notes_for_page, W, H, run_meta):
    """→ 오버레이 단일 페이지 PDF 바이트, 그릴 것이 없으면 None.
    marks/notes를 seq(원래 그리기 순서)로 병합해 재생 — reportlab Canvas는 직전 상태와
    같은 색/굵기 설정을 내부적으로 생략하므로, 순서가 바뀌면 바이트도 바뀐다."""
    # status: pending(도구 제안, 미검토) · approved(회계사 이상없음) 둘 다 그린다 —
    # 승인했다고 마크가 지면에서 사라지면 조서가 아니다. 빠지는 것은 removed뿐.
    items = [(m["seq"], "mark", m) for m in marks_for_page if m.get("status") != "removed"]
    items += [(n["seq"], "note", n) for n in notes_for_page]
    if not items:
        return None
    items.sort(key=lambda t: t[0])
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H), invariant=1)
    for _, typ, obj in items:
        if typ == "mark":
            draw_mark(c, obj, H, W)
        else:
            c.setFillColor(GRAY_NOTE); c.setFont("Helvetica", 5.4)
            c.drawString(36, 18, f"? split-suspect p{obj['prev']}->p{obj['page']} "
                                  f"({obj['reason']}) - reference only")
    c.setFillColor(GRAY_FOOTER); c.setFont("Helvetica", 5.4)
    c.drawString(36, 10, _footer_text(run_meta))
    c.save()
    return buf.getvalue()


def render_all(pdf_path, marks_doc, out_path, pages=None, existing_out=None, quiet=False):
    """marks_doc(marks.json을 로드한 dict) + 원본 PDF → 틱마크 PDF.

    pages         : 렌더할 페이지 번호 집합(1-based). None이면 전체(기본 실행 경로).
    existing_out  : pages 지정 시, 그 밖의 페이지는 이 파일의 기존 렌더 결과를 그대로
                    쓴다(부분 렌더 후 기존 출력에 병합). 없으면 원본 페이지(마크 없음).
    """
    t0 = time.time()
    by_page = {}
    # v2: 검토 항목(marks)과 그리기 전용(annotations)이 나뉘어 있다. 그리는 쪽에서는
    # 구분이 없으므로 합쳐서 seq 순으로 재생한다(v1 문서는 annotations가 없어 그대로 동작).
    for m in marksio.drawables(marks_doc):
        by_page.setdefault(m["page"], []).append(m)
    notes_by_page = {}
    for n in marks_doc.get("page_notes", []):
        notes_by_page.setdefault(n["page"], []).append(n)

    src = PdfReader(pdf_path)
    npages = len(src.pages)
    target_pages = set(pages) if pages else set(range(1, npages + 1))

    existing_reader = None
    if existing_out and os.path.isfile(existing_out):
        # 전량 메모리로 읽는다 — existing_out이 out_path와 같은 경로인 경우(부분 렌더의
        # 통상적 사용법)가 많은데, PdfReader가 파일을 지연 로딩한 채로 두면 아래에서
        # out_path를 쓰기 모드로 열 때 원본이 잘려나가 페이지가 빈 채로 읽힌다(실측
        # 확인). 쓰기 시작 전에 통째로 버퍼링해 원본 파일 핸들과 완전히 분리한다.
        with open(existing_out, "rb") as f:
            existing_reader = PdfReader(io.BytesIO(f.read()))

    writer = PdfWriter()
    for i, pg in enumerate(src.pages, 1):
        if i in target_pages:
            mb = pg.mediabox
            W, H = float(mb.width), float(mb.height)
            overlay = render_page(by_page.get(i, []), notes_by_page.get(i, []), W, H, marks_doc["run"])
            if overlay:
                pg.merge_page(PdfReader(io.BytesIO(overlay)).pages[0])
        elif existing_reader is not None and i <= len(existing_reader.pages):
            pg = existing_reader.pages[i - 1]
        writer.add_page(pg)
    with open(out_path, "wb") as f:
        writer.write(f)
    if not quiet:
        print(f"렌더 소요: {time.time()-t0:.3f}s ({len(target_pages)}페이지)")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="render",
        description="marks.json + 원본 PDF → 틱마크 PDF (분석 재실행 없음, 완전 오프라인)")
    ap.add_argument("pdf")
    ap.add_argument("--marks", required=True, help="marks.json 경로")
    ap.add_argument("--out", default=None, help="산출물 경로 (기본: <원본>_틱마크.pdf, 입력 폴더)")
    ap.add_argument("--pages", default=None, help="쉼표구분 페이지 번호만 재렌더, 예: 12,13")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    if not os.path.isfile(a.pdf):
        print(f"[오류] 파일이 없습니다: {a.pdf}"); sys.exit(2)
    if not os.path.isfile(a.marks):
        print(f"[오류] marks 파일이 없습니다: {a.marks}"); sys.exit(2)
    with open(a.marks, encoding="utf-8") as f:
        doc = json.load(f)
    base = os.path.splitext(os.path.basename(a.pdf))[0]
    outdir = os.path.dirname(os.path.abspath(a.pdf))
    out = a.out or os.path.join(outdir, base + "_틱마크.pdf")
    pages = {int(x) for x in a.pages.split(",") if x.strip()} if a.pages else None
    render_all(a.pdf, doc, out, pages=pages, existing_out=(out if pages else None), quiet=a.quiet)
    print(f"산출물: {out}")
