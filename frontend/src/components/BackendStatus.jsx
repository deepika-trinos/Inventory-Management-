// Small reusable panel showing whether the backend and database are reachable.
import { useEffect, useState } from 'react'
import { Alert, CircularProgress, Stack } from '@mui/material'

import { getHealth } from '../api/health'

export default function BackendStatus() {
  const [state, setState] = useState({ loading: true, data: null, error: false })

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then((data) => !cancelled && setState({ loading: false, data, error: false }))
      .catch(() => !cancelled && setState({ loading: false, data: null, error: true }))
    return () => {
      cancelled = true
    }
  }, [])

  if (state.loading) {
    return (
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <CircularProgress size={18} />
        <span>Checking the backend…</span>
      </Stack>
    )
  }

  if (state.error) {
    return (
      <Alert severity="error">
        Cannot reach the backend. Is it running on {import.meta.env.VITE_API_BASE_URL}?
      </Alert>
    )
  }

  const ok = state.data.status === 'ok'
  return (
    <Alert severity={ok ? 'success' : 'warning'}>
      Backend: running · Database: {state.data.database}
    </Alert>
  )
}
