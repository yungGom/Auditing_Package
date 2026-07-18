# -*- coding: utf-8 -*-
"""
조회 모집단 완전성 — 데모/엔드투엔드 점검 스크립트 (외부 통신 없음).

하는 일:
  1) 머리글 3줄짜리 '예시_분개장.xlsx' 생성 (H1 헤더 자동탐지 시연용)
  2) 같은 파이프라인(헤더탐지 → 탐지 → 집계 → 전기 병합)으로 처리
  3) 산출물 '예시_조회대상_명세.xlsx' 저장 + 요약 출력

샘플 데이터는 전부 가상이다(실제 피감 데이터 아님).
사용: python demo_confirmation.py [출력폴더]   (기본=이 파일 폴더)
"""
import sys, os, io, json
import pandas as pd
from openpyxl import Workbook

import fi_detector as D
from report_builder import build_workbook
from mapping_utils import detect_header_row, guess_col, GUESS

# ── 가상 샘플 분개장 (머리글 3줄 + 헤더 + 데이터) ──
TITLE_ROWS = [
    ["주식회사 가나다 (가상) 분개장", "", "", "", "", ""],
    ["출력일자 2026-06-22  /  기간 2025-01-01 ~ 2025-12-31", "", "", "", "", ""],
    ["단위: 원", "", "", "", "", ""],
]
HEADER = ["전표일자", "거래처명", "계정과목", "적요", "차변금액", "대변금액"]
DATA = [
    ["2025-01-05", "신한은행",          "보통예금",       "이자입금",       "1,200,000", ""],
    ["2025-03-11", "신한은행 강남지점",  "보통예금",       "예금이자",       "500,000",   ""],
    ["2025-02-20", "㈜하나은행",         "단기차입금",     "차입금 상환",    "",          "30,000,000"],
    ["2025-04-01", "대구은행",          "정기예금",       "정기예금 예치",  "5,000,000", ""],
    ["2025-05-15", "삼성생명",          "보통예금",       "보험금 수령",    "200,000",   ""],
    ["2025-06-30", "미래에셋증권",      "단기매매증권",   "주식 매입",      "10,000,000",""],
    ["2025-07-10", "",                  "사채",          "사채이자 지급",  "",          "2,000,000"],
    ["2025-08-02", "페퍼저축은행",      "정기예금",       "정기예금 예치",  "1,000,000", ""],
    ["2025-09-09", "메리츠캐피탈",      "장기차입금",     "시설자금 차입",  "",          "50,000,000"],
    ["2025-10-01", "한국철강공업(매출원가)", "매출원가",   "원재료 매입",    "8,000,000", ""],
    ["2025-10-21", "행복식당",          "복리후생비",     "부서 회식",      "300,000",   ""],
    ["2025-11-30", "글로벌인베스트",    "선급금",        "투자 선급금",    "700,000,000",""],
]
# 전기 발송 조회처 (당기 미탐지분 흡수 시연: 농협/씨티)
PRIOR = ["신한은행", "KEB하나은행", "NH농협은행", "한국씨티은행"]


def make_sample(path):
    wb = Workbook(); ws = wb.active; ws.title = "분개장"
    for row in TITLE_ROWS + [HEADER] + DATA:
        ws.append(row)
    wb.save(path)


def build_records(df, cols):
    cv = guess_col(cols, GUESS["vendor"])
    ca = guess_col(cols, GUESS["account"])
    cm = guess_col(cols, GUESS["memo"])
    camt = guess_col(cols, GUESS["amount"])
    recs = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        def g(col):
            return str(r[col]) if col != "(없음)" and col in df.columns else ""
        amt = g(camt).replace(",", "").strip()
        try:
            amt = float(amt) if amt else 0.0
        except ValueError:
            amt = 0.0
        recs.append({
            "row_no": i, "source": "예시_분개장.xlsx", "kind": "분개장",
            "date": g("전표일자"), "slip_no": "",
            "account": g(ca).strip(), "vendor": g(cv).strip(),
            "memo": g(cm).strip(), "amount": amt,
            "raw": r.to_dict(), "raw_cols": cols,
        })
    return recs


def run(outdir):
    os.makedirs(outdir, exist_ok=True)
    sample = os.path.join(outdir, "예시_분개장.xlsx")
    make_sample(sample)

    # H1: 헤더행 자동 탐지
    probe = pd.read_excel(sample, header=None, nrows=21, dtype=str).fillna("")
    hrow = detect_header_row(probe.values.tolist())
    df = pd.read_excel(sample, header=hrow, dtype=str).fillna("")
    cols = list(df.columns)

    records = build_records(df, cols)
    hits = D.scan(records)
    cands = D.aggregate(hits)
    cands, added = D.merge_prior(cands, PRIOR)
    hit_rows = {h["row_no"] for h in hits}
    unmatched = [r for r in records if r["row_no"] not in hit_rows]

    out = os.path.join(outdir, "예시_조회대상_명세.xlsx")
    build_workbook(cands, hits, unmatched).save(out)

    n_online = sum(1 for c in cands if c["조회방법"] == "온라인 조회")
    n_review = len(cands) - n_online
    n_prior = sum(1 for c in cands if "전기" in c.get("포함근거", "") and c["발견건수"] == 0)

    print(f"[H1] 헤더행 자동 탐지 = {hrow}행 (기대 3)  ->  {'OK' if hrow == 3 else 'CHECK'}")
    print(f"[메트릭] 조회대상 {len(cands)} / 온라인 {n_online} / 서면·확인필요 {n_review} "
          f"/ 전기보유분 {n_prior} / 미매칭 안전망 {len(unmatched)}")
    print(f"[파일] 샘플  : {sample}")
    print(f"[파일] 산출물: {out}")

    # 화면 미리보기용 JSON (정렬은 report_builder 기준과 동일하게 form 순)
    from report_builder import sort_candidates
    rows = []
    for i, c in enumerate(sort_candidates(cands), 1):
        online = c["조회방법"] == "온라인 조회"
        rows.append({
            "no": f"BC{i}",
            "기관": c.get("온라인정식명") or c["기관(정규화)"],
            "조회": c["조회방법"],
            "전화번호": "" if online else c.get("전화번호", ""),
            "양식": c["조회서양식"],
            "포함근거": c.get("포함근거", "당기 탐지"),
            "발견": c["발견건수"],
        })
    metrics = {"조회대상": len(cands), "온라인": n_online, "서면확인필요": n_review,
               "전기보유분": n_prior, "미매칭": len(unmatched), "헤더행": hrow}
    print("PREVIEW_JSON_START")
    print(json.dumps({"metrics": metrics, "rows": rows}, ensure_ascii=False))
    print("PREVIEW_JSON_END")


if __name__ == "__main__":
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    run(outdir)
