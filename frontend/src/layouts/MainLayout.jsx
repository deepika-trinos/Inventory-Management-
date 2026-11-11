// The frame around every logged-in page:
//   - top bar: menu button (small screens), app name, user's name and role, Log out
//   - sidebar: always visible on desktop; slides in from the left on tablet/phone
//   - the current page in the middle
import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router'
import LogoutOutlined from '@mui/icons-material/LogoutOutlined'
import MenuOutlined from '@mui/icons-material/MenuOutlined'
import {
  AppBar,
  Box,
  Button,
  Chip,
  Drawer,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'

import { displayName, useAuth } from '../context/AuthContext'
import Sidebar from './Sidebar'

const DRAWER_WIDTH = 240

export default function MainLayout() {
  const theme = useTheme()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md')) // md = 900px wide or more
  const [menuOpen, setMenuOpen] = useState(false)
  const { user, role, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'grey.50' }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar sx={{ gap: 1 }}>
          {!isDesktop ? (
            <IconButton color="inherit" edge="start" aria-label="Open menu" onClick={() => setMenuOpen(true)}>
              <MenuOutlined />
            </IconButton>
          ) : null}
          <Typography variant="h6" component="div" noWrap sx={{ flexGrow: 1 }}>
            IT Asset &amp; Inventory
          </Typography>

          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', minWidth: 0 }}>
            <Typography
              variant="body2"
              noWrap
              sx={{ display: { xs: 'none', sm: 'block' }, maxWidth: 220 }}
              title={user?.email}
            >
              {displayName(user)}
            </Typography>
            <Chip
              label={role}
              size="small"
              sx={{ bgcolor: 'rgba(255,255,255,0.18)', color: 'inherit' }}
            />
            {isDesktop ? (
              <Button color="inherit" startIcon={<LogoutOutlined />} onClick={handleLogout}>
                Log out
              </Button>
            ) : (
              <Tooltip title="Log out">
                <IconButton color="inherit" aria-label="Log out" onClick={handleLogout}>
                  <LogoutOutlined />
                </IconButton>
              </Tooltip>
            )}
          </Stack>
        </Toolbar>
      </AppBar>

      <Box component="aside" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        {isDesktop ? (
          <Drawer
            variant="permanent"
            open
            sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' } }}
          >
            <Sidebar />
          </Drawer>
        ) : (
          <Drawer
            variant="temporary"
            open={menuOpen}
            onClose={() => setMenuOpen(false)}
            ModalProps={{ keepMounted: true }}
            sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' } }}
          >
            <Sidebar onNavigate={() => setMenuOpen(false)} />
          </Drawer>
        )}
      </Box>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, sm: 3 } }}>
        <Toolbar /> {/* empty space under the top bar */}
        <Outlet />
      </Box>
    </Box>
  )
}
