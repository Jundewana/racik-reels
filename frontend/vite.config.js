import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Saat `npm run dev`, permintaan /api dan /media diteruskan ke backend AutoReels (python main.py --web).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/media': 'http://127.0.0.1:8000'
    }
  },
  build: { outDir: 'dist', emptyOutDir: true }
});
