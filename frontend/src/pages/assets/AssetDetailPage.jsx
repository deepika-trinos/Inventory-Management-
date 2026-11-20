// Asset page: /assets/:assetId (Admin and IT Manager, Slice 4.1, AST-02, AST-05).
// :assetId is the asset ID (AST-000007) or the id (7).
// Shows the asset's details, where it came from (its purchase, with links to the
// purchase and the vendor; "entered by hand" when there is none), who created it and
// when, and its full history: every audit log entry about the asset, newest first,
// paged on the server. Later slices add entries there automatically (4.2 edit /
// retire, 5.x assign / return, 6.x maintenance).
// Reading only: editing and retiring come in Slice 4.2.
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import { Box, Button, Divider, Link, Paper, Stack, Typography } from '@mui/material'

import { assetStatusLabel, getAsset, getAssetHistory, historyActionLabel } from '../../api/assets'
import { getErrorCode } from '../../api/errors'
import DataTable from '../../components/DataTable'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { formatDateTime, formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'

function Detail({ label, value, testId }) {
  return (
    <Box data-testid={testId}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1" component="div" sx={{ wordBreak: 'break-word' }}>
        {value || '—'}
      </Typography>
    </Box>
  )
}

function Section({ title, children }) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }} component="section" aria-label={title}>
      <Typography variant="h6" component="h2">
        {title}
      </Typography>
      <Divider sx={{ my: 1 }} />
      {children}
    </Paper>
  )
}

const grid = { display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' } }

// A short note under each history entry, from what the audit log recorded.
export function historyNote(entry) {
  const after = entry.after ?? {}
  if (entry.action === 'asset.created') {
    return after.purchase_number ? `Received on purchase ${after.purchase_number}` : 'Entered by hand'
  }
  if (after.reason) return `Reason: ${after.reason}`
  return ''
}

const HISTORY_COLUMNS = [
  { field: 'created_at', label: 'When', render: (e) => formatDateTime(e.created_at) },
  { field: 'action', label: 'What', render: (e) => historyActionLabel(e.action) },
  { field: 'actor', label: 'By', render: (e) => e.actor?.email ?? 'System' },
  { field: 'note', label: 'Details', render: (e) => historyNote(e) || '—' },
]

function AssetHistory({ assetRef }) {
  const fetchRows = useCallback((args) => getAssetHistory(assetRef, args), [assetRef])
  return (
    <DataTable
      columns={HISTORY_COLUMNS}
      fetchRows={fetchRows}
      searchable={false}
      emptyTitle="No history recorded"
      emptyMessage="Changes to this asset will be listed here."
      pageSizeOptions={[5, 10, 20]}
    />
  )
}

export default function AssetDetailPage() {
  const { assetId } = useParams()
  const [asset, setAsset] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getAsset(assetId)
      .then(setAsset)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [assetId])

  useEffect(load, [load])

  const backLink = (
    <Button component={RouterLink} to="/assets" startIcon={<ArrowBackOutlined />} sx={{ alignSelf: 'flex-start' }}>
      All assets
    </Button>
  )

  if (loading && !asset) return <LoadingState message="Loading asset…" />
  if (error) {
    const notFound = getErrorCode(error) === 'asset_not_found' || error?.response?.status === 422
    return (
      <Stack spacing={2}>
        {backLink}
        {notFound ? (
          <EmptyState title="Asset not found" message="It may have been typed wrongly in the address." />
        ) : (
          <ErrorMessage error={error} onRetry={load} />
        )}
      </Stack>
    )
  }

  const a = asset
  const purchase = a.purchase

  return (
    <Stack spacing={2}>
      {backLink}

      <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
        <Typography variant="h5" component="h1">
          Asset {a.asset_code}
        </Typography>
        <StatusBadge status={assetStatusLabel(a.status)} />
      </Stack>

      <Section title="Details">
        <Box sx={grid}>
          <Detail label="Name" value={a.name} />
          <Detail label="Category" value={`${a.category.name}${a.category.status !== 'active' ? ' (inactive)' : ''}`} />
          <Detail label="Serial number" value={a.serial_number} />
          <Detail label="Model" value={a.model} />
          <Detail label="Brand" value={a.brand} />
          <Detail label="Location" value={a.location} />
          <Detail label="Warranty expiry" value={a.warranty_expiry ? formatPlainDate(a.warranty_expiry) : null} />
          <Detail label="Status" value={assetStatusLabel(a.status)} />
          <Detail label="Created by" testId="asset-created-by" value={`${a.created_by.email} · ${formatDateTime(a.created_at)}`} />
        </Box>
      </Section>

      <Section title="Purchase">
        {purchase ? (
          <Box sx={grid}>
            <Detail
              label="Purchase"
              testId="asset-purchase"
              value={
                <Link component={RouterLink} to={`/purchases/${purchase.purchase_id}`} underline="hover">
                  {purchase.purchase_number}
                </Link>
              }
            />
            <Detail
              label="Vendor"
              value={
                <Link component={RouterLink} to={`/vendors/${purchase.vendor_id}`} underline="hover">
                  {purchase.vendor}
                </Link>
              }
            />
            <Detail label="Invoice / reference no." value={purchase.reference_number} />
            <Detail label="Purchase date" value={a.purchase_date ? formatPlainDate(a.purchase_date) : null} />
            <Detail label="Cost" value={a.cost ? formatAmount(a.cost) : null} />
          </Box>
        ) : (
          <EmptyState title="No purchase" message="This asset was entered by hand, not received on a purchase." />
        )}
      </Section>

      <Section title="History">
        <AssetHistory assetRef={a.asset_code} />
      </Section>
    </Stack>
  )
}
