// "Are you sure?" box for consequential actions (PRD section 13), such as
// receiving a purchase, assigning or retiring an asset, or adjusting stock.
//
//   <ConfirmDialog
//     open={open}
//     title="Retire this asset?"
//     message="This cannot be undone."
//     confirmLabel="Retire"
//     destructive                      // red button for risky actions
//     onConfirm={async () => {...}}    // may be async; buttons are disabled while it runs
//     onCancel={() => setOpen(false)}
//   />
import { useState } from 'react'
import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material'

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
}) {
  const [busy, setBusy] = useState(false)

  const handleConfirm = async () => {
    setBusy(true)
    try {
      await onConfirm?.()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      {message ? (
        <DialogContent>
          <DialogContentText>{message}</DialogContentText>
        </DialogContent>
      ) : null}
      <DialogActions>
        <Button onClick={onCancel} disabled={busy}>
          {cancelLabel}
        </Button>
        <Button
          onClick={handleConfirm}
          disabled={busy}
          variant="contained"
          color={destructive ? 'error' : 'primary'}
          startIcon={busy ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
