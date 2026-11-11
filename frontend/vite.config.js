// Vite settings: how the React app is served during development and built for go-live.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,       // must match CORS_ORIGINS in backend/.env
    strictPort: true, // fail loudly instead of silently moving to another port
  },
})
