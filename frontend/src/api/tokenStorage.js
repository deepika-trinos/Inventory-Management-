// Where the login token is kept in the browser.
//
// CHOICE: sessionStorage (one small box per browser tab).
//   + Survives a page refresh, so you stay logged in.
//   + Wiped automatically when the tab or browser is closed: safer on shared PCs.
//   + Simple: no extra server work.
//   - Like any storage JavaScript can read, a malicious script running in the
//     page (XSS) could read it. We limit that risk by: React escaping all text
//     by default, the token expiring after 30 minutes, and the server
//     re-checking the user on every request.
//   - A new tab needs its own login.
// Stronger option for later (Slice 8.3, security checks): an httpOnly cookie
// that JavaScript cannot read at all. That needs backend and CSRF changes.

const KEY = 'itam.accessToken'

export function getToken() {
  try {
    return window.sessionStorage.getItem(KEY)
  } catch {
    return null // storage blocked (e.g. strict privacy mode)
  }
}

export function setToken(token) {
  try {
    window.sessionStorage.setItem(KEY, token)
  } catch {
    /* storage blocked: the user stays logged in until the page reloads */
  }
}

export function clearToken() {
  try {
    window.sessionStorage.removeItem(KEY)
  } catch {
    /* nothing to clear */
  }
}
