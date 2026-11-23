// Stock item page: /inventory/:itemId (Admin and IT Manager, Slice 4.3, INV-02, INV-05, INV-06).
// Shows the item's details with its quantity on hand, reorder threshold and the "Low stock"
// badge (active and at or below the threshold, decisions B37, G1), and its full movement
// history: every receipt (and from Slice 4.4/4.5 every issue, adjustment and opening
// stock), newest saved first (G2), with type, change, balance after, business date,
// who saved it and when, the reason, and what caused it (a receipt links to its purchase).
// The existing Edit and Activate / Deactivate actions reuse the Inventory page's boxes.
// Slice 4.4 (INV-04; A4, A5, A4-5b): "Issue…" and "Adjust…" open StockChangeDialog (form,
// then a confirm box with the balance now and after); the page and history update after.
// Inactive items cannot be issued or adjusted (B38), so both are greyed out for them.
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import OutboxOutlined from '@mui/icons-material/OutboxOutlined'
import TuneOutlined from '@mui/icons-material/TuneOutlined'
import { Box, Button, Divider, Link, Paper, Stack, Tooltip, Typography } from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { movementTypeLabel } from '../../api/purchases'
import { getStockItem, getStockMovements, setStockItemActive, unitLabel } from '../../api/stockItems'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge, { recordStatusLabel } from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatDateTime, formatPlainDate } from '../../utils/dates'
import LowStockBadge from './LowStockBadge'
import StockChangeDialog from './StockChangeDialog'
import StockItemFormDialog from './StockItemFormDialog'

