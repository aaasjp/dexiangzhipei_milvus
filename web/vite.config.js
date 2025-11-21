import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 8080,
    proxy: {
      '/vector_db_service': {
        target: 'http://localhost:8005',
        changeOrigin: true
      },
      '/chat_service': {
        target: 'http://localhost:8006',
        changeOrigin: true
      }
    }
  }
})

