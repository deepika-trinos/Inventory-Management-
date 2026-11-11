// App-wide settings read from frontend/.env (only VITE_ variables reach the browser).
// Nothing secret belongs here: everything in this file is visible to every visitor.

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// Company timezone used to DISPLAY dates (decision Q11). The server stores and
// sends UTC; screens convert. Keep this the same as APP_TIMEZONE in backend/.env.
export const APP_TIMEZONE = import.meta.env.VITE_APP_TIMEZONE ?? 'Asia/Kolkata'
