// start.js — 시작 화면(run.bat 설계안_run_시작화면.md). 검토자 이름·최근 목록·
// 보고서 열기·분석 진행 표시. 검토 화면(index.html/export.js)과는 별개 문서라
// bus.js를 쓰지 않는다 — 화면 전환은 Python(api._goto_viewer)이 window.load_url로
// 한다. 이 파일이 하는 일은 "누른다 → api를 부른다 → 결과를 보여준다"뿐이다.

const el = {
  version: document.getElementById("toolVersion"),
  reviewerAsk: document.getElementById("reviewerAsk"),
  reviewerInput: document.getElementById("reviewerInput"),
  reviewerSave: document.getElementById("reviewerSave"),
  reviewerLine: document.getElementById("reviewerLine"),
  reviewerName: document.getElementById("reviewerName"),
  reviewerEdit: document.getElementById("reviewerEdit"),
  btnOpen: document.getElementById("btnOpen"),
  recentsList: document.getElementById("recentsList"),
  recentsEmpty: document.getElementById("recentsEmpty"),
  statusBar: document.getElementById("statusBar"),
  progressWrap: document.getElementById("progressWrap"),
  progressText: document.getElementById("progressText"),
};

let curEta = null;   // {pages, low_s, high_s} — 진행 중인 분석의 예상 범위
let opening = false; // 중복 클릭 방지

function api() { return (window.pywebview && window.pywebview.api) || null; }
function waitForApi() {
  if (api()) return Promise.resolve();
  return new Promise((r) => window.addEventListener("pywebviewready", () => r(), { once: true }));
}

