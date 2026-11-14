import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./slides/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#080B10",
        basalt: "#111722",
        ash: "#1A2230",
        ember: "#FF6B35",
        fire: "#E53935",
        cyan: { sci: "#48D8FF" },
        verified: "#35D6A0",
        ink: "#F3F6FA",
        mute: "#94A3B8",
        dim: "#5B6678",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
