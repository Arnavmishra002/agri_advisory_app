import { defineConfig, loadEnv } from 'vite';
import { resolve } from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, resolve(__dirname), '');
  const apiTarget = (env.VITE_API_BASE_URL || 'http://localhost:8000').replace(
    /\/$/,
    '',
  );

  return {
    root: resolve(__dirname),
    publicDir: resolve(__dirname, 'public'),
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
    },
  };
});
