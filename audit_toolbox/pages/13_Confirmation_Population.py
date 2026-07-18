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


REVIEW_GROUPS = []  # 검토 드릴다운 그룹 (gkey, review_rows) — 매 실행마다 재구성


def mapping_widget(df, cols, *, key_prefix, kind, show_account=True, hrow=0):
    """거래처(복수)/계정/적요/금액 매핑 UI 렌더 → (cv_list, ca, cm, camt) 반환.
       분개장(단일시트)·명세서(시트별) 공용. (PATCH 6/9)"""
    opts = ["(없음)"] + cols
    prof, psource, sig = match_mapping(cols)
    if psource == "user":
        st.success("📌 저장된 매핑 자동 적용 — 확인만 하세요.")
    elif psource == "preset":
        st.info(f"🧩 ERP 프리셋 추정: {prof.get('label', '')}")
    auto = resolve_mapping(cols, df.to_dict("list"))

    def idx(field):
        if prof and prof.get(field) in opts:
            return opts.index(prof[field])
        if auto.get(field) in opts:
            return opts.index(auto[field])
        return 0

    def vdef():
        if prof:
            vc = prof.get("vendor_cols")
            if isinstance(vc, list):
                sel = [c for c in vc if c in cols]
                if sel:
                    return sel
            if prof.get("vendor") in cols:
                return [prof["vendor"]]
        cand = [c for c in cols if any(k in str(c)
                for k in ("관리항목", "거래처", "상대처", "거래상대"))]
        if auto.get("vendor") in cols and auto["vendor"] not in cand:
            cand.insert(0, auto["vendor"])
        return cand

    if show_account:
        c1, c2, c3, c4 = st.columns(4)
    else:
        c1, c3, c4 = st.columns(3)
        c2 = None
    cv_list = c1.multiselect("거래처명 후보 컬럼 * (여러 개 가능)", cols, default=vdef(),
                             key=f"v_{key_prefix}",
                             help="관리항목 등 거래처가 여러 컬럼에 흩어져 있으면 모두 선택하세요.")
    if show_account and c2 is not None:
        ca = c2.selectbox("계정과목", opts, index=idx("account"), key=f"a_{key_prefix}")
    else:
        ca = "(없음)"
    cm = c3.selectbox("적요", opts, index=idx("memo"), key=f"m_{key_prefix}")
    camt = c4.selectbox("금액", opts, index=idx("amount"), key=f"amt_{key_prefix}")
    st.dataframe(df.head(5), use_container_width=True, height=160)
    if st.button("💾 이 컬럼 매핑 저장/갱신", key=f"save_{key_prefix}",
                 help="같은 양식(동일 헤더 구성) 파일을 다음에 올리면 매핑이 자동 적용됩니다."):
        try:
            save_profile(sig, {
                "header_row": int(hrow),
                "vendor": (cv_list[0] if cv_list else "(없음)"),
                "vendor_cols": list(cv_list),
                "account": ca, "memo": cm, "amount": camt,
                "headers": cols, "label": kind,
            })
            st.success(f"매핑을 저장했습니다. (저장 위치: {profile_path()})")
        except Exception as e:
            st.error(f"매핑 저장 실패: {e}")
    return cv_list, ca, cm, camt


def build_records_from_df(df, cols, cv_list, ca, cm, camt, *, source, kind, sheet, account_hint):
    """선택 매핑으로 행 records 생성 (row_no는 이후 일괄 부여). account 없으면 시트힌트."""
    recs = []
    for _, r in df.iterrows():
        def g(col):
            return str(r[col]) if col != "(없음)" and col in df.columns else ""
        amt = g(camt).replace(",", "").strip()
        try:
            amt = float(amt) if amt else 0.0
        except ValueError:
            amt = 0.0
        vendor_candidates = [g(c).strip() for c in cv_list]
        vendor_rep = next((x for x in vendor_candidates if x), "")
        account = g(ca).strip() if (ca and ca != "(없음)") else (account_hint or "")
        recs.append({
            "row_no": None, "source": source, "kind": kind, "sheet": sheet,
            "date": "", "slip_no": "",
            "account": account,
            "vendor": vendor_rep,
            "vendor_candidates": vendor_candidates,
            "vendor_cand_cols": list(cv_list),
            "memo": g(cm).strip(), "amount": amt,
            "raw": r.to_dict(), "raw_cols": cols,
        })
    return recs


