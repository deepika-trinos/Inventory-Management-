// A small read-only view of one asset (Slice 3.2), opened from a received purchase's
// asset IDs. The full asset register and asset page (with history) come in Slice 4.1.
import { useEffect, useState } from 'react'
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Table, TableBody, TableCell, TableRow } from '@mui/material'

import { assetStatusLabel, getAsset } from '../../api/assets'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'

export default function AssetDetailsDialog({ open, assetRef, onClose }) {
  const [asset, setAsset] = useState(null)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    setAsset(null)
    setError(null)
    getAsset(assetRef)
      .then((found) => !cancelled && setAsset(found))
      .catch((err) => !cancelled && setError(err))
    return () => {
      cancelled = true
    }
  }, [assetRef, attempt])

  const rows = asset
    ? [
        ['Name', asset.name],
        ['Category', asset.category.name],
        ['Serial number', asset.serial_number],
        ['Model', asset.model],
        ['Brand', asset.brand || '—'],
        ['Location', asset.location || '—'],
        ['Warranty expiry', asset.warranty_expiry ? formatPlainDate(asset.warranty_expiry) : '—'],
        ['Purchase', asset.purchase ? `${asset.purchase.purchase_number} · ${asset.purchase.vendor} · ${asset.purchase.reference_number}` : '—'],
        ['Purchase date', asset.purchase_date ? formatPlainDate(asset.purchase_date) : '—'],
        ['Cost', asset.cost ? formatAmount(asset.cost) : '—'],
      ]
    : []

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <span>Asset {asset?.asset_code ?? assetRef}</span>
          {asset ? <StatusBadge status={assetStatusLabel(asset.status)} /> : null}
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        {error ? (
          <ErrorMessage error={error} onRetry={() => setAttempt((n) => n + 1)} />
        ) : !asset ? (
          <LoadingState message="Loading asset…" />
        ) : (
          <Table size="small" aria-label="Asset details">
            <TableBody>
              {rows.map(([label, value]) => (
                <TableRow key={label}>
                  <TableCell component="th" scope="row" sx={{ width: 160, color: 'text.secondary', border: 0 }}>
                    {label}
                  </TableCell>
                  <TableCell sx={{ border: 0 }}>{value}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}
