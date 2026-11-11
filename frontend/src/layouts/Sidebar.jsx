// The left menu. Shows only the pages the user's role may open (from navigation.js).
import { NavLink, useLocation } from 'react-router'
import { List, ListItemButton, ListItemIcon, ListItemText, Toolbar } from '@mui/material'

import { useAuth } from '../context/AuthContext'
import { pagesForRole } from '../routes/navigation'

export default function Sidebar({ onNavigate }) {
  const { role } = useAuth()
  const { pathname } = useLocation()

  return (
    <nav aria-label="Main menu">
      <Toolbar /> {/* empty space under the top bar */}
      <List dense>
        {pagesForRole(role).map(({ path, label, icon: Icon }) => (
          <ListItemButton
            key={path}
            component={NavLink}
            to={path}
            selected={pathname === path || pathname.startsWith(`${path}/`)}
            onClick={onNavigate}
            sx={{ mx: 1, borderRadius: 1 }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <Icon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary={label} />
          </ListItemButton>
        ))}
      </List>
    </nav>
  )
}
