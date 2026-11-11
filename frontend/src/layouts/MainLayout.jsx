// Page frame shared by every screen: a top bar plus the current page below it.
// Slice 1.5 adds the role-based sidebar menu here.
import { Outlet } from 'react-router'
import { AppBar, Box, Container, Toolbar, Typography } from '@mui/material'

export default function MainLayout() {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'grey.50' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div">
            IT Asset &amp; Inventory
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Outlet />
      </Container>
    </Box>
  )
}
