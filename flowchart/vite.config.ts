import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Electron 은 file:// 로 index.html 을 로드하므로 자산 경로를 상대경로로.
  //   (브라우저 dev/preview 에도 영향 없음 — "./" 는 양쪽 모두 동작)
  base: "./",
  server: {
    port: 5173,
    host: "127.0.0.1",
    strictPort: false,
  },
  build: {
    target: "es2022",
    sourcemap: true,
  },
});
