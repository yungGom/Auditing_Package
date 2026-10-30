// detail.js — 우측 상세 패널(U-5). marks.json 필드를 화면에 매핑하고, 판단 버튼
// 클릭은 "judge" 이벤트로만 낸다 — mark 객체를 여기서 직접 바꾸지 않는다.
// 데이터(MARKS 배열)의 유일한 소유자는 sidebar.js다(선택 상태 소유와 같은 이유 —
// 카운터·목록 재계산·자동 이동이 전부 그쪽에 있어 소유자를 나누면 불일치가 난다).
//
// 버스 계약 추가분(U-5, 설계안_UI셸_U5.md §2·§5·§8):
//   judge             detail → sidebar   판단 확정 {markId, decision, comment}
//   reviewComplete    sidebar → detail   자동 이동 대상(미검토 차이) 소진
//   highlightOperands detail → viewer    산식 클릭 시 성분 좌표 배열(또는 [] = 해제)
import { on, emit } from "./bus.js";

const el = {
  empty: document.getElementById("detailEmpty"),
  body: document.getElementById("detailBody"),
  complete: document.getElementById("detailComplete"),
  account: document.getElementById("dAccount"),
  meta: document.getElementById("dMeta"),
  vShown: document.getElementById("vShown"),
  vComputedRow: document.getElementById("vComputedRow"),
  vComputed: document.getElementById("vComputed"),
  vDelta: document.getElementById("vDelta"),
  vFormula: document.getElementById("vFormula"),
  accCounterparts: document.getElementById("accCounterparts"),
  cpCount: document.getElementById("cpCount"),
  cpBody: document.getElementById("cpBody"),
  srcBody: document.getElementById("srcBody"),
  histBody: document.getElementById("histBody"),
  memo: document.getElementById("judgeMemo"),
  btnConfirm: document.getElementById("btnConfirm"),
  btnReject: document.getElementById("btnReject"),
  judgedNote: document.getElementById("judgedNote"),
};

let currentMark = null;
let opShown = false;      // 산식 클릭 토글 — 마크가 바뀌면 초기화
let completeMode = false; // reviewComplete 이후, 사용자가 다시 뭔가 고르기 전까지 유지

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/** 절대값 문자열 — sign_flipped 카운터파트는 부호가 반대라는 걸 이미 배지로
 * 알리므로, 문자 강조는 부호를 빼고 자리수만 비교한다(설계안 §3, 부호는 UI가
 * 미리 뒤집어 보여주지 않는다). */
function absAmount(s) {
  if (s == null) return "";
  return String(s).replace(/^\(/, "").replace(/\)$/, "").replace(/^-/, "");
}

/** 우측 정렬 후 자리별 비교 — 다른 자리만 <span class="ch-diff">로 감싼다.
 * 공백 패딩은 &nbsp;로(일반 공백은 HTML이 접어 정렬이 깨진다). */
function charDiffPair(a, b) {
  const sa = a == null ? "" : String(a);
  const sb = b == null ? "" : String(b);
  const len = Math.max(sa.length, sb.length);
  const pa = sa.padStart(len, " ");
  const pb = sb.padStart(len, " ");
  const wrap = (c) => (c === " " ? "&nbsp;" : escapeHtml(c));
  let ha = "", hb = "";
  for (let i = 0; i < len; i++) {
    const same = pa[i] === pb[i];
    const ca = wrap(pa[i]), cb = wrap(pb[i]);
    ha += same ? ca : `<span class="ch-diff">${ca}</span>`;
    hb += same ? cb : `<span class="ch-diff">${cb}</span>`;
  }
  return { a: ha, b: hb };
}

function showEmpty() { el.empty.hidden = false; el.body.hidden = true; el.complete.hidden = true; }
function showComplete() { el.empty.hidden = true; el.body.hidden = true; el.complete.hidden = false; }
function showBody() { el.empty.hidden = true; el.body.hidden = false; el.complete.hidden = true; }

const JUDGE_LABELS = {
  diff: { confirm: "이상없음", reject: "차이 아님" },
  unverified: { confirm: "확인함", reject: "해당없음" },
};

function renderVerify(m) {
  if (m.computed_value != null) {
    const d = charDiffPair(m.shown_value, m.computed_value);
    el.vShown.innerHTML = d.a;
    el.vComputed.innerHTML = d.b;
    el.vComputedRow.hidden = false;
  } else {
    // unverified/L2 — 비교 대상 자체가 없다(unverified는 계산 불가, L2는
    // counterparts 아코디언에서 각 상대와 개별 비교한다).
    el.vShown.textContent = m.shown_value ?? "-";
    el.vComputedRow.hidden = true;
  }
  el.vDelta.textContent = m.delta || "-";
  el.vFormula.textContent = m.formula || "-";
  const clickable = Array.isArray(m.operands) && m.operands.length > 0;
  el.vFormula.classList.toggle("clickable", clickable);
  el.vFormula.title = clickable ? "클릭하면 성분이 지면에서 강조됩니다" : "";
}

