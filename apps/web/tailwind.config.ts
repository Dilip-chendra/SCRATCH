import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#050505",
        surface: {
          DEFAULT: "#0A0A0C",
          elevated: "#121216",
          border: "#1E1E24",
        },
        accent: {
          DEFAULT: "#00D6FF",
          hover: "#33DEFF",
          glow: "rgba(0, 214, 255, 0.15)",
        },
        brand: {
          blue: "#0050FF",
          cyan: "#00D6FF",
        },
        text: {
          primary: "#F0F0F2",
          secondary: "#888890",
          muted: "#5A5A62",
        },
        status: {
          success: "#00E599",
          warning: "#FFB020",
          danger: "#FF453A",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
