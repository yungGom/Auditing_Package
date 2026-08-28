// viewer.js — U-1 최소 렌더러. pdf.js 코어만 쓴다(공식 뷰어 UI 미사용,
// 설계안_UI셸_U1.md §1 결정 A). PDF는 PyWebView 브리지로 바이트를 직접 받는다 —
// fetch/XHR을 전혀 쓰지 않는다(§1 결정 A의 "네트워크 요청 0건" 근거).
import * as pdfjsLib from "./vendor/pdfjs/build/pdf.mjs";
import { on, emit } from "./bus.js";
import { hitTest, pdfRectToViewport, glyphRect } from "./hit.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = "./vendor/pdfjs/build/pdf.worker.mjs";

const CMAP_URL = "./vendor/pdfjs/web/cmaps/";
const FONT_URL = "./vendor/pdfjs/web/standard_fonts/";
// 0.8 대신 0.75를 둔다 — U-4 게이트가 "75%에서도 좌표가 맞는가"를 요구하는데
// 단계에 없으면 그 배율을 실제로 재볼 수가 없다. 인덱스 3 = 1.0(기본)은 그대로.
const ZOOM_STEPS = [0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3];

const el = {
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
  pageNum: document.getElementById("pageNum"),
  pageCount: document.getElementById("pageCount"),
  zoomIn: document.getElementById("zoomIn"),
  zoomOut: document.getElementById("zoomOut"),
  zoomLabel: document.getElementById("zoomLabel"),
  status: document.getElementById("status"),
  canvas: document.getElementById("page"),
  ring: document.getElementById("ring"),
  popup: document.getElementById("candidatePopup"),
};

let pdfDoc = null;
let curPage = 1;
let zoomIdx = 3; // ZOOM_STEPS[3] = 1.0
let renderTask = null; // 진행 중인 렌더를 취소하기 위함 — 빠른 연타 대비
let curViewport = null;   // 현재 페이지의 viewport — 클릭 역변환·링 배치의 기준
let MARKS = [];           // 히트 판정용(읽기 전용). 선택 상태는 sidebar가 소유한다
let OFFSETS = null;       // ui/glyph_offsets.json — 글리프 히트영역의 유일한 출처
let selected = null;      // sidebar가 selectionChanged로 알려준 확정 선택

function setStatus(msg) { el.status.textContent = msg || ""; }

function waitForApi() {
  // pywebview는 브리지 준비가 끝나면 pywebviewready 이벤트를 쏜다. 이미 준비돼
  // 있으면 이벤트가 안 올 수 있어 존재 여부도 같이 본다.
  if (window.pywebview && window.pywebview.api) return Promise.resolve();
  return new Promise((resolve) => {
    window.addEventListener("pywebviewready", () => resolve(), { once: true });
  });
}

async function loadPdf() {
  await waitForApi();
  const res = await window.pywebview.api.get_pdf();
  if (res.error) { setStatus(res.error); return; }
  const bytes = Uint8Array.from(atob(res.base64), (c) => c.charCodeAt(0));
  const task = pdfjsLib.getDocument({
    data: bytes, cMapUrl: CMAP_URL, cMapPacked: true, standardFontDataUrl: FONT_URL,
  });
  pdfDoc = await task.promise;
  el.pageCount.textContent = `/ ${pdfDoc.numPages}`;
  el.pageNum.max = pdfDoc.numPages;
  document.title = `${res.name} — DSD 풋팅`;

  // 히트 판정에 필요한 것만 따로 읽는다(읽기 전용 사본). 선택 상태는 sidebar 소유라
  // 여기서 만들지 않는다 — 이 배열은 좌표 비교에만 쓴다.
  const mk = await window.pywebview.api.get_marks();
  if (!mk.error) MARKS = mk.marks;
  const off = await window.pywebview.api.get_glyph_offsets();
  if (off.error) setStatus(off.error); else OFFSETS = off;

  await renderPage(1);
}

async function renderPage(n) {
  if (!pdfDoc || n < 1 || n > pdfDoc.numPages) return;
  curPage = n;
  el.pageNum.value = n;
  el.prev.disabled = n <= 1;
  el.next.disabled = n >= pdfDoc.numPages;
  // 이동 수단(목록 클릭·이전/다음·페이지 직접 입력) 구분 없이 매번 낸다 — sidebar.js가
  // "선택된 마크의 페이지와 달라졌으면 선택 해제"를 판단하는 유일한 신호다(설계안 §2).
  emit("pageChanged", n);

  if (renderTask) { renderTask.cancel(); }
  const page = await pdfDoc.getPage(n);
  const dpr = window.devicePixelRatio || 1;
  const scale = ZOOM_STEPS[zoomIdx];
  const viewport = page.getViewport({ scale });

  el.canvas.width = Math.round(viewport.width * dpr);
  el.canvas.height = Math.round(viewport.height * dpr);
  el.canvas.style.width = `${Math.round(viewport.width)}px`;
  el.canvas.style.height = `${Math.round(viewport.height)}px`;

  curViewport = viewport;   // 클릭 역변환·링 배치가 같은 viewport를 쓴다
  const ctx = el.canvas.getContext("2d");
  const transform = dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null;
  renderTask = page.render({ canvasContext: ctx, viewport, transform });
  try {
    await renderTask.promise;
    setStatus("");
  } catch (e) {
    if (e && e.name !== "RenderingCancelledException") setStatus(`렌더 실패: ${e.message || e}`);
  } finally {
    renderTask = null;
  }
  drawRing();               // 확대·페이지 이동 후에도 링이 따라온다
}

