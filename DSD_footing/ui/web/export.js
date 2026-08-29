// export.js — U-6. 검토자 이름(1회 입력) · 최종 출력 · ERRORS.json 조각 복사 ·
// 저장 실패 표면화. 판단 저장 자체는 sidebar.js가 판단 시점에 즉시 한다.
//
// ★ 이 파일은 ERRORS.json을 읽지도 쓰지도 않는다. 형식 문자열만 만들어 보여준다 —
//   자동 반영은 승인 절차를 우회하는 경로다(U-6 설계안 §6, 2026-08-29 승인).
import { on } from "./bus.js";

const el = {
  bar: document.getElementById("statusBar"),
  reviewer: document.getElementById("reviewerName"),
  reviewerEdit: document.getElementById("reviewerEdit"),
  ask: document.getElementById("reviewerAsk"),
  askInput: document.getElementById("reviewerInput"),
  askSave: document.getElementById("reviewerSave"),
  btnExport: document.getElementById("btnExport"),
  btnErrors: document.getElementById("btnErrors"),
  modal: document.getElementById("snippetModal"),
  snippet: document.getElementById("snippetText"),
  snippetCopy: document.getElementById("snippetCopy"),
  snippetClose: document.getElementById("snippetClose"),
};

function api() {
  return (window.pywebview && window.pywebview.api) || null;
}

function say(msg, kind) {
  el.bar.textContent = msg || "";
  el.bar.className = kind || "";
  el.bar.hidden = !msg;
}

function waitForApi() {
  if (api()) return Promise.resolve();
  return new Promise((r) => window.addEventListener("pywebviewready", () => r(), { once: true }));
}

// 저장·로드 실패는 반드시 눈에 띄어야 한다. 판단이 사라진 것처럼 보이면
// 회계사가 다시 검토하게 되고, 그건 조서 신뢰의 문제다.
on("saveError", (msg) => say(`⚠ ${msg}`, "err"));

async function refreshReviewer() {
  const r = await api().get_reviewer();
  const name = (r && r.reviewer) || "";
  el.reviewer.textContent = name || "(미입력)";
  // 이름이 없으면 첫 실행이다 — 한 번만 묻는다. 인증이 아니라 "누가 검토했는지"다.
  el.ask.hidden = !!name;
  return name;
}

el.askSave.addEventListener("click", async () => {
  const r = await api().set_reviewer(el.askInput.value);
  if (r && r.error) { say(`⚠ ${r.error}`, "err"); return; }
  el.ask.hidden = true;
  await refreshReviewer();
  say("검토자를 저장했습니다.", "ok");
});
el.askInput.addEventListener("keydown", (e) => { if (e.key === "Enter") el.askSave.click(); });

el.reviewerEdit.addEventListener("click", async () => {
  el.askInput.value = el.reviewer.textContent === "(미입력)" ? "" : el.reviewer.textContent;
  el.ask.hidden = false;
  el.askInput.focus();
});

el.btnExport.addEventListener("click", async () => {
  el.btnExport.disabled = true;
  say("최종 PDF를 만드는 중입니다…", "");
  const r = await api().export_final();
  el.btnExport.disabled = false;
  if (r && r.error) { say(`⚠ ${r.error}`, "err"); return; }
  // 미검토가 남은 상태의 출력을 막지 않는다(중간 출력이 실무에서 필요하다).
  // 다만 끝나지 않은 조서가 끝난 것처럼 보이면 안 되므로 여기서도 알린다.
  const warn = r.pending ? ` ⚠ 미검토 ${r.pending}건이 남아 있습니다.` : "";
  say(`저장했습니다: ${r.path}  (이상없음 ${r.approved} · 차이 아님 ${r.removed}${warn})`,
      r.pending ? "err" : "ok");
});

el.btnErrors.addEventListener("click", async () => {
  const r = await api().export_errors_snippet();
  if (r && r.error) { say(`⚠ ${r.error}`, "err"); return; }
  if (!r.count) { say("'차이 아님'으로 판정한 항목이 없습니다.", ""); return; }
  el.snippet.value = r.text;
  el.modal.hidden = false;
});

el.snippetCopy.addEventListener("click", () => {
  el.snippet.select();
  document.execCommand("copy");          // file:// 에서는 navigator.clipboard가 막힌다
  say("복사했습니다. ERRORS.json에 붙여넣고 task를 채우십시오.", "ok");
});
el.snippetClose.addEventListener("click", () => { el.modal.hidden = true; });

waitForApi().then(refreshReviewer).catch((e) => say(`⚠ ${e.message || e}`, "err"));
