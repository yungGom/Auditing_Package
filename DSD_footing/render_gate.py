# -*- coding: utf-8 -*-
"""render 회귀 게이트 (R-1 고정) — 등록 축의 마크 오버레이가 이전과 바이트 동일한지
확인한다. Phase 1(판정/렌더 분리) 착수 시 실측으로 잡은 두 함정을 여기 박아둔다:

  1. 좌표를 반올림하지 않는다. marks.py의 box4()에서 소수 반올림을 넣으면 reportlab이
     원래 값과 다르게 포맷해 바이트가 어긋난다(실측: 삼성 114페이지 전부 불일치).
     분석이 낸 좌표를 그대로 흘려야 한다.
  2. 비교 전에 버전/시각 스탬프를 고정한다. VER(git 커밋)·RUN_TS(실행 시각)는 매 실행
     마다 달라지는 게 정상이라, 고정하지 않으면 어떤 두 실행을 비교해도 무조건
     불일치가 난다("스탬프는 원래 다르니 통과로 치자"로 넘기지 말 것 — 애초에
     드로잉 바이트가 같은지를 볼 수 없게 되어 R-1이 무의미해진다).
  3. 비교 양쪽 모두 Canvas(invariant=1)가 필수(reportlab 기본값은 타임스탬프·문서ID가
     매번 달라 같은 입력이어도 바이트가 다르다).

이 게이트는 "이전 코드와의 비교"가 아니라 "지금 코드의 자기 결정성 + 저장된 골든
레퍼런스와의 일치"로 정의한다 — Phase 1 이전의 인라인 드로잉 코드는 이미 대체되어
비교 대상으로 남아있지 않기 때문이다. RENDER_GATES.json이 골든 레퍼런스다.

사용:
  python render_gate.py            # 등록 축 전부 대조
  python render_gate.py --update   # 현재 출력을 새 골든 레퍼런스로 기록
"""
import hashlib, json, os, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render  # noqa: E402  (final.py도 같은 모듈을 import하므로 sys.modules를 공유한다)
GATE_FILE = os.path.join(HERE, "RENDER_GATES.json")

FIXED_VER = "RGATE"
FIXED_TS = "2026-01-01 00:00"


class _FixedDT(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 1, 1, 0, 0)


def _patch_determinism():
    """VER/RUN_TS·Canvas(invariant=1)를 고정 — R-1 재현의 전제조건 (위 함정 2·3)."""
    import reportlab.pdfgen.canvas as canvas_mod
    orig_init = canvas_mod.Canvas.__init__
    def patched_init(self, *a, **kw):
        kw["invariant"] = 1
        return orig_init(self, *a, **kw)
    canvas_mod.Canvas.__init__ = patched_init

    class _Result:
        stdout = FIXED_VER
    subprocess.run = lambda *a, **kw: _Result()
    datetime.datetime = _FixedDT


def render_axis(pdf_path):
    """final.py를 고정 스탬프로 실행해 페이지별 오버레이 SHA256을 낸다."""
    _patch_determinism()
    import runpy
    argv = sys.argv
    sys.argv = [os.path.join(HERE, "final.py"), pdf_path, "0", "--quiet"]
    try:
        g = runpy.run_path(os.path.join(HERE, "final.py"), run_name="__main__")
    finally:
        sys.argv = argv
    assert g["VER"] == FIXED_VER and g["RUN_TS"] == FIXED_TS, "스탬프 고정 실패 — 함정 2 재발"
    doc = g["MARKS_DOC"]
    from pypdf import PdfReader
    import marks as marksio
    by_page = {}
    # v2에서 marks(검토 항목)/annotations(그리기 전용)로 나뉘었다. 게이트가 보는 것은
    # '그려지는 것 전량'이라 둘을 합친다 — 배열 분리만으로 total_marks가 307→8로
    # 떨어져 가짜 불일치가 나는 것을 막는다(스키마 변경이지 드로잉 변경이 아니다).
    drawables = marksio.drawables(doc)
    for m in drawables:
        by_page.setdefault(m["page"], []).append(m)
    notes_by_page = {}
    for n in doc.get("page_notes", []):
        notes_by_page.setdefault(n["page"], []).append(n)
    src = PdfReader(pdf_path)
    hashes = {}
    for i, pg in enumerate(src.pages, 1):
        mb = pg.mediabox
        W, H = float(mb.width), float(mb.height)
        b = render.render_page(by_page.get(i, []), notes_by_page.get(i, []), W, H, doc["run"])
        if b is not None:
            hashes[str(i)] = hashlib.sha256(b).hexdigest()
    return {"pages_with_marks": len(hashes), "total_marks": len(drawables),
            "page_hashes": hashes}


def load_gates():
    if not os.path.exists(GATE_FILE):
        return {}
    with open(GATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_gates(doc):
    with open(GATE_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


AXES = [
    "samples/삼성전자_감사보고서.pdf",
    "samples/[LG에너지솔루션]반기검토보고서(2025.08.14).pdf",
    "samples/[조선내화]연결감사보고서(2026.03.19).pdf",
    "samples/[휴맥스홀딩스]연결감사보고서(2025.03.19).pdf",
]

if __name__ == "__main__":
    update = "--update" in sys.argv
    gates = load_gates()
    ok = True
    for rel in AXES:
        pdf_path = os.path.join(HERE, rel)
        name = os.path.basename(rel)
        cur = render_axis(pdf_path)
        if update or name not in gates:
            gates[name] = cur
            print(f"[RENDER_GATE] 골든 레퍼런스 기록: {name} ({cur['pages_with_marks']}페이지, "
                  f"마크 {cur['total_marks']}개)")
            continue
        base = gates[name]
        diffs = [p for p in set(base["page_hashes"]) | set(cur["page_hashes"])
                  if base["page_hashes"].get(p) != cur["page_hashes"].get(p)]
        if not diffs and base["total_marks"] == cur["total_marks"]:
            print(f"[RENDER_GATE] 통과: {name} ({cur['pages_with_marks']}페이지 바이트 동일)")
        else:
            ok = False
            print(f"[RENDER_GATE] *** 불일치: {name} *** 페이지 {sorted(diffs, key=int)[:10]} "
                  f"/ 마크 수 {base['total_marks']}→{cur['total_marks']}")
    if update:
        save_gates(gates)
    sys.exit(0 if ok else 1)
