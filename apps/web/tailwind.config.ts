/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ow: {
          bg: "#0a0a0f",
          surface: "#12121a",
          "surface-elevated": "#1a1a26",
          border: "#2a2a3a",
          "border-subtle": "#1e1e2e",
          text: "#e8e8f0",
          "text-muted": "#8888a0",
          "text-dim": "#5a5a70",
          accent: "#00d4ff",
          "accent-dim": "#0099bb",
          trusted: "#00e676",
          approval: "#ffb300",
          blocked: "#ff5252",
          intelligence: "#b388ff",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(0, 212, 255, 0.15)",
        "glow-sm": "0 0 10px rgba(0, 212, 255, 0.1)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
