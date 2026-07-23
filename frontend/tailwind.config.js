/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Deep apothecary sage/forest green — the primary brand color.
        brand: {
          50: "#F0F6F2",
          100: "#DCEBE1",
          200: "#B9D6C3",
          300: "#8FBA9E",
          400: "#639B79",
          500: "#437E5B",
          600: "#316348",
          700: "#264E39",
          800: "#1D3C2C",
          900: "#152C20",
          950: "#0C1A13",
        },
        // Muted antique gold — used sparingly for premium accents (top-pick
        // badges, subtle highlights), never as a primary action color.
        gold: {
          50: "#FBF7EF",
          100: "#F4E8D3",
          200: "#E7D2A7",
          300: "#D8B978",
          400: "#C7A050",
          500: "#AC8538",
          600: "#8A692C",
          700: "#6B5222",
        },
        // Warm paper background, softer and more apothecary-label than
        // stark white or cool gray.
        paper: {
          DEFAULT: "#FBF9F4",
          100: "#F6F2E9",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "Cambria", "serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(21, 44, 32, 0.04), 0 4px 16px rgba(21, 44, 32, 0.06)",
        panel: "0 1px 3px rgba(21, 44, 32, 0.05), 0 8px 24px rgba(21, 44, 32, 0.05)",
      },
    },
  },
  plugins: [],
};
