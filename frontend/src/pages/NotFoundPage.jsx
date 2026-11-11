// Shown when the address in the browser doesn't match any page.
import { Link as RouterLink } from 'react-router'
import { Button, Paper, Stack, Typography } from '@mui/material'

export default function NotFoundPage() {
  return (
    <Paper sx={{ p: 4 }}>
      <Stack spacing={2} sx={{ alignItems: 'flex-start' }}>
        <Typography variant="h5" component="h1">
          Page not found
        </Typography>
        <Button component={RouterLink} to="/" variant="contained">
          Go to start page
        </Button>
      </Stack>
    </Paper>
  )
}
