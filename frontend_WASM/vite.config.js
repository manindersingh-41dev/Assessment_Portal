import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const runtimeAssetDirectory = resolve('public/clang')
const runtimeAssetVersions = readdirSync(runtimeAssetDirectory, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && /^runtime-[a-f0-9]{20}$/.test(entry.name))
  .map((entry) => entry.name)

if (runtimeAssetVersions.length !== 1) {
  throw new Error('Expected exactly one generated, content-versioned Clang runtime asset directory.')
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_WASM_RUNTIME_ASSET_VERSION': JSON.stringify(runtimeAssetVersions[0]),
  },
  server: {
    host: '0.0.0.0',
    https: false,
    port: 3000,
    open: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api'),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: false,
  },
})
