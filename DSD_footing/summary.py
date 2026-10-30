# -*- coding: utf-8 -*-
"""검토 결과 요약 — 조서 첨부용 별지 1장을 만들어 틱마크 PDF 뒤에 붙인다 (U-6).

★ render.py를 건드리지 않는다. 요약은 원본 지면 위에 그리는 마크가 아니라 **새로
  만드는 별지**라 성격이 다르다 — 렌더러가 하나라는 결정 11은 '지면 위 드로잉'에
  대한 것이고, 여기는 그 대상이 아니다.

★ 출력은 `<원본>_검토완료.pdf`다. `<원본>_틱마크.pdf`에 덧붙이면 render_gate가
  페이지 수 변화를 불일치로 잡는다 — 파일을 분리해야 하는 이유다(설계안 §3).
  검토완료 PDF는 판단 내용에 따라 매번 달라지므로 **게이트 대상이 아니다.**

한글 폰트: reportlab 내장 CID 폰트(HYSMyeongJo-Medium)를 쓴다. 폰트 파일을 저장소에
넣지 않아도 되고(라이선스 문제 없음) 오프라인에서 동작한다. render.py의 기존 드로잉은
전부 ASCII(Helvetica)라 이 파일이 한글을 그리는 유일한 곳이다.
"""
import datetime, io, os
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from pypdf import PdfReader, PdfWriter

KFONT = "HYSMyeongJo-Medium"
RED = HexColor("#D0342C")
GRAY = HexColor("#6B7075")
DARK = HexColor("#22262A")
PAGE_W, PAGE_H = 595.28, 841.89          # A4

# 판단 → 회계사가 읽는 말. detail.js의 버튼 라벨과 같은 어휘를 쓴다(U-5 결정 20).
VERDICT_TEXT = {
    ("approved", "diff"): "이상없음",
    ("approved", "unverified"): "확인함",
    ("removed", "diff"): "차이 아님",
    ("removed", "unverified"): "해당없음",
}


def _font():
    try:
        pdfmetrics.getFont(KFONT)
    except Exception:
        pdfmetrics.registerFont(UnicodeCIDFont(KFONT))
    return KFONT


def tally(marks, judgments):
    """도구 지적 / 판단별 건수. status는 판단 파일이 원본이고, 없으면 pending이다."""
    out = {"total": len(marks), "approved": 0, "removed": 0, "pending": 0, "rows": []}
    for m in marks:
        j = judgments.get(m["id"]) or {}
        st = j.get("status") or m.get("status") or "pending"
        if st == "approved": out["approved"] += 1
        elif st == "removed": out["removed"] += 1
        else: out["pending"] += 1
        out["rows"].append({
            "page": m.get("page"), "account": m.get("account") or "",
            "type": m.get("type") or "diff", "status": st,
            "comment": (j.get("comment") or m.get("comment") or "").strip(),
            "reviewed_at": j.get("reviewed_at") or "",
        })
    out["rows"].sort(key=lambda r: (0 if r["status"] == "pending" else 1, r["page"]))
    return out


def _wrap(c, text, width, size):
    """폭에 맞춰 줄바꿈. 한글은 어절 단위로 끊는다."""
    if not text: return []
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, KFONT, size) <= width:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines


