// sidebar.js — U-2 좌측 목록. marks[]만 읽는다(annotations[] 제외).
// 지면 연동(클릭→점프)은 U-3, 좌표 매칭은 U-4, 상세 패널은 U-5 — 여기선 하지 않는다.
//
// 카운터 규칙(CLAUDE.md 결정 16):
//   전체 건수(diff/unverified/ok/recon 등)는 document.counts에서 읽는다 — 다시 세지 않는다.
//   진행 상태(미검토/검토완료 등 status 기반)는 marks[]를 그 자리에서 센다 —
//   status는 런타임에 바뀌는 값이라 분석 산출물(document.counts)에 없다.

const el = {
  counters: {
    diff: document.getElementById("cDiff"),
    unverified: document.getElementById("cUnverified"),
    recon: document.getElementById("cRecon"),
  },
  tabs: document.querySelectorAll("#filterTabs .tab"),
  list: document.getElementById("markList"),
};

let MARKS = []; // marks[] 원본(annotations 제외) — counterparts 등 전 필드 보존
let filter = "diff";

function waitForApi() {
  if (window.pywebview && window.pywebview.api) return Promise.resolve();
  return new Promise((resolve) => {
    window.addEventListener("pywebviewready", () => resolve(), { once: true });
  });
}

function renderCounters(counts) {
  // "전체" = document.counts. "미검토/확인 필요" 등 status 기반은 marks[]를 센다.
  const diffPending = MARKS.filter((m) => m.type === "diff" && m.status === "pending").length;
  el.counters.diff.innerHTML = `차이 <b>${counts.diff}</b>건 중 <b>${diffPending}</b>건 미검토`;
  el.counters.unverified.innerHTML = `확인 필요 <b>${counts.unverified}</b>건`;
  el.counters.recon.innerHTML = `대사 완료 <b>${counts.recon}</b>건 · 검산 완료 <b>${counts.ok}</b>건`;
}

function fmtMeta(m) {
  const page = `${m.page}면`;
  const delta = m.delta ? ` · ${m.delta}` : "";
  return page + delta;
}

function rowHtml(m) {
  return `<div class="row" data-mark-id="${m.id}" data-type="${m.type}"
               data-status="${m.status}" data-l2-class="${m.l2_class || ""}">
    <span class="dot"></span>
    <span class="text">
      <div class="title">${escapeHtml(m.account || "")}</div>
      <div class="meta">${escapeHtml(fmtMeta(m))}</div>
    </span>
  </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function visibleMarks() {
  // 정렬: 차이 그룹 전체 → 확인 필요 그룹 전체, 그룹 내부는 page 오름차순.
  const rank = (m) => (m.type === "diff" ? 0 : 1);
  const sorted = [...MARKS].sort((a, b) => rank(a) - rank(b) || a.page - b.page);
  if (filter === "all") return sorted;
  return sorted.filter((m) => m.type === filter);
}

function renderList() {
  const rows = visibleMarks();
  el.list.innerHTML = rows.length
    ? rows.map(rowHtml).join("")
    : `<div class="empty">해당하는 항목이 없습니다</div>`;
}

el.tabs.forEach((btn) => {
  btn.addEventListener("click", () => {
    filter = btn.dataset.filter;
    el.tabs.forEach((b) => b.classList.toggle("active", b === btn));
    renderList();
  });
});

async function loadMarks() {
  await waitForApi();
  const res = await window.pywebview.api.get_marks();
  if (res.error) {
    el.list.innerHTML = `<div class="empty">목록을 불러올 수 없습니다<br>${escapeHtml(res.error)}</div>`;
    return;
  }
  MARKS = res.marks; // annotations[]는 애초에 여기서 안 받는다(app.py가 marks만 넘김)
  renderCounters(res.counts);
  renderList();
}

loadMarks().catch((e) => {
  el.list.innerHTML = `<div class="empty">목록을 불러올 수 없습니다<br>${escapeHtml(e.message || String(e))}</div>`;
});
