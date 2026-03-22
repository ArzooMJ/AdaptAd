/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        show:     { DEFAULT: '#22c55e', light: '#bbf7d0', dark: '#15803d' },
        soften:   { DEFAULT: '#f59e0b', light: '#fde68a', dark: '#b45309' },
        delay:    { DEFAULT: '#f97316', light: '#fed7aa', dark: '#c2410c' },
        suppress: { DEFAULT: '#ef4444', light: '#fecaca', dark: '#b91c1c' },
      },
    },
  },
  plugins: [],
}