def draw(c, doc, t, reviewer, reviewed_on, page_no, total_pages):
    f = _font()
    y = PAGE_H - 60

    c.setFillColor(DARK); c.setFont(f, 15)
    c.drawString(50, y, "DSD 풋팅 검토 결과 요약"); y -= 8
    c.setStrokeColor(GRAY); c.setLineWidth(0.6); c.line(50, y, PAGE_W - 50, y); y -= 22

    d = doc.get("document") or {}
    run = doc.get("run") or {}
    c.setFont(f, 9); c.setFillColor(GRAY)
    # ★ run 블록의 키는 commit/at이다(marks.py). version/run_ts로 읽으면 조서에
    #   도구 버전·분석 일시가 '-'로 비어 나간다 — 추적성 정보라 빠지면 안 된다.
    #   실물 출력을 열어보고 잡은 결함이라, 키 이름을 바꿀 때 여기도 같이 볼 것.
    for label, val in (("문서", d.get("title") or doc.get("source", {}).get("pdf", "")),
                       ("검토자", reviewer or "(미입력)"),
                       ("검토 완료일", reviewed_on),
                       ("분석 일시", run.get("at") or "-"),
                       ("도구 버전", run.get("commit") or "-")):
        c.setFillColor(GRAY); c.drawString(50, y, label)
        c.setFillColor(DARK); c.drawString(120, y, str(val)[:80]); y -= 13
    y -= 10

    # ── 건수 ────────────────────────────────────────────────────────
    c.setFillColor(DARK); c.setFont(f, 11)
    c.drawString(50, y, "검토 현황"); y -= 18
    c.setFont(f, 10)
    rows = [("도구 지적", t["total"], DARK),
            ("  이상없음 / 확인함", t["approved"], DARK),
            ("  차이 아님 / 해당없음", t["removed"], DARK),
            ("  미검토", t["pending"], RED if t["pending"] else DARK)]
    for label, n, col in rows:
        c.setFillColor(col); c.drawString(58, y, label)
        c.drawRightString(210, y, f"{n}건"); y -= 14
    # 지면에서 빠진 건이 있으면 그 사실을 적는다 — 조서를 보는 사람이 오독하지 않게.
    if t["removed"]:
        c.setFillColor(GRAY); c.setFont(f, 8.5)
        c.drawString(58, y, f"[안내] '차이 아님/해당없음' {t['removed']}건은 지면에서 제외되어 있습니다"); y -= 13
    y -= 4

    # ★ 미검토가 남은 상태의 출력을 막지는 않는다(중간 출력이 실무에서 필요하다).
    #   다만 끝나지 않은 조서가 끝난 것처럼 보이면 안 되므로 눈에 띄게 적는다.
    if t["pending"]:
        c.setFillColor(RED); c.setFont(f, 10)
        c.drawString(50, y, f"[주의] 미검토 {t['pending']}건이 남아 있습니다 - 검토가 완료되지 않은 상태의 출력입니다")
        y -= 20

    # ── 판단 내역 ───────────────────────────────────────────────────
    c.setFillColor(DARK); c.setFont(f, 11)
    c.drawString(50, y, "판단 내역"); y -= 16
    y = _thead(c, f, y)

    for r in t["rows"]:
        if y < 70:
            _footer(c, page_no, total_pages); c.showPage(); page_no += 1
            # ★ 표 머리를 이어지는 장에도 다시 찍는다. 없으면 조서를 넘겨보는 사람이
            #   열이 무엇인지 알 수 없다(휴맥스 50건 실물에서 잡힌 결함).
            y = PAGE_H - 60
            c.setFillColor(DARK); c.setFont(f, 11)
            c.drawString(50, y, "판단 내역 (이어짐)"); y -= 16
            y = _thead(c, f, y)
        pend = r["status"] == "pending"
        c.setFillColor(RED if pend else DARK); c.setFont(f, 8.5)
        c.drawString(50, y, f"p{r['page']}")
        c.drawString(76, y, r["account"][:24])
        c.drawString(250, y, "미검토" if pend else VERDICT_TEXT.get((r["status"], r["type"]), r["status"]))
        c.setFillColor(GRAY)
        memo = _wrap(c, r["comment"], PAGE_W - 50 - 330, 8.5)
        if memo:
            c.drawString(330, y, memo[0][:60])
            for extra in memo[1:3]:
                y -= 10; c.drawString(330, y, extra[:60])
        y -= 13

    # ★ 맺음 문구를 그릴 자리가 모자라면 장을 넘긴다. 안 넘기면 푸터(y=28)와 겹쳐
    #   찍힌다 — 실측: 90행에서 "(candidate only검).토 결과 요약 2/2"처럼 두 문자열이
    #   포개졌다. 조서에서 글자가 겹치면 읽을 수 없다.
    if y < 62:
        _footer(c, page_no, total_pages); c.showPage(); page_no += 1
        y = PAGE_H - 60
    y -= 8
    c.setStrokeColor(GRAY); c.setLineWidth(0.3); c.line(50, y, PAGE_W - 50, y); y -= 14
    c.setFillColor(GRAY); c.setFont(f, 8)
    for ln in ("이 도구는 표시된 수치 사이의 정합성만 검증합니다. 원장 및 조서 대사는 별도 절차입니다.",
               "자동 판정은 추천이며 확정은 회계사입니다 (candidate only)."):
        c.drawString(50, y, ln); y -= 11
    _footer(c, page_no, total_pages)
    return page_no


def _thead(c, f, y):
    """판단 내역 표 머리. 첫 장과 이어지는 장 모두에서 같은 모양으로 쓴다."""
    c.setFont(f, 8); c.setFillColor(GRAY)
    c.drawString(50, y, "면"); c.drawString(76, y, "계정과목")
    c.drawString(250, y, "판단"); c.drawString(330, y, "검토 메모"); y -= 4
    c.setStrokeColor(GRAY); c.setLineWidth(0.3); c.line(50, y, PAGE_W - 50, y); y -= 12
    c.setFont(f, 8)
    return y


def _footer(c, page_no, total_pages):
    c.setFillColor(GRAY); c.setFont(KFONT, 7)
    c.drawCentredString(PAGE_W / 2, 28, f"검토 결과 요약 {page_no}/{total_pages}")


def build_pages(doc, judgments, reviewer, reviewed_on=None):
    """요약 PDF 바이트를 만든다. 항목이 많으면 여러 장이 된다."""
    _font()
    t = tally(doc.get("marks", []), judgments or {})
    reviewed_on = reviewed_on or datetime.date.today().isoformat()
    # ★ 장수를 추정하지 않고 두 번 그려서 센다. 종전 추정식은 첫 장 여유를 28행으로
    #   가정했는데 실제로는 37행이 들어갔다(휴맥스 실물) — 우연히 맞았을 뿐이고,
    #   어긋나면 조서에 "1/2"라고 적힌 3장짜리 요약이 나간다. 1장 더 그리는 비용이
    #   그 위험보다 싸다.
    scratch = canvas.Canvas(io.BytesIO(), pagesize=(PAGE_W, PAGE_H))
    total = draw(scratch, doc, t, reviewer, reviewed_on, 1, 1)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setTitle("DSD 풋팅 검토 결과 요약")
    draw(c, doc, t, reviewer, reviewed_on, 1, total)
    c.save()
    return buf.getvalue(), t


def append_to(tick_pdf, doc, judgments, reviewer, out_path, reviewed_on=None):
    """틱마크 PDF + 요약 별지 → out_path. 원본 틱마크 PDF는 건드리지 않는다."""
    pages, t = build_pages(doc, judgments, reviewer, reviewed_on)
    w = PdfWriter()
    with open(tick_pdf, "rb") as f:
        base = PdfReader(io.BytesIO(f.read()))     # 파일 핸들과 분리(결정 11의 함정)
    for p in base.pages:
        w.add_page(p)
    for p in PdfReader(io.BytesIO(pages)).pages:
        w.add_page(p)
    tmp = out_path + ".tmp"
    with open(tmp, "wb") as f:
        w.write(f)
    os.replace(tmp, out_path)
    return t
