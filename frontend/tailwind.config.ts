import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Vercel-inspired dark adaptation
        background: "#0a0a0a",
        surface: "#111111",
        "surface-light": "#1a1a1a",
        "surface-softer": "#222222",
        border: "#2e2e2e",
        "border-strong": "#444444",
        ink: "#ededed",
        body: "#a1a1a1",
        mute: "#666666",
        accent: "#0070f3",
        "accent-soft": "#003fbf",
        "accent-red": "#ee0000",
        "accent-yellow": "#f5a623",
        "accent-cyan": "#50e3c2",
        "accent-violet": "#7928ca",
        "accent-pink": "#ff0080",
        // Vercel brand gradients
        "gradient-develop": "#007cf0",
        "gradient-develop-end": "#00dfd8",
        "gradient-preview": "#7928ca",
        "gradient-preview-end": "#ff0080",
        "gradient-ship": "#ff4d4d",
        "gradient-ship-end": "#f9cb28",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "monospace"],
      },
      borderRadius: {
        xs: "4px",
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
        "pill-sm": "64px",
        pill: "100px",
      },
      boxShadow: {
        "vercel-1": "0 0 0 1px rgba(255,255,255,0.05) inset",
        "vercel-2": "0 1px 1px rgba(0,0,0,0.3), 0 2px 2px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05) inset",
        "vercel-3": "0 2px 2px rgba(0,0,0,0.2), 0 8px 8px -8px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05) inset",
        "vercel-4": "0 2px 2px rgba(0,0,0,0.2), 0 8px 16px -4px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05) inset",
      },
      letterSpacing: {
        display: "-0.04em",
      },
    },
  },
  plugins: [],
};
export default config;
