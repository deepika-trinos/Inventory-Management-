// One shared Axios instance. Every call to the backend goes through here, so
// later (Slice 1.5) the login token is added in ONE place for all requests.
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  timeout: 10000, // milliseconds
})

export default apiClient
