// Calls to the backend's login endpoints (Slice 1.3, /api/v1/auth/...).
import apiClient from './client'

export async function loginRequest(email, password) {
  const { data } = await apiClient.post('/api/v1/auth/login', { email, password })
  return data // { access_token, token_type, expires_in }
}

export async function fetchCurrentUser() {
  const { data } = await apiClient.get('/api/v1/auth/me')
  return data // { id, email, role: {name}, employee: {full_name} | null, ... }
}

export async function logoutRequest() {
  await apiClient.post('/api/v1/auth/logout')
}
