// Login screen (PRD 13.1): email + password, required markers, validation
// messages, a clear error for wrong credentials, button disabled while waiting.
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import LockOutlined from '@mui/icons-material/LockOutlined'
import { Alert, Box, Button, CircularProgress, Paper, Stack, Typography } from '@mui/material'

import { getErrorMessage } from '../api/errors'
import FormField from '../components/FormField'
import { useAuth } from '../context/AuthContext'
import { canOpen, homePathFor } from '../routes/navigation'

const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

function validate({ email, password }) {
  const errors = {}
  if (!email.trim()) errors.email = 'Please enter your email.'
  else if (!EMAIL_SHAPE.test(email.trim())) errors.email = 'Please enter a valid email address.'
  if (!password) errors.password = 'Please enter your password.'
  return errors
}

export default function LoginPage() {
  const { status, role, login, sessionExpired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from

  const [values, setValues] = useState({ email: '', password: '' })
  const [fieldErrors, setFieldErrors] = useState({})
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Already logged in (e.g. pressed Back): go to the home page instead.
  if (status === 'authenticated' && !submitting) {
    return <Navigate to={homePathFor(role)} replace />
  }

  const handleChange = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }))
    setFieldErrors((e) => ({ ...e, [field]: '' }))
    setSubmitError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const errors = validate(values)
    setFieldErrors(errors)
    if (Object.keys(errors).length) return

    setSubmitting(true)
    setSubmitError('')
    try {
      const me = await login(values.email.trim(), values.password)
      const userRole = me.role.name
      // Back to the page they wanted, if their role may open it.
      const target = from && canOpen(userRole, from) ? from : homePathFor(userRole)
      navigate(target, { replace: true })
    } catch (error) {
      setSubmitError(getErrorMessage(error))
      setValues((v) => ({ ...v, password: '' }))
      setSubmitting(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'grey.100',
        p: 2,
      }}
    >
      <Paper sx={{ p: { xs: 3, sm: 4 }, width: '100%', maxWidth: 400 }} elevation={2}>
        <Stack spacing={1} sx={{ alignItems: 'center', mb: 2 }}>
          <LockOutlined color="primary" sx={{ fontSize: 36 }} />
          <Typography variant="h5" component="h1">
            Sign in
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center' }}>
            IT Asset &amp; Inventory Management
          </Typography>
        </Stack>

        {sessionExpired && !submitError ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Your session has ended. Please sign in again.
          </Alert>
        ) : null}
        {submitError ? (
          <Alert severity="error" sx={{ mb: 2 }} role="alert">
            {submitError}
          </Alert>
        ) : null}

        <Box component="form" onSubmit={handleSubmit} noValidate>
          <FormField
            label="Email"
            type="email"
            name="email"
            autoComplete="username"
            autoFocus
            required
            value={values.email}
            onChange={handleChange('email')}
            error={fieldErrors.email}
            disabled={submitting}
          />
          <FormField
            label="Password"
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={values.password}
            onChange={handleChange('password')}
            error={fieldErrors.password}
            disabled={submitting}
          />
          <Typography variant="caption" color="text.secondary" component="p" sx={{ mb: 2 }}>
            * Required
          </Typography>
          <Button
            type="submit"
            variant="contained"
            size="large"
            fullWidth
            disabled={submitting}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : null}
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
