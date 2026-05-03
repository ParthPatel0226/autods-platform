import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cosmic: {
          900: "#07091A",
          800: "#0C0F2D",
          700: "#11173D",
          600: "#1A2150",
        },
        accent: {
          violet: "#A855F7",
          indigo: "#6366F1",
          purple: "#8B5CF6",
          pink: "#EC4899",
          cyan: "#22D3EE",
          green: "#10B981",
          amber: "#F59E0B",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      backgroundImage: {
        "aurora-1":
          "radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.15) 0%, transparent 70%)",
        "aurora-2":
          "radial-gradient(ellipse at 80% 20%, rgba(168,85,247,0.12) 0%, transparent 70%)",
        "aurora-3":
          "radial-gradient(ellipse at 50% 80%, rgba(34,211,238,0.08) 0%, transparent 70%)",
      },
      borderRadius: {
        "4xl": "2rem",
        "5xl": "2.5rem",
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
        "glass-lg": "0 16px 48px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.08)",
        glow: "0 0 20px rgba(168, 85, 247, 0.3)",
        "glow-lg": "0 0 40px rgba(168, 85, 247, 0.4)",
        "glow-cyan": "0 0 20px rgba(34, 211, 238, 0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
