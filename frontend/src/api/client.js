// One shared Axios instance. EVERY call to the backend goes through here, so
// these rules apply everywhere automatically:
//   1. The backend address comes from frontend/.env (VITE_API_BASE_URL).
//   2. The login token is attached to every request.
//   3. If the server answers 401 ("not logged in / session expired"), the token
//      is cleared and the app is told, so it can send the user to /login.
import axios from 'axios'

import { API_BASE_URL } from '../config'
import { clearToken, getToken } from './tokenStorage'

export const SESSION_EXPIRED_EVENT = 'auth:session-expired'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // milliseconds
})

// Before each request: add "Authorization: Bearer <token>" if we have one.
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// After each response: react to 401 Unauthorized.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const isLoginCall = error.config?.url?.endsWith('/auth/login')
    // A 401 from the login form just means "wrong password": the form shows it.
    if (status === 401 && !isLoginCall && getToken()) {
      clearToken()
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT))
    }
    return Promise.reject(error)
  },
)

export default apiClient
