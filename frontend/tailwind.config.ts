import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172033",
        brand: "#2f5bea",
        canvas: "#f5f7fb",
      },
      boxShadow: {
        card: "0 1px 2px rgba(23, 32, 51, 0.04), 0 8px 24px rgba(23, 32, 51, 0.05)",
      },
    },
  },
  plugins: [],
};

export default config;

