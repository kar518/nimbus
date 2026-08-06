/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Neutral surface scale — dashboards live or die on legible neutrals.
        surface: {
          50: "#f7f8fa",
          100: "#eef0f3",
          200: "#dde1e7",
          300: "#c1c7d1",
          400: "#8f97a5",
          500: "#646c7a",
          600: "#4a505c",
          700: "#383d47",
          800: "#24272e",
          900: "#15171b",
          950: "#0b0c0e",
        },
        // Status colors used consistently for job/worker states.
        status: {
          queued: "#8f97a5",
          running: "#2563eb",
          succeeded: "#16a34a",
          failed: "#dc2626",
          cancelled: "#a855f7",
        },
        accent: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
