# -*- coding: utf-8 -*-
"""
조회 모집단 완전성 검토 (금융기관 스크리닝)
- 분개장/명세서 업로드 → 컬럼 매핑 → 탐지 → 전기 조회처 병합 → 화면 표시 + Excel 다운로드
- 전부 로컬 처리. 외부 통신 없음.
"""
import sys, os, io
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fi_detector as D
from report_builder import build_workbook, sort_candidates
from mapping_utils import GUESS, guess_col, detect_header_row, resolve_mapping
from profile_store import match_mapping, save_profile, default_path as profile_path

st.set_page_config(page_title="조회 모집단 완전성", page_icon="📨", layout="wide")
st.title("📨 조회 모집단 완전성 검토 — 금융기관 스크리닝")
st.caption("분개장·명세서에서 조회 대상을 자동 추출 · 온라인 조회 가능 여부 판정 · 전기 조회처 자동 병합")

def guess_kind(fname):
    n = str(fname)
    if "분개" in n or "전표" in n or "원장" in n:
        return "분개장"
    if "명세" in n:
        return "명세서"
    return "기타"

def read_excel_safe(file, header_row):
    try:
        return pd.read_excel(file, header=header_row, dtype=str).fillna("")
    except Exception as e:
        st.error(f"읽기 오류: {e}")
        return None

def sidebar():
    with st.sidebar:
        st.markdown("### 🔒 로컬 전용")
        st.caption("업로드 파일은 외부로 전송되지 않으며 이 PC에서만 처리됩니다.")
        st.markdown("### 📚 사전 현황")
        st.caption(f"금융기관 사전: {sum(len(v) for v in D.FI_DICT.values())}개 키워드")
        st.caption(f"온라인 조회 참가기관: {len(D.ONLINE_FI)}개")
        with st.expander("온라인 조회 참가기관 보기"):
            st.dataframe(pd.DataFrame(
                [{"기관": n, "유형": t} for n, t, d, tel in D.ONLINE_FI]),
                use_container_width=True, hide_index=True, height=280)

# ── 1) 업로드 ──
st.markdown("### 1️⃣ 분개장·명세서 업로드")
files = st.file_uploader(
    "엑셀 파일을 올려주세요 (분개장·예금/차입금/유가증권 명세서 등, 여러 개 가능)",
    type=["xlsx", "xls"], accept_multiple_files=True)

if not files:
    st.info("거래처·적요·계정·금액이 들어있는 분개장과 각종 명세서를 올리면 자동으로 금융기관을 탐지합니다.")
    sidebar()
    st.stop()

# ── 2) 컬럼 매핑 ──
st.markdown("### 2️⃣ 컬럼 매핑 확인")
st.caption("파일 종류를 자동 추정했습니다. 컬럼 매핑이 틀리면 직접 바꿔주세요. (자동 인식보다 직접 확인이 안전합니다)")

