// Runs before every frontend test file (npm test). Development only; never shipped.
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Remove whatever the previous test drew on the pretend page.
afterEach(() => {
  cleanup()
})
