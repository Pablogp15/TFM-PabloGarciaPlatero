import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// El proxy mantiene el mismo origen en desarrollo, requisito de las cookies
// HttpOnly con SameSite=Lax que usará la autenticación. Se usa 127.0.0.1 en
// lugar de localhost para no depender de la resolución IPv6 del sistema.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false,
      },
    },
  },
})
