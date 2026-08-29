// sidebar.js — 좌측 목록(U-2) + 목록 클릭→페이지 점프(U-3) + 선택 상태 소유(U-4).
// marks[]만 읽는다(annotations[] 제외). 상세 패널·판단 버튼은 U-5.
//
// 카운터 규칙(CLAUDE.md 결정 16):
//   전체 건수(diff/unverified/ok/recon 등)는 document.counts에서 읽는다 — 다시 세지 않는다.
//   진행 상태(미검토/검토완료 등 status 기반)는 marks[]를 그 자리에서 센다 —
//   status는 런타임에 바뀌는 값이라 분석 산출물(document.counts)에 없다.
//
// viewer.js와는 bus.js로만 연결한다 — 직접 import 안 함.
// 버스 계약(U-4 확정, 설계안_UI셸_U4.md §5) — **선택 상태의 소유자는 이 파일 하나다**:
//   selectMark        viewer → sidebar   "이 마크를 선택해 달라"(요청). 지면 클릭이 낸다
//   selectionChanged  sidebar → viewer   "선택이 이렇게 됐다"(확정). 페이지 이동·링의 근거
//   pageChanged       viewer → sidebar   페이지가 바뀌었다(이동 수단 무관)
// viewer는 selectionChanged를 받아 처리만 하고 되쏘지 않으므로 루프가 없다.
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
let DOCUMENT_COUNTS = null; // document.counts — 판단 후 카운터 재계산에 재사용(U-5)

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
  // status=="removed"(판단: 차이 아님/해당없음)는 목록에서 아예 뺀다 — sidebar.css의
  // 기존 주석("removed: 목록에서 아예 제외") 그대로. 지면에서도 빠지는 것과 같은
  // 이유: 도구가 틀렸다고 확정된 항목을 계속 다시 보여줄 필요가 없다(U-5).
  const rank = (m) => (m.type === "diff" ? 0 : 1);
  const sorted = [...MARKS]
    .filter((m) => m.status !== "removed")
    .sort((a, b) => rank(a) - rank(b) || a.page - b.page);
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
  emit("selectionChanged", mark);   // 페이지 이동·링 갱신의 유일한 근거
}

function clearSelection() {
  selectedId = null;
  applySelectionDom();
  el.tableLabel.textContent = "";
  emit("selectionChanged", null);
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

// 지면 클릭이 낸 요청. 선택 확정은 여기(단일 소유자)에서만 일어난다.
// 지면 클릭으로 선택할 때는 목록 필터를 건드리지 않는다 — 현재 탭에 안 보이는
// 마크를 골랐으면 "모두" 탭으로 넓혀 목록에서도 보이게 한다.
on("selectMark", (markId) => {
  if (markId === null) { if (selectedId) clearSelection(); return; }
  const mark = markById(markId);
  if (!mark) return;
  if (filter !== "all" && mark.type !== filter) {
    filter = "all";
    el.tabs.forEach((b) => b.classList.toggle("active", b.dataset.filter === "all"));
    renderList();
  }
  selectMark(mark);
});

// U-5 — 상세 패널(detail.js)의 판단 확정. 마크 데이터(status/comment)를 바꾸는
// 유일한 곳이다 — detail.js는 절대 mark 객체를 직접 건드리지 않고 이 이벤트만
// 낸다(선택 상태를 sidebar 하나가 소유하는 것과 같은 이유: 카운터·목록·자동 이동이
// 전부 이 파일에 있어 소유자를 나누면 불일치가 난다).
//
// status 매핑(승인 B안, 2026-08-28 확정, 설계안_UI셸_U5.md §5): confirm(이상없음/
// 확인함) -> approved. reject(차이아님/해당없음) -> removed — render.py의 기존
// "status != removed면 그린다" 조건(결정 12)과 그대로 맞물려 새 스키마가 필요
// 없다. 이력은 marks.json에 남고(향후 U-6 저장), 지면·목록에서만 빠진다 — Phase 1
// "도구 마크는 삭제 대신 removed로 바꾼다" 원칙 그대로.
on("judge", ({ markId, decision, comment }) => {
  const mark = markById(markId);
  if (!mark) return;
  mark.status = decision === "confirm" ? "approved" : "removed";
  mark.comment = comment || null;
  if (DOCUMENT_COUNTS) renderCounters(DOCUMENT_COUNTS); // 미검토 수는 즉시 줄어든다(게이트6)
  renderList();
  // 판단 즉시 저장(U-6) — 앱이 죽으면 판단이 날아가는 것이 실무에서 가장 나쁘다.
  // 화면 갱신을 막지 않도록 await하지 않고, 실패만 표면화한다.
  if (window.pywebview && window.pywebview.api && window.pywebview.api.save_judgment) {
    window.pywebview.api.save_judgment(markId, mark.status, mark.comment)
      .then((r) => { if (r && r.error) emit("saveError", r.error); })
      .catch((e) => emit("saveError", String(e && e.message || e)));
  }
  advanceAfterJudge(markId);
});

/** 판단 후 다음 미검토 차이로 이동(설계안 §7) — 판단된 마크의 type과 무관하게
 * 항상 "다음 미검토 차이"다(스펙 원문 그대로, N키와 같은 대상 집합).
 * N키처럼 이미 필터링된 배열을 돌리지 않는 이유: 방금 판단한 마크가 diff 타입이면
 * 그 자리가 기준점이어야 "다음"이 이어진다 — 전체 diff를 page순으로 두고 그
 * 마크의 위치에서부터 pending을 찾는다(판단된 마크 자신은 이제 pending이 아니라
 * 자연히 건너뛴다). 판단한 마크가 unverified면 idx=-1이라 처음부터 찾는다(N키가
 * 미선택 상태에서 0번부터 시작하는 것과 동일한 동작). */
function advanceAfterJudge(judgedId) {
  const diffs = [...MARKS].filter((m) => m.type === "diff").sort((a, b) => a.page - b.page);
  const idx = diffs.findIndex((m) => m.id === judgedId);
  for (let i = 1; i <= diffs.length; i++) {
    const cand = diffs[(idx + i) % diffs.length];
    if (cand.status === "pending") { selectMark(cand, { switchToDiffTab: true }); return; }
  }
  clearSelection();
  emit("reviewComplete"); // detail.js가 "미검토 차이 없음" 완료 상태로 전환
}

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
  DOCUMENT_COUNTS = res.counts;
  // 저장된 판단은 api가 marks에 이미 얹어 보낸다. 적용 실패·유실은 조용히 넘기지
  // 않는다 — 판단이 사라진 것처럼 보이면 회계사가 다시 검토하게 된다(U-6 §1).
  if (res.review_error) emit("saveError", res.review_error);
  else if (res.review && res.review.missing && res.review.missing.length) {
    emit("saveError",
      `저장된 판단 ${res.review.missing.length}건이 현재 marks.json에 없는 항목입니다 ` +
      `(재분석으로 항목이 바뀐 것으로 보입니다). 적용되지 않았습니다: ` +
      res.review.missing.slice(0, 5).join(", "));
  }
  renderCounters(DOCUMENT_COUNTS);
  renderList();
}

loadMarks().catch((e) => {
  el.list.innerHTML = `<div class="empty">목록을 불러올 수 없습니다<br>${escapeHtml(e.message || String(e))}</div>`;
});
