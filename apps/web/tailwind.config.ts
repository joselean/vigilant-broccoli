import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#000000",
          900: "#08090b",
          800: "#111214",
          700: "#1c1d20",
          600: "#2a2b2f",
        },
        glow: "#e8ecff",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 24px 2px rgba(232, 236, 255, 0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
