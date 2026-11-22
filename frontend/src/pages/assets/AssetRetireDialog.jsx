// Retire an asset (Slice 4.2, AST-07; owner's answer A3), opened from the asset page.
// A confirm box that says retiring cannot be undone and asks for the reason (required,
// up to 500 characters). Only Available or Damaged assets can be retired; the server
// checks that again. The reason is shown afterwards on the asset page and in its history.
import { useState } from 'react'
import { Alert, TextField } from '@mui/material'

import { retireAsset } from '../../api/assets'
import { getErrorMessage } from '../../api/errors'
import ConfirmDialog from '../../components/ConfirmDialog'

export const REASON_MAX = 500

export default function AssetRetireDialog({ open, asset, onClose, onRetired }) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const trimmed = reason.trim()
  const tooLong = trimmed.length > REASON_MAX

  const handleConfirm = async () => {
    if (!trimmed || tooLong) return
    setError('')
    try {
      const saved = await retireAsset(asset.asset_code, trimmed)
      onRetired(saved)
    } catch (err) {
      setError(getErrorMessage(err)) // box stays open so they can read it or try again
    }
  }

  return (
    <ConfirmDialog
      open={open}
      title={`Retire ${asset.asset_code}?`}
      message={`Retiring is permanent and cannot be undone: ${asset.asset_code} can no longer be edited or used again. Nothing is deleted; it stays in the register as Retired with this reason in its history.`}
      confirmLabel="Retire asset"
      destructive
      confirmDisabled={!trimmed || tooLong}
      onConfirm={handleConfirm}
      onCancel={onClose}
    >
      {error ? (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      ) : null}
      <TextField
        label="Reason for retiring"
        required
        autoFocus
        fullWidth
        multiline
        minRows={3}
        margin="normal"
        value={reason}
        onChange={(e) => {
          setReason(e.target.value)
          setError('')
        }}
        error={tooLong}
        helperText={tooLong ? `Use at most ${REASON_MAX} characters.` : `${trimmed.length} / ${REASON_MAX}`}
        placeholder="e.g. Screen cracked beyond repair; repair quote higher than replacement."
        slotProps={{ htmlInput: { maxLength: REASON_MAX + 50 } }}
      />
    </ConfirmDialog>
  )
}