records = []
row_counter = 1
for f in files:
    kind = guess_kind(f.name)
    with st.expander(f"📄 {f.name}  ·  추정: {kind}", expanded=True):
        raw_bytes = f.getvalue()
        # H1: 상단을 스캔해 헤더 행을 자동 추정 → number_input 기본값으로 제공
        default_hrow = 0
        try:
            probe = pd.read_excel(io.BytesIO(raw_bytes), header=None, nrows=21,
                                  dtype=str).fillna("")
            default_hrow = detect_header_row(probe.values.tolist())
        except Exception:
            default_hrow = 0
        hrow = st.number_input(
            f"[{f.name}] 헤더 행 번호 (0=첫 행)", 0, 20, int(default_hrow),
            key=f"h_{f.name}",
            help="상단 행을 스캔해 자동 추정한 값입니다. 머리글이 여러 줄이면 직접 조정하세요.")
        if default_hrow > 0:
            st.caption(f"🔎 헤더 행 자동 추정: {default_hrow}행 (0=첫 행). 틀리면 위에서 조정하세요.")
        df = read_excel_safe(io.BytesIO(raw_bytes), hrow)
        if df is None or df.empty:
            continue
        cols = list(df.columns)
        opts = ["(없음)"] + cols
        # H3: 같은 양식(헤더 시그니처) 파일이면 저장된 매핑/ERP 프리셋 자동 적용
        prof, psource, sig = match_mapping(cols)
        if psource == "user":
            st.success("📌 저장된 매핑을 자동 적용했습니다. 맞는지 확인만 하세요.")
        elif psource == "preset":
            st.info(f"🧩 ERP 프리셋 추정 적용: {prof.get('label','')}. 확인 후 저장하면 다음부터 우선 적용됩니다.")
        # H2: 헤더명 동의어 + 데이터 시그니처 보조 추정 (저장본 없을 때 위치 추정)
        auto = resolve_mapping(cols, df.to_dict("list"))

        def idx(field, keys):
            # 우선순위: 저장본/프리셋 → 헤더명+데이터 보조 추정 → (없음)
            if prof and prof.get(field) in opts:
                return opts.index(prof[field])
            if auto.get(field) in opts:
                return opts.index(auto[field])
            return 0
        c1, c2, c3, c4 = st.columns(4)
        cv = c1.selectbox("거래처명 *", opts, index=idx("vendor", GUESS["vendor"]), key=f"v_{f.name}")
        ca = c2.selectbox("계정과목", opts, index=idx("account", GUESS["account"]), key=f"a_{f.name}")
        cm = c3.selectbox("적요", opts, index=idx("memo", GUESS["memo"]), key=f"m_{f.name}")
        camt = c4.selectbox("금액", opts, index=idx("amount", GUESS["amount"]), key=f"amt_{f.name}")
        st.dataframe(df.head(5), use_container_width=True, height=180)

        # H3: 현재 매핑을 양식 시그니처로 저장 (컬럼명 메타데이터만 — 데이터 저장 안 함)
        if st.button("💾 이 컬럼 매핑 저장/갱신", key=f"save_{f.name}",
                     help="같은 양식(동일 헤더 구성) 파일을 다음에 올리면 매핑이 자동 적용됩니다."):
            try:
                save_profile(sig, {
                    "header_row": int(hrow), "vendor": cv, "account": ca,
                    "memo": cm, "amount": camt, "headers": cols, "label": kind,
                })
                st.success(f"매핑을 저장했습니다. 같은 양식 파일은 자동 적용됩니다. (저장 위치: {profile_path()})")
            except Exception as e:
                st.error(f"매핑 저장 실패: {e}")

        for _, r in df.iterrows():
            def g(col):
                return str(r[col]) if col != "(없음)" and col in df.columns else ""
            amt = g(camt).replace(",", "").strip()
            try:
                amt = float(amt) if amt else 0.0
            except ValueError:
                amt = 0.0
            records.append({
                "row_no": row_counter, "source": f.name, "kind": kind,
                "date": "", "slip_no": "",
                "account": g(ca).strip(), "vendor": g(cv).strip(),
                "memo": g(cm).strip(), "amount": amt,
                "raw": r.to_dict(),               # 원본 행 그대로 보존
                "raw_cols": cols,                  # 원본 컬럼 순서
            })
            row_counter += 1

# ── 2-b) 전기 조회처 입력 ──
st.markdown("### 3️⃣ 전기 발송 조회처 입력 (선택)")
st.caption("전기에 발송한 조회처는 일단 포함 가정합니다. 기관명만 입력하면 명칭이 조금 달라도(KEB하나은행=하나은행 등) 자동 분류·병합됩니다.")
pc1, pc2 = st.columns([3, 2])
with pc1:
    prior_text = st.text_area("전기 조회처 (한 줄에 기관 하나)", height=120,
                              placeholder="신한은행\nKEB하나은행\nNH농협은행\n삼성생명")
with pc2:
    prior_file = st.file_uploader("또는 전기 조회처 엑셀", type=["xlsx", "xls"], key="prior_xl")
    prior_col = None
    prior_df = None
    if prior_file:
        prior_df = read_excel_safe(prior_file, 0)
        if prior_df is not None and not prior_df.empty:
            prior_col = st.selectbox("기관명 컬럼", list(prior_df.columns), key="prior_col")

prior_names = [x.strip() for x in prior_text.splitlines() if x.strip()]
if prior_df is not None and prior_col:
    prior_names += [str(x).strip() for x in prior_df[prior_col].tolist() if str(x).strip()]

scan_memo = st.checkbox("적요(메모) 필드에서도 기관명 탐지 (사채 주관사 등 / 오탐 증가 가능)", value=False)

# ── 4) 탐지 ──
if st.button("🔎 금융기관 탐지 실행", type="primary"):
    if not records:
        st.warning("읽힌 데이터가 없습니다. 컬럼 매핑을 확인해주세요.")
        st.stop()
    if scan_memo:
        for rec in records:
            if not rec["vendor"] and rec["memo"] and D._match_dict(rec["memo"]):
                rec["vendor"] = rec["memo"]
    hits = D.scan(records)
    cands = D.aggregate(hits)
    cands, added = D.merge_prior(cands, prior_names)
    hit_rows = {h["row_no"] for h in hits}
    unmatched = [r for r in records if r["row_no"] not in hit_rows]
    st.session_state["result"] = (cands, hits, unmatched, added)

