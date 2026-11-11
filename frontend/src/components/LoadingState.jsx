// "Loading..." with a spinner, shown while data is on its way.
import { CircularProgress, Stack, Typography } from '@mui/material'

export default function LoadingState({ message = 'Loading…', minHeight = 160 }) {
  return (
    <Stack
      role="status"
      spacing={2}
      sx={{ alignItems: 'center', justifyContent: 'center', minHeight, color: 'text.secondary' }}
    >
      <CircularProgress size={32} />
      <Typography variant="body2">{message}</Typography>
    </Stack>
  )
}
