import { defineConfig } from 'vite';

export default defineConfig({
  root: './frontend',
  server: {
    port: 5180,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8600',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
});
