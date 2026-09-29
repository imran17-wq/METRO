/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: {
          DEFAULT: "#F5F0E8",
          50: "#FDFCF9",
          100: "#F5F0E8",
          200: "#EDE5D3",
        },
        rust: {
          DEFAULT: "#C4472B",
          light: "#D9614A",
          dark: "#A33820",
        },
        mustard: {
          DEFAULT: "#D4A017",
          light: "#E8BB3A",
          dark: "#AA7F10",
        },
        dark: {
          bg: "#0A0A0A",
          surface: "#111111",
          card: "#181818",
          border: "#242424",
          hover: "#1E1E1E",
        },
        metro: {
          purple: "#7B2D8B",
          "purple-light": "#9B4DAB",
          green: "#2A7D4F",
          "green-light": "#3A9D6F",
          yellow: "#D4A017",
          "yellow-light": "#E8BB3A",
        },
      },
      fontFamily: {
        heading: ["Anton", "sans-serif"],
        editorial: ["Fraunces", "serif"],
        data: ["Courier Prime", "monospace"],
        body: ["Inter", "system-ui", "sans-serif"],
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-in-out",
        "slide-up": "slideUp 0.3s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};