/** 선택 마크의 anchor_bbox에 링을 얹는다. 히트 판정과 같은 변환 함수를 쓴다. */
function drawRing() {
  if (!selected || !curViewport || selected.page !== curPage) {
    el.ring.hidden = true;
    return;
  }
  const b = selected.box;   // anchor_bbox와 동일 사각형(U-4 진단 §0-1에서 전수 확인)
  const r = pdfRectToViewport(b, curViewport);
  el.ring.style.left = `${r.left}px`;
  el.ring.style.top = `${r.top}px`;
  el.ring.style.width = `${r.right - r.left}px`;
  el.ring.style.height = `${r.bottom - r.top}px`;
  el.ring.hidden = false;
  // 확대하면 지면이 창보다 커져 선택한 마크가 화면 밖에 있을 수 있다. 그러면
  // 목록에서 골랐는데 아무것도 안 보인다 — 보이는 곳으로 끌어온다. 이미 보이면
  // block:"nearest"라 아무 일도 일어나지 않는다(150% 게이트에서 실측된 결함).
  el.ring.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function closePopup() { el.popup.hidden = true; el.popup.innerHTML = ""; }

function openPopup(clientX, clientY, cands) {
  el.popup.innerHTML =
    `<div class="cap">이 위치에 ${cands.length}건이 겹칩니다</div>` +
    cands.map((m) => {
      const sub = (m.formula || "").split(" — ")[0];
      return `<button class="cand" data-mark-id="${m.id}">
        <div class="t">${escapeHtml(m.account || "")}</div>
        <div class="s">${escapeHtml(sub)}</div></button>`;
    }).join("");
  el.popup.style.left = `${clientX + 6}px`;
  el.popup.style.top = `${clientY + 6}px`;
  el.popup.hidden = false;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

el.prev.addEventListener("click", () => renderPage(curPage - 1));
el.next.addEventListener("click", () => renderPage(curPage + 1));
el.pageNum.addEventListener("change", () => {
  const n = parseInt(el.pageNum.value, 10);
  if (Number.isInteger(n)) renderPage(n); else el.pageNum.value = curPage;
});
el.zoomIn.addEventListener("click", () => {
  if (zoomIdx < ZOOM_STEPS.length - 1) zoomIdx++;
  applyZoom();
});
el.zoomOut.addEventListener("click", () => {
  if (zoomIdx > 0) zoomIdx--;
  applyZoom();
});
function applyZoom() {
  el.zoomLabel.textContent = `${Math.round(ZOOM_STEPS[zoomIdx] * 100)}%`;
  el.zoomIn.disabled = zoomIdx >= ZOOM_STEPS.length - 1;
  el.zoomOut.disabled = zoomIdx <= 0;
  renderPage(curPage);
}

// ── 지면 클릭 → 마크 판정 ────────────────────────────────────────────
el.canvas.addEventListener("click", (ev) => {
  closePopup();
  if (!curViewport || !OFFSETS) return;
  // client → 뷰포트 좌표. rect/viewport 비율을 곱해 CSS 스케일이 끼어도 안전하게.
  // 반올림하지 않는다.
  const rect = el.canvas.getBoundingClientRect();
  const vx = (ev.clientX - rect.left) * (curViewport.width / rect.width);
  const vy = (ev.clientY - rect.top) * (curViewport.height / rect.height);
  const here = MARKS.filter((m) => m.page === curPage);
  const hits = hitTest(vx, vy, here, curViewport, OFFSETS);
  if (hits.length === 1) {
    emit("selectMark", hits[0].id);          // 선택 확정은 sidebar가 한다(단일 소유자)
  } else if (hits.length > 1) {
    openPopup(ev.clientX, ev.clientY, hits); // 겹침 — 사용자가 고른다
  } else {
    emit("selectMark", null);                // 빈 공간 → 선택 해제
  }
});

el.popup.addEventListener("click", (ev) => {
  const btn = ev.target.closest(".cand");
  if (!btn) return;
  emit("selectMark", btn.dataset.markId);
  closePopup();
});
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") closePopup(); });

// sidebar가 선택을 확정하면(목록 클릭·J/K/N·지면 클릭 무관) 여기로 온다.
// viewer는 이 이벤트를 되쏘지 않는다 — 루프가 생기지 않는다(설계안 §5).
on("selectionChanged", async (mark) => {
  selected = mark;
  if (mark && mark.page !== curPage) await renderPage(mark.page);
  else drawRing();
});

// 개발 검증용 읽기 전용 훅. 게이트가 좌표식을 다시 구현하면 UI가 틀려도 같이 틀려
// 못 잡으므로, 테스트가 **이 화면이 실제로 쓰는 함수와 상태**를 그대로 태우게 한다.
// 상태를 바꾸는 함수는 노출하지 않는다 — 테스트는 진짜 UI 조작(행 클릭·확대 버튼·
// 페이지 입력)으로만 화면을 움직인다.
window.__dsdDebug = Object.freeze({
  getViewport: () => curViewport,
  getMarks: () => MARKS,
  getOffsets: () => OFFSETS,
  pdfRectToViewport, glyphRect, hitTest,
});

applyZoom();
loadPdf().catch((e) => setStatus(`불러오기 실패: ${e.message || e}`));
