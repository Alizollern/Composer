/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Глубокий лес — фон тёмных секций / приложения
        forest: {
          DEFAULT: '#0a2a1e',
          900: '#062016',
          800: '#0a2a1e',
          700: '#0e3a2b',
          600: '#134d39',
        },
        // Изумруд — бренд / акцент
        emerald: {
          DEFAULT: '#15a06b',
          400: '#2bc486',
          500: '#15a06b',
          600: '#0f8a5b',
        },
        // Тёплая бумага — светлая база
        paper: {
          DEFAULT: '#faf8f2',
          card: '#ffffff',
          deep: '#f1eee4',
        },
        ink: {
          DEFAULT: '#13211b',
          soft: '#3d4f47',
          muted: '#6b7d73',
        },
        line: '#e7e2d6',
      },
      maxWidth: {
        container: '1180px',
      },
      borderRadius: {
        xl2: '1.25rem',
        '4xl': '2rem',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(16,40,30,.04), 0 8px 30px -12px rgba(16,40,30,.12)',
        lift: '0 4px 12px rgba(16,40,30,.06), 0 24px 60px -20px rgba(16,40,30,.22)',
        glow: '0 0 0 1px rgba(21,160,107,.18), 0 20px 50px -16px rgba(21,160,107,.35)',
      },
      letterSpacing: {
        tightest: '-0.04em',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%,100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-soft': {
          '0%,100%': { opacity: '1' },
          '50%': { opacity: '.45' },
        },
      },
      animation: {
        'fade-up': 'fade-up .6s cubic-bezier(.21,.6,.35,1) both',
        float: 'float 6s ease-in-out infinite',
        shimmer: 'shimmer 2.2s linear infinite',
        'pulse-soft': 'pulse-soft 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
