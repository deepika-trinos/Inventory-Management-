// Gate for every page except /login: not logged in -> go to /login,
// remembering where the user wanted to go so we can bring them back after login.
//
// On every page change it also re-checks the session with the server, so a
// user who was deactivated is signed out on their next click, and a changed
// role shows the right menu immediately.
import { useEffect, useRef } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import LoadingState from '../components/LoadingState'
import { useAuth } from '../context/AuthContext'

export default function RequireAuth() {
  const { status, refreshUser } = useAuth()
  const location = useLocation()
  const firstPage = useRef(true)

  useEffect(() => {
    if (firstPage.current) {
      firstPage.current = false // the first page was just checked while loading
      return
    }
    if (status === 'authenticated') refreshUser()
  }, [location.pathname]) // only on page changes

  if (status === 'loading') {
    return <LoadingState message="Checking your session…" minHeight="100vh" />
  }
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
