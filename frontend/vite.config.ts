import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000' } },
  preview: { proxy: { '/api': 'http://127.0.0.1:8000', '/health': 'http://127.0.0.1:8000' } },
  build: { rollupOptions: { output: { manualChunks(id) {
    if (!id.includes('node_modules')) return
    if (id.includes('recharts') || id.includes('/d3-') || id.includes('victory-vendor')) return 'charts'
    if (id.includes('@xyflow')) return 'workflow'
    if (id.includes('react-markdown') || id.includes('remark-') || id.includes('micromark') || id.includes('mdast-') || id.includes('hast-')) return 'markdown'
    return 'vendor'
  } } } }
})
