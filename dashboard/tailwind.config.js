/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#08080a",
        panel: "#121214",
        raise: "#1a1a1e",
        line: "#2a2a30",
        mist: "#8b8b95",
        paper: "#f4f4f6",
        accent: "#e9e9ee",
        accent2: "#b9b9c2",
        warn: "#9a9aa4",
        danger: "#fafafa",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        serif: ["Instrument Serif", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "Consolas", "monospace"],
      },
      boxShadow: {
        matte:
          "inset 0 1px 0 0 rgba(255,255,255,0.05), 0 1px 2px 0 rgba(0,0,0,0.6), 0 12px 32px -18px rgba(0,0,0,0.9)",
        lift:
          "inset 0 1px 0 0 rgba(255,255,255,0.08), 0 2px 4px 0 rgba(0,0,0,0.5), 0 18px 40px -20px rgba(0,0,0,1)",
      },
    },
  },
  plugins: [],
};
