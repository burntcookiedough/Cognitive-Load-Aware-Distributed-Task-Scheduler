import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/cls':       { target: 'http://localhost:8001', changeOrigin: true, rewrite: p => p.replace(/^\/api\/cls/, '') },
      '/api/annotate':  { target: 'http://localhost:8002', changeOrigin: true, rewrite: p => p.replace(/^\/api\/annotate/, '') },
      '/api/scheduler': { target: 'http://localhost:8003', changeOrigin: true, rewrite: p => p.replace(/^\/api\/scheduler/, '') },
    },
  },
})
