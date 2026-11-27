/** @type {import('tailwindcss').Config} */
// Warna memakai CSS variable (src/index.css) sehingga mode gelap cukup menukar nilai variabel.
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  darkMode: 'class', // App menambah/menghapus class "dark" di <html>
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        paper: v('paper'),
        surface: v('surface'),
        sunken: v('sunken'),
        ink: v('ink'),
        muted: v('muted'),
        line: v('line'),
        brand: v('brand'),
        'brand-soft': v('brand-soft'),
        'on-brand': v('on-brand'),
        go: v('go'),
        'go-text': v('go-text'),
        'on-go': v('on-go'),
        hook: v('hook'),
        'on-hook': v('on-hook'),
        stop: v('stop'),
        'stop-text': v('stop-text'),
        'on-stop': v('on-stop')
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'Segoe UI', 'sans-serif'],
        display: ['"Barlow Condensed"', '"Arial Narrow"', 'system-ui', 'sans-serif']
      }
    }
  },
  plugins: []
};
