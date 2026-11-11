// Gate for every page except /login: not logged in -> go to /login,
// remembering where the user wanted to go so we can bring them back after login.
import { Navigate, Outlet, useLocation } from 'react-router'

import LoadingState from '../components/LoadingState'
import { useAuth } from '../context/AuthContext'

export default function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <LoadingState message="Checking your session…" minHeight="100vh" />
  }
  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