function say(msg, kind) {
  el.statusBar.textContent = msg || "";
  el.statusBar.className = kind || "";
  el.statusBar.hidden = !msg;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ── 진행 표시 — 예상 소요 범위. 정확한 페이지 진행률은 이번 범위 밖이다
// (final.py를 안 건드리기로 함, 설계안 §2 B안) — 경과 시간 + 문서별 예상 범위로
// "죽었나"를 판단할 근거를 준다. 30초 고정이 아니라 이 문서의 예상 상한을 넘기면
// 안내 문구를 바꾼다(문서마다 정상 소요가 다르므로).
function fmtRange(lowS, highS) {
  if (highS < 60) return `${lowS}~${highS}초`;
  const lo = Math.round(lowS / 60), hi = Math.round(highS / 60);
  return lo === hi ? `약 ${lo}분` : `약 ${lo}~${hi}분`;
}
function fmtElapsed(s) {
  const m = Math.floor(s / 60), sec = s % 60;
  return m > 0 ? `${m}분 ${sec}초` : `${sec}초`;
}

function showProgress(eta) {
  curEta = eta;
  el.btnOpen.disabled = true;
  el.progressWrap.hidden = false;
  say("");
  updateProgressText(0);
}
function hideProgress() {
  el.btnOpen.disabled = false;
  el.progressWrap.hidden = true;
  curEta = null;
}
function updateProgressText(elapsed) {
  const base = curEta
    ? `분석 중… 총 ${curEta.pages}면, 경과 ${fmtElapsed(elapsed)} (보통 ${fmtRange(curEta.low_s, curEta.high_s)} 걸립니다)`
    : `분석 중… 경과 ${fmtElapsed(elapsed)}`;
  const late = curEta && elapsed > curEta.high_s
    ? "\n예상보다 오래 걸리고 있습니다 — 표가 많거나 복잡한 문서일 수 있습니다. 창은 계속 열어 두십시오."
    : "";
  el.progressText.textContent = base + late;
}

// api.py의 _push_progress가 부르는 전역 훅. window.__dsdProgress로 고정된 이름이다
// (api.py 참고) — 읽기 전용 훅이 아니라 진행 신호 수신용이라 이름 규약이 다르다.
window.__dsdProgress = (payload) => {
  if (payload.error) {
    hideProgress();
    say(payload.error, "err");
    opening = false;
    return;
  }
  if (typeof payload.elapsed === "number") updateProgressText(payload.elapsed);
};

// ── 검토자 ───────────────────────────────────────────────────────
async function refreshReviewer() {
  const r = await api().get_reviewer();
  const name = (r && r.reviewer) || "";
  if (name) {
    el.reviewerName.textContent = name;
    el.reviewerLine.hidden = false;
    el.reviewerAsk.hidden = true;
  } else {
    el.reviewerLine.hidden = true;
    el.reviewerAsk.hidden = false;
  }
}
el.reviewerSave.addEventListener("click", async () => {
  const r = await api().set_reviewer(el.reviewerInput.value);
  if (r && r.error) { say(r.error, "err"); return; }
  await refreshReviewer();
});
el.reviewerInput.addEventListener("keydown", (e) => { if (e.key === "Enter") el.reviewerSave.click(); });
el.reviewerEdit.addEventListener("click", () => {
  el.reviewerInput.value = el.reviewerName.textContent;
  el.reviewerLine.hidden = true;
  el.reviewerAsk.hidden = false;
  el.reviewerInput.focus();
});

// ── 최근 목록 ────────────────────────────────────────────────────
async function refreshRecents() {
  const r = await api().list_recents();
  const items = (r && r.recents) || [];
  el.recentsEmpty.hidden = items.length > 0;
  el.recentsList.innerHTML = items.map((it) => `
    <div class="item ${it.exists ? "" : "missing"}" data-path="${escapeHtml(it.path)}"
         data-exists="${it.exists}">
      <span class="name">${escapeHtml(it.name)}</span>
      <span class="meta">${escapeHtml(it.last_opened || "")}</span>
    </div>`).join("");
}
el.recentsList.addEventListener("click", async (ev) => {
  const row = ev.target.closest(".item");
  if (!row || opening) return;
  const path = row.dataset.path;
  if (row.dataset.exists !== "true") {
    // 회색 처리된 항목 — 조용히 지우지 않는다. 확인 후에만 목록에서 뺀다(설계안 §6).
    if (window.confirm(`파일을 찾을 수 없습니다:\n${path}\n\n최근 목록에서 지우시겠습니까?`)) {
      await api().remove_recent(path);
      await refreshRecents();
    }
    return;
  }
  openPath(path);
});

// ── 열기 — 대화상자·최근 목록·CLI 인자 셋 다 이 함수 하나로 모인다 ──────────
async function openPath(path) {
  if (opening) return;
  opening = true;
  say("");
  const r = await api().begin_open(path);
  if (!r) { opening = false; return; }
  if (r.error) { say(r.error, "err"); opening = false; return; }
  if (r.status === "opened") return; // 화면이 곧 전환된다 — 여기서 더 할 일 없음
  if (r.status === "analyzing") { showProgress(r.eta); return; }
  if (r.status === "warn_reanalyze") {
    opening = false;
    // 네이티브 confirm — 별도 모달 마크업을 안 쓴다. hidden이 작성자 CSS의 display에
    // 지는 결함(U-6, CLAUDE.md 결정 34)을 이 화면에서 반복하지 않는 가장 확실한 길이다.
    if (window.confirm(r.message + "\n\n계속 진행하시겠습니까?")) {
      opening = true;
      const r2 = await api().confirm_reanalyze(path);
      if (r2.error) { say(r2.error, "err"); opening = false; return; }
      if (r2.status === "analyzing") showProgress(r2.eta);
    }
    return;
  }
}
el.btnOpen.addEventListener("click", async () => {
  if (opening) return;
  const r = await api().pick_report();
  if (r && r.error) { say(r.error, "err"); return; }
  if (r && r.path) openPath(r.path);   // 취소는 path:null — 조용히 아무 일도 안 함
});

// ── 시작 ─────────────────────────────────────────────────────────
async function init() {
  const v = await api().get_tool_version();
  el.version.textContent = `버전 ${(v && v.version) || "?"}`;
  await Promise.all([refreshReviewer(), refreshRecents()]);

  // CLI 인자(python ui/app.py <원본.pdf>)로 열린 경우 — 대화상자로 고른 것과
  // 완전히 같은 openPath 경로를 태운다(app.py 모듈 docstring 참고).
  const startup = await api().get_startup_arg();
  if (startup && startup.path) openPath(startup.path);
}
waitForApi().then(init).catch((e) => say(String(e && e.message || e), "err"));

// 개발 검증용 읽기 전용 훅(U-4 viewer.js와 같은 패턴) — 테스트가 이 화면이 실제로
// 쓰는 함수를 그대로 태우게 한다. window.confirm()이 열리면 CDP 연결 자체가
//막히는 이 환경의 제약(2026-08-31 실측) 때문에, 대화상자가 뜨기 전에 미리 CDP를
// 붙여 openPath를 직접 부르는 경로가 필요하다. 상태를 바꾸는 새 진입점이 아니라
// 버튼 클릭이 부르는 것과 동일한 함수를 노출할 뿐이다.
window.__dsdDebug = Object.freeze({ openPath });
