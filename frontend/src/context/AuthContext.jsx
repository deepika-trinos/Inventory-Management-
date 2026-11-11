// Who is logged in? Shared with every screen through React "context"
// (a way to make data available everywhere without passing it down by hand).
//
// Provides:
//   status : 'loading' (checking a saved token) | 'authenticated' | 'anonymous'
//   user   : the /auth/me answer (email, role, linked employee)
//   role   : shortcut for user.role.name
//   login(email, password), logout(), refreshUser()
//   sessionExpired : true when the server ended the session (token expired)
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { fetchCurrentUser, loginRequest, logoutRequest } from '../api/auth'
import { SESSION_EXPIRED_EVENT } from '../api/client'
import { clearToken, getToken, setToken } from '../api/tokenStorage'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(getToken() ? 'loading' : 'anonymous')
  const [sessionExpired, setSessionExpired] = useState(false)

  // On page load/refresh: if a token was saved, ask the server who it belongs to.
  useEffect(() => {
    if (!getToken()) return
    let cancelled = false
    fetchCurrentUser()
      .then((me) => {
        if (cancelled) return
        setUser(me)
        setStatus('authenticated')
      })
      .catch(() => {
        if (cancelled) return
        clearToken()
        setUser(null)
        setStatus('anonymous')
      })
    return () => {
      cancelled = true
    }
  }, [])

  // The API client fires this when the server answers 401 to a logged-in call.
  useEffect(() => {
    const onExpired = () => {
      setUser(null)
      setStatus('anonymous')
      setSessionExpired(true)
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired)
  }, [])

  const login = useCallback(async (email, password) => {
    const { access_token: token } = await loginRequest(email, password)
    setToken(token)
    try {
      const me = await fetchCurrentUser()
      setUser(me)
      setStatus('authenticated')
      setSessionExpired(false)
      return me
    } catch (error) {
      clearToken()
      throw error
    }
  }, [])

  // Ask the server again who we are (e.g. on every page change). If the user was
  // deactivated, the server answers 401 and the API client ends the session; if
  // their role changed, the menu updates straight away.
  const refreshUser = useCallback(async () => {
    if (!getToken()) return
    try {
      setUser(await fetchCurrentUser())
    } catch {
      /* 401 is handled by the session-expired event; other errors: keep going */
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutRequest() // tell the server (optional with JWT, see backend docs)
    } catch {
      /* already expired or offline: logging out locally is what matters */
    }
    clearToken()
    setUser(null)
    setStatus('anonymous')
    setSessionExpired(false)
  }, [])

  const value = useMemo(
    () => ({
      user,
      role: user?.role?.name ?? null,
      status,
      sessionExpired,
      login,
      logout,
      refreshUser,
    }),
    [user, status, sessionExpired, login, logout, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}

// Name to show in the top bar: the linked employee's name, else the email.
export function displayName(user) {
  return user?.employee?.full_name || user?.email || ''
}
