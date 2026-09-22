/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Syne'", "sans-serif"],
        body: ["'DM Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        brand: {
          50:  "#f0f4ff",
          100: "#dde7ff",
          200: "#b3c8ff",
          300: "#7aa3ff",
          400: "#4a7dff",
          500: "#2259f5",
          600: "#1540d4",
          700: "#0f2fab",
          800: "#0c2285",
          900: "#091a6a",
        },
        surface: {
          950: "#050810",
          900: "#090d1a",
          800: "#0f1528",
          700: "#162038",
          600: "#1e2d4a",
          500: "#26395e",
        },
        accent: {
          cyan:   "#00d4ff",
          violet: "#8b5cf6",
          amber:  "#f59e0b",
          rose:   "#f43f5e",
          emerald:"#10b981",
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-mesh": "radial-gradient(at 40% 20%, hsla(228,100%,74%,0.15) 0, transparent 50%), radial-gradient(at 80% 0%, hsla(189,100%,56%,0.1) 0, transparent 50%), radial-gradient(at 0% 50%, hsla(355,100%,93%,0.05) 0, transparent 50%)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float":      "float 6s ease-in-out infinite",
        "glow":       "glow 2s ease-in-out infinite",
        "scan":       "scan 2s linear infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-10px)" },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(74, 125, 255, 0.3)" },
          "50%":      { boxShadow: "0 0 40px rgba(74, 125, 255, 0.6)" },
        },
        scan: {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100vh)" },
        },
      },
      backdropBlur: { xs: "2px" },
      boxShadow: {
        "glass":       "0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)",
        "glow-brand":  "0 0 40px rgba(74, 125, 255, 0.4)",
        "glow-cyan":   "0 0 30px rgba(0, 212, 255, 0.3)",
        "card":        "0 20px 60px rgba(0, 0, 0, 0.5)",
      },
    },
  },
  plugins: [],
};
