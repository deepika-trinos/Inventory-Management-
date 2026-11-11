// Shows the page only if the user's role is in `roles`; otherwise "Not allowed".
// This is a courtesy for users. The real protection is the server's role check.
import { useAuth } from '../context/AuthContext'
import NotAllowedPage from '../pages/NotAllowedPage'

export default function RequireRole({ roles, children }) {
  const { role } = useAuth()
  return roles.includes(role) ? children : <NotAllowedPage />
}
