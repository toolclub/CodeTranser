import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// docker compose 模式下,VITE_API_PROXY_TARGET=http://backend:8000(容器互通)
// 本地 npm run dev 模式下,默认走 127.0.0.1:8000
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000'
const wsTarget = apiTarget.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: wsTarget,
        ws: true,
      },
    },
    watch: {
      // docker mount 在 Mac/WSL2 下需要 polling 才能可靠触发热更新
      usePolling: true,
      interval: 300,
    },
  },
})
