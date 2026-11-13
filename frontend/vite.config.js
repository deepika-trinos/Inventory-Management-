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
    // Form tests that click through MUI drop-downs take 5-7 s on a busy PC; the
    // 5 s default made them fail at random (B66).
    testTimeout: 15000,
  },
})
