/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        command: {
          950: '#030712',
          900: '#070d1d',
          850: '#0b1328',
          800: '#0f1a36',
          700: '#19284d',
          600: '#253966',
        },
        cyan: {
          glow: '#00f3ff',
          dim: '#0099aa',
        },
        flood: {
          water: '#00d2ff',
          new: '#ff3366',
          inundated: '#00f0ff',
          alert: '#ff4d4f',
          safe: '#10b981',
          warning: '#f59e0b',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 20px -2px rgba(0, 243, 255, 0.35)',
        'glow-blue': '0 0 25px -4px rgba(37, 99, 235, 0.4)',
        'glow-alert': '0 0 20px -2px rgba(255, 51, 102, 0.4)',
      },
      backgroundImage: {
        'radial-gradient': 'radial-gradient(circle at center, var(--tw-gradient-stops))',
        'grid-pattern': 'linear-gradient(to right, rgba(0, 243, 255, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 243, 255, 0.05) 1px, transparent 1px)',
      }
    },
  },
  plugins: [],
}
