/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      colors: {
        brand: {
          DEFAULT: '#00d4ff',   // electric cyan — primary accent
          dim:     '#0099bb',
          glow:    'rgba(0,212,255,0.15)',
        },
        accent: {
          DEFAULT: '#00ff88',   // electric green — success / SHOW
          dim:     '#00c466',
        },
        show:     { DEFAULT: '#00ff88', light: '#b3ffe0', dark: '#00994d' },
        swap:     { DEFAULT: '#ffb800', light: '#fff0b3', dark: '#cc9300' },
        delay:    { DEFAULT: '#ff6b00', light: '#ffd9b3', dark: '#cc5500' },
        suppress: { DEFAULT: '#ff2d55', light: '#ffb3c0', dark: '#cc0033' },
      },
      boxShadow: {
        'glow-brand':  '0 0 24px rgba(0,212,255,0.20)',
        'glow-accent': '0 0 24px rgba(0,255,136,0.20)',
        'glow-red':    '0 0 16px rgba(255,45,85,0.25)',
      },
      keyframes: {
        'gradient-x': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%':      { backgroundPosition: '100% 50%' },
        },
        'slide-up': {
          '0%':   { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'ticker-in': {
          '0%':   { opacity: '0', transform: 'translateX(-10px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'scan': {
          '0%':   { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(400%)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-5px)' },
        },
      },
      animation: {
        'gradient-x': 'gradient-x 6s ease infinite',
        'slide-up':   'slide-up 0.45s ease-out',
        'fade-in':    'fade-in 0.35s ease-out',
        'ticker-in':  'ticker-in 0.3s ease-out',
        'scan':       'scan 3.5s linear infinite',
        'float':      'float 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
