// Vendor detail page: /vendors/:vendorId (Admin and IT Manager, Slice 2.3, VEN-01).
// Shows the vendor's details with Edit and Activate/Deactivate actions.
// The "Purchase history" section is a placeholder: Slice 3.4 (VEN-04) fills it in.
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import { Box, Button, Divider, Paper, Stack, Typography } from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { getVendor, setVendorActive } from '../../api/vendors'
import ConfirmDialog from '../../components/ConfirmDialog'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge, { recordStatusLabel } from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatDateTime } from '../../utils/dates'
import VendorFormDialog from './VendorFormDialog'
import { DEACTIVATE_VENDOR_MESSAGE } from './VendorsPage'

function Detail({ label, value }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1" sx={{ whiteSpace: 'pre-line', wordBreak: 'break-word' }}>
        {value || '—'}
      </Typography>
    </Box>
  )
}

export default function VendorDetailPage() {
  const { vendorId } = useParams()
  const notify = useNotify()
  const [vendor, setVendor] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(null) // 'edit' | 'active'

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getVendor(vendorId)
      .then(setVendor)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [vendorId])

  useEffect(load, [load])

  const backLink = (
    <Button component={RouterLink} to="/vendors" startIcon={<ArrowBackOutlined />} sx={{ alignSelf: 'flex-start' }}>
      All vendors
    </Button>
  )

  if (loading && !vendor) return <LoadingState />
  if (error) {
    const notFound = getErrorCode(error) === 'vendor_not_found' || error?.response?.status === 422
    return (
      <Stack spacing={2}>
        {backLink}
        {notFound ? (
          <EmptyState title="Vendor not found" message="It may have been typed wrongly in the address." />
        ) : (
          <ErrorMessage error={error} onRetry={load} />
        )}
      </Stack>
    )
  }

  const active = vendor.status === 'active'

  const toggleActive = async () => {
    try {
      const saved = await setVendorActive(vendor.id, !active)
      setVendor(saved)
      notify.success(`${saved.name} ${active ? 'deactivated' : 'activated'}.`)
      setDialog(null)
    } catch (err) {
      notify.error(getErrorMessage(err))
    }
  }

  return (
    <Stack spacing={2}>
      {backLink}

      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <Typography variant="h5" component="h1">
            {vendor.name}
          </Typography>
          <StatusBadge status={recordStatusLabel(vendor.status)} />
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<EditOutlined />} onClick={() => setDialog('edit')}>
            Edit
          </Button>
          <Button
            variant="outlined"
            color={active ? 'error' : 'success'}
            startIcon={active ? <BlockOutlined /> : <CheckCircleOutline />}
            onClick={() => setDialog('active')}
          >
            {active ? 'Deactivate' : 'Activate'}
          </Button>
        </Stack>
      </Stack>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' } }}>
          <Detail label="Contact person" value={vendor.contact_person} />
          <Detail label="Email" value={vendor.email} />
          <Detail label="Phone" value={vendor.phone} />
          <Detail label="Address" value={vendor.address} />
          <Detail label="Added" value={formatDateTime(vendor.created_at)} />
          <Detail label="Last changed" value={formatDateTime(vendor.updated_at)} />
        </Box>
      </Paper>

      {/* ---- PLACEHOLDER: Purchase history (Slice 3.4, VEN-04) ----------------------------
          Slice 3.4 replaces this box with the list of this vendor's purchases
          (purchase reference, date, status, total), newest first. */}
      <Paper variant="outlined" sx={{ p: 2 }} data-testid="vendor-purchase-history">
        <Typography variant="h6" component="h2">
          Purchase history
        </Typography>
        <Divider sx={{ my: 1 }} />
        <EmptyState
          title="Coming in Slice 3.4"
          message="Purchases from this vendor will be listed here once purchases are built."
        />
      </Paper>

      {dialog === 'edit' ? (
        <VendorFormDialog
          open
          vendor={vendor}
          onClose={() => setDialog(null)}
          onSaved={(saved) => {
            setVendor(saved)
            notify.success(`${saved.name} saved.`)
            setDialog(null)
          }}
        />
      ) : null}

      <ConfirmDialog
        open={dialog === 'active'}
        title={active ? `Deactivate ${vendor.name}?` : `Activate ${vendor.name}?`}
        message={active ? DEACTIVATE_VENDOR_MESSAGE : 'New purchases can be created from this vendor again.'}
        confirmLabel={active ? 'Deactivate' : 'Activate'}
        destructive={active}
        onCancel={() => setDialog(null)}
        onConfirm={toggleActive}
      />
    </Stack>
  )
}
