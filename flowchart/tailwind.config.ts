import type { Config } from "tailwindcss";
import { tailwindTheme } from "./src/design";

/**
 * Tailwind 설정은 src/design.ts 의 토큰을 그대로 흡수한다.
 * 색·폰트를 바꾸려면 design.ts 만 손대면 된다.
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: tailwindTheme.colors,
      fontFamily: tailwindTheme.fontFamily,
    },
  },
  plugins: [],
};

export default config;
