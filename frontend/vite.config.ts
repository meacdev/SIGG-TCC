import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': { target: env.API_PROXY_TARGET || 'http://127.0.0.1:5000', changeOrigin: true },
      },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.{ts,tsx}'],
      restoreMocks: true,
    },
  };
});
