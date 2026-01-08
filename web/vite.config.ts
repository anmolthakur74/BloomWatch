import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default ({ mode }) => {
  // Load .env files based on the current mode (development, production)
  const env = loadEnv(mode, process.cwd(), '')

  return defineConfig({
    plugins: [react()],
    server: {
      port: 5173,
      open: true,
      proxy: {
        // Optional: proxy API requests to backend locally
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  })
}
