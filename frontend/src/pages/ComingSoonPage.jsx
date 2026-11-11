// Placeholder for menu pages that are not built yet. Says which slice builds it.
// The two dashboards also show whether the backend and database are reachable.
import { Paper, Stack, Typography } from '@mui/material'

import BackendStatus from '../components/BackendStatus'

export default function ComingSoonPage({ page }) {
  const { label, icon: Icon, slice, path } = page
  const isDashboard = path === '/dashboard' || path === '/my/dashboard'

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1">
        {label}
      </Typography>
      <Paper variant="outlined" sx={{ p: 4 }}>
        <Stack spacing={1} sx={{ alignItems: 'center', textAlign: 'center', color: 'text.secondary' }}>
          <Icon sx={{ fontSize: 48 }} />
          <Typography variant="h6" sx={{ color: 'text.primary' }}>
            Coming soon
          </Typography>
          <Typography variant="body2">This page will be built in {slice}.</Typography>
        </Stack>
      </Paper>
      {isDashboard ? <BackendStatus /> : null}
    </Stack>
  )
}
