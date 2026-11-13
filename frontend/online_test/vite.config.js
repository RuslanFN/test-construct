import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // Проксируем API на бэкенд, чтобы фронт и API были на одном origin.
    // Это критично для HttpOnly-кук (SameSite=Lax): cookie уходит как same-origin,
    // без CORS/credentials-нюансов и без Secure-требований по http.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8081',
        changeOrigin: true,
      },
    },
  },
})
