// Shown when a logged-in user opens a page their role may not use
// (for example an Employee typing /assets into the address bar).
import { Link as RouterLink } from 'react-router'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import { Button, Paper, Stack, Typography } from '@mui/material'

import { useAuth } from '../context/AuthContext'
import { homePathFor } from '../routes/navigation'

export default function NotAllowedPage() {
  const { role } = useAuth()
  return (
    <Paper sx={{ p: 4 }}>
      <Stack spacing={2} sx={{ alignItems: 'flex-start' }}>
        <BlockOutlined color="error" sx={{ fontSize: 40 }} />
        <Typography variant="h5" component="h1">
          Not allowed
        </Typography>
        <Typography color="text.secondary">
          Your role ({role}) does not have access to this page.
        </Typography>
        <Button component={RouterLink} to={homePathFor(role)} variant="contained">
          Go to my home page
        </Button>
      </Stack>
    </Paper>
  )
}
