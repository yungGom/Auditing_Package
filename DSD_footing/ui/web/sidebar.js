// sidebar.js — U-2 좌측 목록 + U-3 목록 클릭→페이지 점프. marks[]만 읽는다
// (annotations[] 제외). 좌표 매칭·하이라이트는 U-4, 상세 패널은 U-5.
//
// 카운터 규칙(CLAUDE.md 결정 16):
//   전체 건수(diff/unverified/ok/recon 등)는 document.counts에서 읽는다 — 다시 세지 않는다.
//   진행 상태(미검토/검토완료 등 status 기반)는 marks[]를 그 자리에서 센다 —
//   status는 런타임에 바뀌는 값이라 분석 산출물(document.counts)에 없다.
//
// viewer.js와는 bus.js(이벤트 버스)로만 연결한다 — 직접 import 안 함(설계안_UI셸_U3.md
// §1). U-4의 역방향(지면 클릭→목록 선택)도 같은 버스에 "selectMark"를 태우면 된다.
import { on, emit } from "./bus.js";

const el = {
  counters: {
    diff: document.getElementById("cDiff"),
    unverified: document.getElementById("cUnverified"),
    recon: document.getElementById("cRecon"),
  },
  tabs: document.querySelectorAll("#filterTabs .tab"),
  list: document.getElementById("markList"),
  tableLabel: document.getElementById("tableLabel"),
};

let MARKS = []; // marks[] 원본(annotations 제외) — counterparts 등 전 필드 보존
let filter = "diff";
let selectedId = null;

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
  applySelectionDom(); // innerHTML 교체로 클래스가 날아가므로 매번 다시 입힌다
}

function applySelectionDom() {
  el.list.querySelectorAll(".row").forEach((r) => {
    r.classList.toggle("selected", r.dataset.markId === selectedId);
  });
}

function markById(id) {
  return MARKS.find((m) => m.id === id) || null;
}

/** 행 클릭·J/K·N이 전부 거치는 단일 경로 — 표시·스크롤·버스 emit이 한 곳에만 있다
 * (설계안 §3, "행 클릭과 키보드가 같은 내부 함수를 공유"). */
function selectMark(mark, { switchToDiffTab = false } = {}) {
  if (!mark) return;
  if (switchToDiffTab && filter !== "diff") {
    filter = "diff";
    el.tabs.forEach((b) => b.classList.toggle("active", b.dataset.filter === "diff"));
    renderList();
  }
  selectedId = mark.id;
  applySelectionDom();
  el.tableLabel.textContent = mark.table_label || "표 이름 미확인";
  const row = el.list.querySelector(`.row[data-mark-id="${mark.id}"]`);
  if (row) row.scrollIntoView({ block: "nearest" });
  emit("jumpToPage", mark.page);
}

function clearSelection() {
  selectedId = null;
  applySelectionDom();
  el.tableLabel.textContent = "";
}

el.list.addEventListener("click", (ev) => {
  const row = ev.target.closest(".row");
  if (!row) return;
  selectMark(markById(row.dataset.markId));
});

el.tabs.forEach((btn) => {
  btn.addEventListener("click", () => {
    filter = btn.dataset.filter;
    el.tabs.forEach((b) => b.classList.toggle("active", b === btn));
    renderList();
  });
});

// viewer.js가 페이지를 렌더할 때마다(이동 수단 무관) 낸다. 선택된 마크의 페이지와
// 달라지면(=목록 클릭이 아니라 이전/다음·직접 입력으로 옮겨간 것) 선택을 지운다 —
// 옛 선택이 남아있으면 회계사가 엉뚱한 표를 대사하게 된다(설계안 §2).
on("pageChanged", (page) => {
  const sel = markById(selectedId);
  if (sel && sel.page !== page) clearSelection();
});

// ── 키보드: J/K(현재 필터에 보이는 목록 안에서 위/아래, 경계 정지) / N(미검토
// 차이만 순회, 순환) ────────────────────────────────────────────────
function isTypingTarget(t) {
  return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
}

document.addEventListener("keydown", (ev) => {
  if (isTypingTarget(document.activeElement)) return;
  const key = ev.key.toLowerCase();
  if (key === "j" || key === "k") {
    ev.preventDefault();
    const rows = visibleMarks();
    if (!rows.length) return;
    let idx = rows.findIndex((m) => m.id === selectedId);
    idx = idx < 0 ? 0 : Math.max(0, Math.min(rows.length - 1, idx + (key === "j" ? 1 : -1)));
    selectMark(rows[idx]);
  } else if (key === "n") {
    ev.preventDefault();
    const pending = MARKS.filter((m) => m.type === "diff" && m.status === "pending")
      .sort((a, b) => a.page - b.page);
    if (!pending.length) return;
    let idx = pending.findIndex((m) => m.id === selectedId);
    idx = (idx + 1) % pending.length; // idx=-1(미선택)이면 0번으로 시작
    selectMark(pending[idx], { switchToDiffTab: true });
  }
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
