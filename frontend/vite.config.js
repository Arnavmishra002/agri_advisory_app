import { defineConfig, loadEnv } from 'vite';
import { resolve } from 'path';
import { copyFileSync, mkdirSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

// Plugin: copy extra directories into dist after build
function copyDirPlugin(src, dest) {
  return {
    name: `copy-${dest}`,
    closeBundle() {
      function copyDir(from, to) {
        try {
          mkdirSync(to, { recursive: true });
          readdirSync(from).forEach(file => {
            const srcFile = join(from, file);
            const destFile = join(to, file);
            if (statSync(srcFile).isDirectory()) {
              copyDir(srcFile, destFile);
            } else {
              copyFileSync(srcFile, destFile);
            }
          });
          // Bug #9 fix: success log was OUTSIDE the try/catch, so it fired even
          // when copyDir() failed (e.g., missing css/ dir on fresh clone), producing
          // a misleading "✅ Copied" line immediately after a warning. Moved inside.
          console.log(`✅ Copied ${from} → ${to}`);
        } catch (e) {
          console.warn(`copyDirPlugin: could not copy ${from} → ${to}: ${e.message}`);
        }
      }
      copyDir(src, dest);
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, resolve(__dirname), '');
  // Use IPv4 explicitly: on macOS, localhost may resolve to ::1 and collide
  // with a Docker-published service while Django is listening on 127.0.0.1.
  const apiTarget = (env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

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
    plugins: [
      // Copy css/ directory into dist/css/ so styles.css is served
      copyDirPlugin(
        resolve(__dirname, 'css'),
        resolve(__dirname, 'dist', 'css')
      ),
    ],
  };
});
