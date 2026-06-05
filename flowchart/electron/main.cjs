/**
 * Electron 메인 프로세스 — ICFR Flowchart Generator 데스크톱 셸.
 *
 *  ⚠ package.json 이 "type":"module" 이므로 CommonJS 메인은 .cjs 확장자 사용.
 *
 *  보안 원칙 (오프라인 로컬 전용 앱):
 *   - nodeIntegration: false  / contextIsolation: true  / sandbox: true
 *   - webSecurity: true
 *   - 외부 네트워크(http/https/ws) 요청 전면 차단 — 로컬 file/blob/data 만 허용
 *   - 외부 URL 네비게이션·새 창 차단
 *   - 메뉴바 제거, 개발자도구 비활성
 */
const { app, BrowserWindow, Menu, session, shell } = require("electron");
const path = require("path");

const isDev = !app.isPackaged && !!process.env.ELECTRON_START_URL;

function installNetworkBlock() {
  // 로컬 리소스만 허용 — 그 외(외부 네트워크)는 전부 차단.
  const ALLOWED = ["file:", "blob:", "data:", "devtools:", "chrome-extension:"];
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    // dev 모드에서는 vite dev 서버(http://127.0.0.1:5173) 허용
    if (isDev && details.url.startsWith("http://127.0.0.1")) {
      callback({ cancel: false });
      return;
    }
    const ok = ALLOWED.some((p) => details.url.startsWith(p));
    callback({ cancel: !ok });
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    title: "ICFR Flowchart Generator",
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      devTools: false, // 개발자도구 숨김
    },
  });

  // 메뉴바 최소화(제거)
  Menu.setApplicationMenu(null);

  if (isDev) {
    win.loadURL(process.env.ELECTRON_START_URL);
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  // 새 창 요청 차단 (target=_blank, window.open 등)
  win.webContents.setWindowOpenHandler(({ url }) => {
    // 외부 링크는 절대 새 창/내부 로드하지 않음 (필요 시 OS 기본 브라우저로만)
    if (/^https?:/.test(url)) {
      // 정책상 외부도 열지 않음 — 완전 오프라인. 열고 싶으면 아래 주석 해제.
      // shell.openExternal(url);
    }
    return { action: "deny" };
  });

  // 외부 URL 네비게이션 차단 — 로컬 file/dev 서버만 허용
  win.webContents.on("will-navigate", (event, url) => {
    const allowed =
      url.startsWith("file://") ||
      (isDev && url.startsWith("http://127.0.0.1"));
    if (!allowed) event.preventDefault();
  });

  // 권한 요청(카메라/위치/알림 등) 전면 거부
  session.defaultSession.setPermissionRequestHandler((_wc, _perm, cb) => cb(false));
}

app.whenReady().then(() => {
  installNetworkBlock();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

// shell 은 향후 확장용 — 현재는 사용 안 함(외부 차단 정책).
void shell;
