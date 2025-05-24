module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    colors: {
      'primary-blue': '#2563eb',
      'primary-blue-dark': '#1d4ed8',
      'primary-blue-light': '#3b82f6',
      'success-green': '#10b981',
      'warning-orange': '#f59e0b',
      'error-red': '#ef4444',
      'info-cyan': '#06b6d4',
      'gray-50': '#f9fafb',
      'gray-100': '#f3f4f6',
      'gray-200': '#e5e7eb',
      'gray-500': '#6b7280',
      'gray-700': '#374151',
      'gray-900': '#111827',
      white: '#fff',
      transparent: 'transparent',
    },
    spacing: {
      '1': '0.25rem',
      '2': '0.5rem',
      '4': '1rem',
      '6': '1.5rem',
      '8': '2rem',
      '12': '3rem',
    },
    fontSize: {
      '4xl': ['2.25rem', { lineHeight: '2.5rem' }], // 36px
      '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
      '2xl': ['1.5rem', { lineHeight: '2rem' }], // 24px
      'xl': ['1.25rem', { lineHeight: '1.75rem' }], // 20px
      'base': ['1rem', { lineHeight: '1.5rem' }], // 16px
      'sm': ['0.875rem', { lineHeight: '1.25rem' }], // 14px
      'xs': ['0.75rem', { lineHeight: '1rem' }], // 12px
    },
    container: {
      center: true,
      screens: {
        sm: '640px',
        md: '768px',
        lg: '1024px',
        xl: '1280px',
        '2xl': '1536px',
      },
    },
    extend: {
      boxShadow: {
        'chat-float': '0 4px 12px rgba(37, 99, 235, 0.3)',
      },
      borderRadius: {
        'chat': '16px',
        'bubble': '18px',
      },
      keyframes: {
        pulse: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s infinite',
      },
    },
  },
  plugins: [],
};