function Detail({ label, value, testId }) {
  return (
    <Box data-testid={testId}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1" component="div" sx={{ wordBreak: 'break-word' }}>
        {value === null || value === undefined || value === '' ? '—' : value}
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

/** "+10 pieces" / "−3 pieces" */
export function signedQuantity(movement, unit) {
  const sign = movement.direction === 'in' ? '+' : '−'
  return `${sign}${movement.quantity} ${unitLabel(unit).toLowerCase()}`
}

function referenceCell(m) {
  if (m.reference) {
    return (
      <Link component={RouterLink} to={`/purchases/${m.reference.purchase_id}`} underline="hover">
        {m.reference.purchase_number}
      </Link>
    )
  }
  if (m.issued_to) return `Issued to ${m.issued_to.full_name} (${m.issued_to.employee_code})`
  return '—'
}

function movementColumns(unit) {
  return [
    { field: 'movement_date', label: 'Date', render: (m) => formatPlainDate(m.movement_date) },
    { field: 'movement_type', label: 'Type', render: (m) => movementTypeLabel(m.movement_type) },
    { field: 'change', label: 'Change', align: 'right', render: (m) => signedQuantity(m, unit) },
    { field: 'balance_after', label: 'Balance after', align: 'right', render: (m) => `${m.balance_after} ${unitLabel(unit).toLowerCase()}` },
    { field: 'reference', label: 'Reference', render: referenceCell },
    { field: 'reason', label: 'Reason', render: (m) => m.reason || '—' },
    { field: 'created_at', label: 'Saved', render: (m) => `${formatDateTime(m.created_at)} · ${m.created_by.email}` },
  ]
}

function MovementHistory({ item, reloadKey }) {
  const fetchRows = useCallback((args) => getStockMovements(item.id, args), [item.id])
  return (
    <DataTable
      columns={movementColumns(item.unit_of_measure)}
      fetchRows={fetchRows}
      reloadKey={reloadKey}
      searchable={false}
      emptyTitle="No stock movements yet"
      emptyMessage="Receipts, issues and adjustments appear here (opening stock arrives with Slice 4.5)."
      pageSizeOptions={[10, 20, 50]}
    />
  )
}

export default function StockItemDetailPage() {
  const { itemId } = useParams()
  const notify = useNotify()
  const [item, setItem] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(null) // 'edit' | 'active' | 'issue' | 'adjust'
  const [historyKey, setHistoryKey] = useState(0)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getStockItem(itemId)
      .then(setItem)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [itemId])

  useEffect(load, [load])

  const backLink = (
    <Button component={RouterLink} to="/inventory" startIcon={<ArrowBackOutlined />} sx={{ alignSelf: 'flex-start' }}>
      All stock items
    </Button>
  )

  if (loading && !item) return <LoadingState message="Loading stock item…" />
  if (error) {
    const notFound = getErrorCode(error) === 'stock_item_not_found' || error?.response?.status === 422
    return (
      <Stack spacing={2}>
        {backLink}
        {notFound ? (
          <EmptyState title="Stock item not found" message="It may have been typed wrongly in the address." />
        ) : (
          <ErrorMessage error={error} onRetry={load} />
        )}
      </Stack>
    )
  }

  const active = item.status === 'active'
  const unit = unitLabel(item.unit_of_measure).toLowerCase()
  const close = () => setDialog(null)

  const toggleActive = async () => {
    try {
      const saved = await setStockItemActive(item.id, !active)
      notify.success(`${item.name} ${active ? 'deactivated' : 'activated'}.`)
      setItem(saved)
      close()
    } catch (err) {
      notify.error(getErrorMessage(err)) // box stays open so they can try again
    }
  }

  return (
    <Stack spacing={2}>
      {backLink}

      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
          <Typography variant="h5" component="h1">
            {item.name}
          </Typography>
          <StatusBadge status={recordStatusLabel(item.status)} />
          {item.low_stock ? <LowStockBadge /> : null}
        </Stack>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Tooltip title={active ? '' : 'Activate the item first.'}>
            <span>
              <Button variant="contained" startIcon={<OutboxOutlined />} disabled={!active} onClick={() => setDialog('issue')}>
                Issue…
              </Button>
            </span>
          </Tooltip>
          <Tooltip title={active ? '' : 'Activate the item first.'}>
            <span>
              <Button variant="outlined" startIcon={<TuneOutlined />} disabled={!active} onClick={() => setDialog('adjust')}>
                Adjust…
              </Button>
            </span>
          </Tooltip>
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

      <Section title="Details">
        <Box sx={grid}>
          <Detail label="Quantity on hand" testId="stock-on-hand" value={`${item.quantity_on_hand} ${unit}`} />
          <Detail label="Reorder threshold" testId="stock-threshold" value={`${item.reorder_threshold} ${unit}`} />
          <Detail
            label="Stock level"
            testId="stock-level"
            value={item.low_stock ? 'Low stock: at or below the reorder threshold' : active ? 'Above the reorder threshold' : 'Inactive (not checked)'}
          />
          <Detail label="Category" value={`${item.category.name}${item.category.status !== 'active' ? ' (inactive)' : ''}`} />
          <Detail label="Unit" value={unitLabel(item.unit_of_measure)} />
          <Detail label="Status" value={recordStatusLabel(item.status)} />
          <Detail label="Added" value={formatDateTime(item.created_at)} />
          <Detail label="Last changed" value={formatDateTime(item.updated_at)} />
        </Box>
      </Section>

      <Section title="Movement history">
        <MovementHistory item={item} reloadKey={historyKey} />
      </Section>

      {dialog === 'edit' ? (
        <StockItemFormDialog
          open
          item={item}
          onClose={close}
          onSaved={(saved) => {
            notify.success(`${saved.name} saved.`)
            setItem(saved)
            setHistoryKey((n) => n + 1)
            close()
          }}
        />
      ) : null}

      {dialog === 'issue' || dialog === 'adjust' ? (
        <StockChangeDialog
          open
          mode={dialog}
          item={item}
          onClose={close}
          onSaved={({ item: saved, movement }) => {
            const verb = movement.movement_type === 'issue' ? 'Issued' : movement.direction === 'in' ? 'Added' : 'Removed'
            notify.success(`${verb} ${movement.quantity} ${unit}. On hand now: ${saved.quantity_on_hand} ${unit}.`)
            setItem(saved)
            setHistoryKey((n) => n + 1)
            close()
          }}
        />
      ) : null}

      <ConfirmDialog
        open={dialog === 'active'}
        title={active ? `Deactivate ${item.name}?` : `Activate ${item.name}?`}
        message={
          active
            ? 'It can no longer be used for new purchases or stock issues. Nothing is deleted, and you can activate it again later. Items with stock left cannot be deactivated.'
            : 'It can be used for new purchases and stock issues again.'
        }
        confirmLabel={active ? 'Deactivate' : 'Activate'}
        destructive={active}
        onCancel={close}
        onConfirm={toggleActive}
      />
    </Stack>
  )
}
