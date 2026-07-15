/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f9f9fb",
        ink:    "#1a1a1a",
        sub:    "#6b7280",
        faint:  "#9ca3af",
        line:   "#e5e7eb",
        line2:  "#d1d5db",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

