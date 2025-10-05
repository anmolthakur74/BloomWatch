/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#1a9850',
          dark: '#146c39',
          light: '#66bd63',
        }
      }
    },
  },
  plugins: [],
}


