// Red box explaining what went wrong, with an optional "Try again" button.
// Pass either `error` (a failed request: turned into a readable sentence) or `message`.
import { Alert, Button } from '@mui/material'

import { getErrorMessage } from '../api/errors'

export default function ErrorMessage({ error, message, onRetry, title }) {
  const text = message ?? getErrorMessage(error)
  return (
    <Alert
      severity="error"
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Try again
          </Button>
        ) : null
      }
    >
      {title ? <strong>{title} </strong> : null}
      {text}
    </Alert>
  )
}
