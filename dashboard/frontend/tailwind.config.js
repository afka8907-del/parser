/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark-bg': '#0f172a',
        'dark-card': '#1e293b',
        'dark-border': '#334155',
        'accent': '#3b82f6',
        'accent-hover': '#2563eb',
        'success': '#10b981',
        'warning': '#f59e0b',
        'danger': '#ef4444',
      },
    },
  },
  plugins: [],
}
