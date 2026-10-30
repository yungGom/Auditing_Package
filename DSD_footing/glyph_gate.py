# -*- coding: utf-8 -*-
"""글리프 오프셋 게이트 — UI 히트영역이 render.py의 실제 드로잉과 어긋나는 것을 막는다.

배경(2026-08-27, U-4 진단): 마크 글리프(✗ / ?)는 `box` 안이 아니라 box 오른쪽
경계를 넘어 그려진다(cross 6.5pt 중 5.0pt가 밖 — 오버레이 콘텐츠 스트림 실측).
그래서 UI가 "보이는 마크"를 클릭 대상으로 삼으려면 render.py의 그리기 공식을 알아야
하는데, 그 값을 UI에 복제해 두면 render.py가 바뀔 때 **아무 경고 없이** 히트영역만
어긋난다 — 이 프로젝트가 계속 막아온 침묵 실패다.

이 게이트가 닫는 고리:
    ui/glyph_offsets.json  ──(브리지)──▶  ui/web/hit.js   (UI가 읽는 유일한 출처)
            │
            └──(이 스크립트)──▶  render.draw_mark()가 실제로 호출한 좌표와 대조

즉 UI는 JSON에서만 값을 얻고, JSON은 이 게이트가 render.py에 묶어 둔다.
**상수 문자열을 비교하지 않는다** — render.py의 실제 그리기 함수를 마크마다 돌려
나온 좌표를 계산 결과와 맞춘다.

사용:
  python glyph_gate.py                     # samples/ 의 *_marks.json 전부 대조
  python glyph_gate.py <marks.json ...>     # 지정한 파일만
marks.json이 없으면 먼저 `python foot.py <보고서.pdf>`로 산출물을 만들 것.

이 게이트는 marks.json에 glyph_bbox가 직접 실리면 불필요해진다(CLAUDE.md 남은 과제).
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import render  # noqa: E402  판정/렌더 코드는 수정하지 않고 그대로 호출한다

OFFSETS = os.path.join(HERE, "ui", "glyph_offsets.json")
EPS = 1e-9


class RecordingCanvas:
    """reportlab Canvas 대역 — render.draw_mark()가 부르는 원시 호출만 기록한다.
    실제 PDF를 만들지 않으므로 빠르고, render.py를 한 줄도 고치지 않는다."""

    def __init__(self):
        self.lines = []    # (x1, y1, x2, y2)
        self.texts = []    # (x, y, text)

    # 상태 설정 — 좌표와 무관하므로 버린다
    def setStrokeColor(self, *a, **k): pass
    def setFillColor(self, *a, **k): pass
    def setLineWidth(self, *a, **k): pass
    def setLineCap(self, *a, **k): pass
    def setFont(self, *a, **k): pass

    def line(self, x1, y1, x2, y2):
        self.lines.append((x1, y1, x2, y2))

    def drawString(self, x, y, text):
        self.texts.append((x, y, text))

    def stringWidth(self, text, font, size):
        return len(text) * size * 0.55      # reftag 전용 — marks[]에는 없다

    # tick/circle 경로 (annotations 쪽). marks[]에는 안 나오지만 방어적으로 받아둔다
    def beginPath(self):
        return _Path(self)

    def drawPath(self, p, **k): pass

    def ellipse(self, *a, **k): pass


class _Path:
    def __init__(self, canvas):
        self.c = canvas
        self.cur = None

    def moveTo(self, x, y):
        self.cur = (x, y)

    def lineTo(self, x, y):
        if self.cur is not None:
            self.c.lines.append((self.cur[0], self.cur[1], x, y))
        self.cur = (x, y)


def glyph_key(mark):
    """glyph_offsets.json의 어떤 항목을 쓰는 마크인가."""
    kind = mark["kind"]
    if kind == "cross" and (mark.get("source") or {}).get("check") == "C":
        return "cross_C"
    if kind in ("cross", "question"):
        return kind
    return None            # tick/slash/circle/reftag/... = annotations, 검토 항목 아님


def expected_origin(mark, off):
    """JSON 값으로 계산한 글리프 시작점 (pdfplumber 좌상단 원점)."""
    b = mark["box"]
    return (b["x1"] + off["dx"], b["bottom"] - off["dy"])


def actual_origin(mark, page_height):
    """render.draw_mark()를 실제로 돌려 얻은 글리프 시작점 (pdfplumber 좌상단 원점).

    reportlab은 좌하단 원점이라 y를 되돌린다: top = page_height - y_reportlab."""
    c = RecordingCanvas()
    render.draw_mark(c, mark, page_height, 595.0)
    if mark["kind"] == "question":
        if not c.texts:
            return None
        x, y, _ = c.texts[0]
        return (x, page_height - y)
    if not c.lines:
        return None
    # cross()는 c.line(x, y, x+s, y+s)를 먼저 부른다 → 첫 호출의 시작점이 origin
    x1, y1, _x2, _y2 = c.lines[0]
    return (x1, page_height - y1)


def check_file(path, offsets):
    doc = json.load(open(path, encoding="utf-8"))
    page_height = 842.0     # 5축 전부 mediabox [0,0,595,842] (U-4 진단에서 실측)
    total = ok = skipped = 0
    fails = []
    for m in doc.get("marks", []):
        key = glyph_key(m)
        if key is None:
            skipped += 1
            continue
        total += 1
        off = offsets["glyph"].get(key)
        if off is None:
            fails.append((m["id"], f"glyph_offsets.json에 '{key}' 항목이 없음", None, None))
            continue
        exp = expected_origin(m, off)
        act = actual_origin(m, page_height)
        if act is None:
            fails.append((m["id"], "render.draw_mark()가 아무것도 그리지 않음", exp, None))
            continue
        if abs(exp[0] - act[0]) > EPS or abs(exp[1] - act[1]) > EPS:
            fails.append((m["id"], "글리프 시작점 불일치", exp, act))
            continue
        ok += 1
    return total, ok, skipped, fails


def main():
    if not os.path.isfile(OFFSETS):
        print(f"[GLYPH_GATE] *** 실패: {OFFSETS} 없음 ***")
        return 1
    offsets = json.load(open(OFFSETS, encoding="utf-8"))

    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    files = args or sorted(glob.glob(os.path.join(HERE, "samples", "*_marks.json")))
    if not files:
        print("[GLYPH_GATE] 대조 생략: samples/에 *_marks.json이 없습니다 — "
              "`python foot.py <보고서.pdf>`로 먼저 산출물을 만드세요.")
        return 0

    all_ok = True
    for f in files:
        total, ok, skipped, fails = check_file(f, offsets)
        name = os.path.basename(f)
        if fails:
            all_ok = False
            print("=" * 70)
            print(f"[GLYPH_GATE] *** 불일치 [{name}] — UI 히트영역이 render.py와 어긋납니다 ***")
            for mid, why, exp, act in fails:
                print(f"[GLYPH_GATE]   {mid}")
                print(f"[GLYPH_GATE]     {why}")
                if exp is not None:
                    print(f"[GLYPH_GATE]     JSON 계산={exp}  render.py 실제={act}")
            print("[GLYPH_GATE] render.py의 draw_mark()를 고쳤다면 ui/glyph_offsets.json도 "
                  "같이 고쳐야 합니다.")
            print("=" * 70)
        else:
            print(f"[GLYPH_GATE] 통과: {name} — 검토 항목 {ok}/{total}건 글리프 시작점 일치 "
                  f"(annotations {skipped}건 대상 외)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