function renderCounterparts(m) {
  const cps = m.counterparts || [];
  if (!cps.length) {
    el.accCounterparts.hidden = true; // 아코디언 자체를 그리지 않는다(설계안 §0-a, 8/18건 실측)
    return;
  }
  el.accCounterparts.hidden = false;
  el.cpCount.textContent = `${cps.length}건`;
  el.cpBody.innerHTML = cps.map((cp) => {
    const base = cp.sign_flipped ? absAmount(m.shown_value) : m.shown_value;
    const other = cp.sign_flipped ? absAmount(cp.amount) : cp.amount;
    const d = charDiffPair(base, other);
    const flag = cp.sign_flipped ? `<div class="cp-flag">부호 반전 적용됨</div>` : "";
    return `<div class="cp-row">
      <div class="cp-head">
        <span class="cp-tag">${escapeHtml(cp.tag || "")}</span>
        <span class="cp-page">${cp.page ?? "-"}면</span>
      </div>
      <div class="cp-label">${escapeHtml(cp.label || "")}</div>
      <div class="cp-amt">${d.b}</div>
      ${flag}
    </div>`;
  }).join("");
  // 기본 펼침: level=="L2"(설계안 §4). 마크 전환 때마다 다시 정해야 이전 마크의
  // 접힘/펼침 상태가 새지 않는다.
  el.accCounterparts.querySelector(".acc-body").hidden = m.level !== "L2";
}

function renderSource(m) {
  const s = m.source || {};
  el.srcBody.innerHTML = `
    <div class="kv"><span>면</span><b>${m.page}면</b></div>
    <div class="kv"><span>표</span><b>${s.table ?? "-"}</b></div>
    <div class="kv"><span>계정과목</span><b>${escapeHtml(m.account || "-")}</b></div>
    <div class="kv"><span>조서번호</span><b>${escapeHtml(m.paper_no || "미배정")}</b></div>
  `;
}

function renderHistory(m) {
  const reviewed = m.reviewed_at ? `(${escapeHtml(m.reviewed_at)})` : "(미확정)";
  el.histBody.innerHTML = `
    <div class="kv"><span>도구 검증</span><b>${escapeHtml(m.verified_at || "-")}</b></div>
    <div class="kv"><span>회계사 검토</span><b>${escapeHtml(m.reviewed_by || "—")} ${reviewed}</b></div>
    <div class="kv"><span>메모</span><b>${escapeHtml(m.comment || m.note || "없음")}</b></div>
  `;
}

function renderJudge(m) {
  const labels = JUDGE_LABELS[m.type] || JUDGE_LABELS.diff;
  el.btnConfirm.textContent = labels.confirm;
  el.btnReject.textContent = labels.reject;
  el.memo.value = m.comment || "";
  if (m.status === "pending") {
    el.judgedNote.hidden = true;
  } else {
    el.judgedNote.hidden = false;
    el.judgedNote.textContent = `이미 판단됨 → ${m.status === "approved" ? labels.confirm : labels.reject}`;
  }
}

function render(mark) {
  currentMark = mark;
  opShown = false;
  completeMode = false;
  showBody();
  el.account.textContent = mark.account || "";
  el.meta.textContent = `${mark.page}면 · ${mark.table_label || "표 이름 미확인"}`;
  renderVerify(mark);
  renderCounterparts(mark);
  renderSource(mark);
  renderHistory(mark);
  renderJudge(mark);
  emit("highlightOperands", []); // 마크가 바뀌면 이전 성분 강조부터 지운다
}

el.vFormula.addEventListener("click", () => {
  if (!currentMark || !Array.isArray(currentMark.operands) || !currentMark.operands.length) return;
  opShown = !opShown;
  emit("highlightOperands", opShown ? currentMark.operands : []);
});

// 아코디언 펼침/접힘 — 대사 대상 기본 펼침이라도 회계사가 접을 수 있어야 한다
// (강제 펼침 아님). 출처·검토이력은 항상 클릭으로 토글.
document.querySelectorAll(".acc-head").forEach((btn) => {
  btn.addEventListener("click", () => {
    const body = btn.parentElement.querySelector(".acc-body");
    body.hidden = !body.hidden;
  });
});

function judge(decision) {
  if (!currentMark) return;
  emit("judge", { markId: currentMark.id, decision, comment: el.memo.value.trim() || null });
}
el.btnConfirm.addEventListener("click", () => judge("confirm"));
el.btnReject.addEventListener("click", () => judge("reject"));

on("selectionChanged", (mark) => {
  if (mark) { render(mark); return; }
  emit("highlightOperands", []);
  if (!completeMode) showEmpty();
});

on("reviewComplete", () => {
  completeMode = true;
  showComplete();
});
