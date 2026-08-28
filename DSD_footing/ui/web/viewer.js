// viewer.js — U-1 최소 렌더러. pdf.js 코어만 쓴다(공식 뷰어 UI 미사용,
// 설계안_UI셸_U1.md §1 결정 A). PDF는 PyWebView 브리지로 바이트를 직접 받는다 —
// fetch/XHR을 전혀 쓰지 않는다(§1 결정 A의 "네트워크 요청 0건" 근거).
import * as pdfjsLib from "./vendor/pdfjs/build/pdf.mjs";
import { on, emit } from "./bus.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = "./vendor/pdfjs/build/pdf.worker.mjs";

const CMAP_URL = "./vendor/pdfjs/web/cmaps/";
const FONT_URL = "./vendor/pdfjs/web/standard_fonts/";
const ZOOM_STEPS = [0.5, 0.67, 0.8, 1, 1.25, 1.5, 2, 3];

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
};

let pdfDoc = null;
let curPage = 1;
let zoomIdx = 3; // ZOOM_STEPS[3] = 1.0
let renderTask = null; // 진행 중인 렌더를 취소하기 위함 — 빠른 연타 대비

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

// sidebar.js가 목록 클릭/N/J/K로 선택한 마크의 페이지로 이동시킨다. viewer.js는
// "마크"가 뭔지 전혀 모른다 — 페이지 번호만 받는다(관심사 분리 유지).
on("jumpToPage", (page) => { renderPage(page); });

applyZoom();
loadPdf().catch((e) => setStatus(`불러오기 실패: ${e.message || e}`));