# ── 5) 결과 ──
if "result" in st.session_state:
    cands, hits, unmatched, added = st.session_state["result"]
    cands_sorted = sort_candidates(cands)

    n_online = sum(1 for c in cands if c["조회방법"] == "온라인 조회")
    n_review = len(cands) - n_online
    n_prior = sum(1 for c in cands if "전기" in c.get("포함근거", "") and c["발견건수"] == 0)
    m = st.columns(5)
    m[0].metric("조회 대상", f"{len(cands)}개")
    m[1].metric("온라인 가능", f"{n_online}개")
    m[2].metric("서면/확인필요", f"{n_review}개")
    m[3].metric("전기보유분", f"{n_prior}개")
    m[4].metric("미매칭 안전망", f"{len(unmatched)}건")

    st.markdown("### 📋 조회 대상 명세")
    st.caption("🟡 '서면 조회(확인필요)' 행은 온라인 미참가/유형 미확정/전기보유분입니다. 아래 검토 패널에서 원천 자료를 확인하세요.")
    rows = []
    for i, c in enumerate(cands_sorted, 1):
        online = c["조회방법"] == "온라인 조회"
        rows.append({
            "조회서번호": f"BC{i}",
            "금융기관": c.get("온라인정식명") or c["기관(정규화)"],
            "조회(*1)": c["조회방법"],
            "전화번호": "" if online else c.get("전화번호", ""),
            "회신/스캔(*2)": "원본",
            "조회서 양식": c["조회서양식"],
            "포함근거": c.get("포함근거", "당기 탐지"),
            "발견건수": c["발견건수"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                 height=min(560, 80 + 36 * len(rows)))

    # ── 서면/확인필요 검토 패널 (원천 자료 원본 표시) ──
    review_list = [c for c in cands_sorted
                   if c["조회방법"].startswith("서면") or c["조회서양식"].endswith("(검토필요)")]
    st.markdown("### 🔍 서면/확인필요 기관 검토")
    if not review_list:
        st.success("확인이 필요한 기관이 없습니다. 모두 온라인 조회 가능 기관으로 분류되었습니다.")
    else:
        st.caption(f"{len(review_list)}개 기관이 담당자 검토 대상입니다. 기관을 선택하면 어느 자료에서 왔는지와 원본 내역을 그대로 보여줍니다.")
        labels = [f"{c.get('온라인정식명') or c['기관(정규화)']}  ·  {c['조회서양식']}  ·  {c.get('포함근거','')}"
                  for c in review_list]
        sel = st.selectbox("검토할 기관 선택", range(len(review_list)),
                           format_func=lambda i: labels[i])
        chosen = review_list[sel]
        st.markdown(f"**{chosen.get('온라인정식명') or chosen['기관(정규화)']}** · {chosen['조회서양식']} · {chosen.get('포함근거','')}")
        chits = chosen.get("_hits", [])
        if not chits:
            st.info("당기 분개장·명세서에서 발견되지 않은 전기 조회처입니다. 당기 거래 종료 여부를 확인하세요.")
        else:
            by_src = {}
            for h in chits:
                by_src.setdefault(h["source"], []).append(h)
            for src, hs in by_src.items():
                st.markdown(f"📄 **{src}**  ({hs[0].get('kind','')}) — {len(hs)}건")
                raw_cols = hs[0].get("raw_cols", [])
                raw_rows = [h["raw"] for h in hs]
                df_raw = pd.DataFrame(raw_rows)
                if raw_cols:
                    df_raw = df_raw[[c for c in raw_cols if c in df_raw.columns]]
                st.dataframe(df_raw, use_container_width=True, hide_index=True)

    with st.expander("🔎 전체 검토 근거 & 미매칭 안전망"):
        tr = [{"기관": h["norm_vendor"], "출처": h["source"], "원천행": h["row_no"],
               "계정과목": h["account"], "거래처명": h.get("vendor") or "(공란)",
               "적요": h["memo"], "금액": h["amount"]}
              for h in sorted(hits, key=lambda x: x["norm_vendor"])]
        st.dataframe(pd.DataFrame(tr), use_container_width=True, hide_index=True)
        if unmatched:
            st.markdown("**미매칭 잔여 (안전망, 금액 큰 순) — 비정형 명칭의 금융기관이 숨었을 수 있음**")
            um = [{"출처": u["source"], "원천행": u["row_no"], "계정과목": u["account"],
                   "거래처명": u.get("vendor") or "(공란)", "적요": u["memo"], "금액": u["amount"]}
                  for u in sorted(unmatched, key=lambda x: -float(x["amount"]))]
            st.dataframe(pd.DataFrame(um), use_container_width=True, hide_index=True)

    # ── 다운로드 ──
    st.markdown("### 📥 산출물 다운로드")
    wb = build_workbook(cands, hits, unmatched)
    buf = io.BytesIO(); wb.save(buf)
    st.download_button("조회 대상 명세 (Excel) 다운로드", buf.getvalue(),
                       file_name="조회대상_금융기관_명세.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       type="primary")

sidebar()
