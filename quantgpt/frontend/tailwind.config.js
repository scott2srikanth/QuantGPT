/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef6ff",
          100: "#d9eaff",
          500: "#2f7bff",
          600: "#1f63e0",
          700: "#174fb0",
        },
      },
    },
  },
  plugins: [],
};