def render_drilldown(gkey, rows):
    """검토 드릴다운: 행 단위 포함 체크 + 전체 포함/제외 일괄동작 (PATCH 8/9 공용)."""
    REVIEW_GROUPS.append((gkey, rows))
    mapkey = f"incmap::{gkey}"
    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("전체 포함", key=f"incall::{gkey}"):
        st.session_state[mapkey] = {rr["row_no"]: True for rr in rows}
        st.session_state.pop(f"ed::{gkey}", None)
        st.rerun()
    if b2.button("전체 제외", key=f"excall::{gkey}"):
        st.session_state[mapkey] = {rr["row_no"]: False for rr in rows}
        st.session_state.pop(f"ed::{gkey}", None)
        st.rerun()
    cur = st.session_state.get(mapkey, {rr["row_no"]: rr["auto_include"] for rr in rows})
    data = [{
        "포함": bool(cur.get(rr["row_no"], rr["auto_include"])),
        "검토": ("🟡 적요확인필요" if rr["tag"] == "적요확인필요"
               else ("✅ 자동추천" if rr["auto_include"] else "—")),
        "일자": rr["date"], "거래처": rr["vendor_display"],
        "적요": rr["memo"], "금액": rr["amount"], "row_no": rr["row_no"],
    } for rr in rows]
    edited = st.data_editor(
        pd.DataFrame(data), key=f"ed::{gkey}", hide_index=True, use_container_width=True,
        column_config={
            "포함": st.column_config.CheckboxColumn("포함", default=False),
            "금액": st.column_config.NumberColumn("금액", format="%d"),
            "row_no": None,
        },
        disabled=["검토", "일자", "거래처", "적요", "금액"])
    st.session_state[mapkey] = {int(r["row_no"]): bool(r["포함"]) for _, r in edited.iterrows()}
    st.caption("🟡 = 거래처 공란/비금융인데 적요에 단서가 있는 행 — 적요를 읽고 직접 포함을 결정하세요.")


