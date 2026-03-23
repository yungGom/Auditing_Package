/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "background": "#f8f9fa",
        "surface-container-highest": "#e1e3e4",
        "secondary": "#48626e",
        "on-tertiary-container": "#ff6c63",
        "primary-container": "#003366",
        "primary": "#001e40",
        "primary-fixed": "#d5e3ff",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f3f4f5",
        "surface-container": "#edeeef",
        "on-surface": "#191c1d",
        "on-surface-variant": "#43474f",
        "outline": "#737780",
        "outline-variant": "#c3c6d1",
        "error": "#ba1a1a",
        "secondary-container": "#cbe7f5",
        "on-secondary-container": "#4e6874",
        "tertiary-fixed": "#ffdad6",
        "on-tertiary-fixed-variant": "#930010",
      },
      fontFamily: {
        "headline": ["Manrope", "sans-serif"],
        "body": ["Inter", "sans-serif"],
        "label": ["Inter", "sans-serif"],
      },
      borderRadius: {
        "DEFAULT": "0.125rem",
        "lg": "0.25rem",
        "xl": "0.5rem",
        "full": "0.75rem",
      },
    },
  },
  plugins: [],
}
