// Start page for Slice 1.2: proves the React app runs and can talk to the backend.
import { Paper, Stack, Typography } from '@mui/material'

import BackendStatus from '../components/BackendStatus'

export default function HomePage() {
  return (
    <Paper sx={{ p: 4 }}>
      <Stack spacing={2}>
        <Typography variant="h4" component="h1">
          IT Asset &amp; Inventory Management System
        </Typography>
        <Typography color="text.secondary">
          Project setup is complete. Login and the main screens arrive in the next slices.
        </Typography>
        <BackendStatus />
      </Stack>
    </Paper>
  )
}