def handle_multisheet(f, raw_bytes, sheet_names, records):
    """PATCH 9: 통합문서(멀티시트) 명세서 — 시트 인벤토리 + 시트별 매핑 → records 추가."""
    st.markdown(f"#### 📑 {f.name} — 통합문서 {len(sheet_names)}개 시트")
    inv = []
    for sh in sheet_names:
        try:
            probe = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=sh, header=None,
                                  nrows=21, dtype=str).fillna("")
            hr = detect_header_row(probe.values.tolist())
            dfx = pd.read_excel(io.BytesIO(raw_bytes), sheet_name=sh, header=hr,
                                dtype=str).fillna("")
        except Exception:
            dfx, hr = None, 0
        gs = D.guess_sheet(sh)
        cols = list(dfx.columns) if dfx is not None else []
        autom = resolve_mapping(cols, dfx.to_dict("list")) if cols else {}
        has_vendor = bool([c for c in cols if any(k in str(c)
                          for k in ("관리항목", "거래처", "상대처", "거래상대"))]
                          or autom.get("vendor"))
        inv.append({"sheet": sh, "account": gs["account"], "is_fi": gs["is_fi"],
                    "nrows": (0 if dfx is None else len(dfx)), "hr": hr,
                    "cols": cols, "df": dfx, "has_vendor": has_vendor})
    st.dataframe(pd.DataFrame([{
        "검토대상(기본)": ("✅" if x["is_fi"] else "—"), "시트": x["sheet"],
        "추정계정": x["account"] or "-", "행수": x["nrows"], "헤더행": x["hr"],
        "거래처컬럼": ("있음" if x["has_vendor"] else "없음(적요만)")} for x in inv]),
        use_container_width=True, hide_index=True)
    for x in inv:
        sh = x["sheet"]
        chk = st.checkbox(f"[{sh}] 검토 대상에 포함", value=x["is_fi"],
                          key=f"sheetchk_{f.name}_{sh}")
        if not chk or x["df"] is None or x["df"].empty:
            continue
        if not x["has_vendor"]:
            st.warning(f"[{sh}] 거래처 컬럼이 안 보입니다 — 적요만으로 검토합니다(적요 확인 필요).")
        with st.expander(f"🗂️ [{sh}] 컬럼 매핑 (추정계정: {x['account'] or '-'})", expanded=False):
            cv_list, ca, cm, camt = mapping_widget(
                x["df"], x["cols"], key_prefix=f"{f.name}_{sh}",
                kind="명세서", show_account=False, hrow=x["hr"])
        records.extend(build_records_from_df(
            x["df"], x["cols"], cv_list, ca, cm, camt,
            source=f"{f.name} ▸ {sh}", kind="명세서", sheet=sh, account_hint=x["account"]))


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
        st.markdown("### 🗂️ 사전 외부 파일")
        src = "외부 엑셀 사용 중" if (D.EXTERNAL_DICT_LOADED or D.EXTERNAL_ONLINE_LOADED) else "내장 기본값"
        st.caption(f"현재 출처: {src}")
        st.caption(f"엑셀을 이 폴더에 두면 코드 수정 없이 갱신됩니다:\n`{D._BASE_DIR}`")
        st.caption(f"파일명: {D.DICT_XLSX_NAME} · {D.ONLINE_XLSX_NAME}")
        if st.button("현재 사전 → 엑셀 템플릿 내보내기", key="export_dicts"):
            try:
                dp, op = D.export_templates(D._BASE_DIR)
                D.reload_external()
                st.success("내보냈습니다. 엑셀을 수정한 뒤 페이지를 새로고침하면 반영됩니다.")
                st.caption(f"{os.path.basename(dp)} / {os.path.basename(op)}")
            except Exception as e:
                st.error(f"내보내기 실패: {e}")

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
for f in files:
    raw_bytes = f.getvalue()
    try:
        sheet_names = pd.ExcelFile(io.BytesIO(raw_bytes)).sheet_names
    except Exception as e:
        st.error(f"{f.name} 읽기 오류: {e}")
        continue

    if len(sheet_names) > 1:
        # PATCH 9: 통합문서(멀티시트) → 시트 인벤토리 + 시트별 매핑 + 시트별 검토
        handle_multisheet(f, raw_bytes, sheet_names, records)
        continue

    # 단일 시트: 분개장 / 단일 명세서
    kind = guess_kind(f.name)
    only_sheet = sheet_names[0] if sheet_names else ""
    with st.expander(f"📄 {f.name}  ·  추정: {kind}", expanded=True):
        # H1: 상단을 스캔해 헤더 행을 자동 추정 → number_input 기본값
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
        cv_list, ca, cm, camt = mapping_widget(df, cols, key_prefix=f.name,
                                               kind=kind, show_account=True, hrow=hrow)
        records.extend(build_records_from_df(
            df, cols, cv_list, ca, cm, camt,
            source=f.name, kind=kind, sheet=only_sheet, account_hint=""))

# 검토 준비: row_no 일괄 부여(파일·시트 통합 유니크) + 그룹 초기화 + 분류
for i, rec in enumerate(records, 1):
    rec["row_no"] = i
REVIEW_GROUPS.clear()
journal_records = [r for r in records if r.get("kind") == "분개장"]
statement_records = [r for r in records if r.get("kind") == "명세서"]
other_records = [r for r in records if r.get("kind") not in ("분개장", "명세서")]

