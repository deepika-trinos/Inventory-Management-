// Calls GET /health on the backend.
import apiClient from './client'

export async function getHealth() {
  // /health answers 503 when the database is down, but still sends a useful
  // body, so treat 200 and 503 both as "the server answered".
  const response = await apiClient.get('/health', {
    validateStatus: (status) => status === 200 || status === 503,
  })
  return response.data // { status: 'ok' | 'degraded', database: 'reachable' | 'unreachable' }
}
