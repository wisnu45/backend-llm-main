import path from 'path';
import react from '@vitejs/plugin-react-swc';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['showcase.under.my.id', 'localhost'] // Menambahkan hostname yang diizinkan
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
});