# ── 3) 분개장 검토 (계정 슬라이서 → 드릴다운 → 일괄동작) ──
st.markdown("### 3️⃣ 분개장 검토 — 관련 계정 선택 후 거래 확인")
if not journal_records:
    st.caption("분개장으로 인식된 파일이 없습니다. (명세서만 올린 경우 이 단계는 건너뜁니다)")
else:
    summary = D.account_summary(journal_records)
    all_accts = [s["account"] for s in summary]
    fi_default = [s["account"] for s in summary if s["is_fi"]]
    cnt = {s["account"]: s["count"] for s in summary}
    st.caption("자동 탐지는 1차 추천(체크 기본값)일 뿐입니다. 계정을 좁힌 뒤 거래처·적요를 직접 확인해 포함을 확정하세요.")
    sel_accounts = st.multiselect(
        "검토할 계정과목 (🏦 금융 관련 계정은 기본 선택)",
        all_accts, default=fi_default, key="rev_accounts",
        format_func=lambda a: f"{'🏦 ' if a in D.FI_ACCOUNT_FLAT else ''}{a} ({cnt.get(a, 0)}건)")
    jrev = D.review_journal(journal_records, selected_accounts=set(sel_accounts))
    for acct in sel_accounts:
        rows = [rr for rr in jrev if rr["account"] == acct]
        if not rows:
            continue
        n_auto = sum(1 for rr in rows if rr["auto_include"])
        n_chk = sum(1 for rr in rows if rr["tag"] == "적요확인필요")
        head = f"{'🏦 ' if acct in D.FI_ACCOUNT_FLAT else ''}{acct} — {len(rows)}건"
        with st.expander(f"📂 {head}  ·  자동추천 {n_auto} · 적요확인 {n_chk}", expanded=False):
            render_drilldown(f"acct::{acct}", rows)

# ── 3-b) 명세서 시트 검토 (시트 슬라이서 → 드릴다운) ──
st.markdown("### 📑 명세서 시트 검토")
if not statement_records:
    st.caption("명세서로 인식된 시트가 없습니다. (멀티시트 명세서를 올리면 시트별로 검토합니다)")
else:
    srcs = []
    for r in statement_records:
        if r["source"] not in srcs:
            srcs.append(r["source"])
    for src in srcs:
        rrec = [r for r in statement_records if r["source"] == src]
        rev = D.review_journal(rrec)
        n_auto = sum(1 for rr in rev if rr["auto_include"])
        n_chk = sum(1 for rr in rev if rr["tag"] == "적요확인필요")
        with st.expander(f"📑 {src} — {len(rev)}건  ·  자동추천 {n_auto} · 적요확인 {n_chk}",
                         expanded=False):
            render_drilldown(f"src::{src}", rev)

# ── 4) 전기 조회처 입력 ──
st.markdown("### 4️⃣ 전기 발송 조회처 입력 (선택)")
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

# ── 5) 탐지 ──
if st.button("🔎 금융기관 탐지 실행", type="primary"):
    if not records:
        st.warning("읽힌 데이터가 없습니다. 컬럼 매핑을 확인해주세요.")
        st.stop()
    # 검토 단계에서 포함 확정된 행(분개장 계정 + 명세서 시트)만 후보화 — 사람이 최종 판단
    include_map = {}
    review_all = []
    for gkey, rows in REVIEW_GROUPS:
        m = st.session_state.get(f"incmap::{gkey}",
                                 {rr["row_no"]: rr["auto_include"] for rr in rows})
        include_map.update(m)
        review_all.extend(rows)
    jhits = D.hits_from_included(review_all, include_map=include_map)
    # 검토 대상이 아닌 기타 자료: 기존 자동 탐지
    if scan_memo:
        for rec in other_records:
            if not rec.get("vendor") and rec.get("memo") and D._match_dict(rec["memo"]):
                rec["vendor"] = rec["memo"]
    ohits = D.scan(other_records)
    hits = jhits + ohits
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
               "매칭컬럼": h.get("vendor_col") or "-",
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
