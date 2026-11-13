// Vite settings: how the React app is served during development and built for go-live.
// The "test" part is read by Vitest (npm test, decision T1); it is never part of the build.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,       // must match CORS_ORIGINS in backend/.env
    strictPort: true, // fail loudly instead of silently moving to another port
  },
  test: {
    environment: 'jsdom', // a pretend browser page, so screens can be rendered in tests
    include: ['src/**/*.test.{js,jsx}'],
    setupFiles: ['src/test/setup.js'],
    env: { VITE_APP_TIMEZONE: 'Asia/Kolkata' },
  },
})
