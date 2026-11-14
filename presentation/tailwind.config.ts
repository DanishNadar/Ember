import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./slides/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#0B0606",
        basalt: "#1A0F0C",
        ash: "#2A1712",
        ember: "#FF6B35",
        fire: "#E53935",
        cyan: { sci: "#48D8FF" },
        verified: "#35D6A0",
        ink: "#F3F6FA",
        mute: "#C2AFA4",
        dim: "#8A7266",
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
