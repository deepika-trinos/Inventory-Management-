// Purchases page (Admin and IT Manager, Slice 3.1, PUR-01 to PUR-04, PUR-08).
// List and search purchases by reference number, vendor name or purchase number;
// filter by status and vendor. Create a draft, edit a draft, or cancel a draft
// (after a confirm box). Received and cancelled purchases open read-only.
// A draft or cancelled purchase never changes stock (PUR-08, BR-06). No delete (BR-12).
// Receive a draft (Slices 3.2-3.3): each one-by-one unit becomes an asset; each
// by-quantity line adds to stock.
// Purchase history (Slice 3.4, PUR-09): purchase-date range filter, received date column;
// the purchase number (or View) opens the detail page /purchases/:id.
// While a filter is set, an empty result says "No matches" (not "No purchases yet") and
// offers to clear the filters (D9, extended to Purchases at Phase 3 sign-off, D10). A
// "from" date after the "to" date is explained without a useless "Try again" button.
import { useCallback, useEffect, useState } from 'react'
import AddOutlined from '@mui/icons-material/AddOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import MoveToInboxOutlined from '@mui/icons-material/MoveToInboxOutlined'
import VisibilityOutlined from '@mui/icons-material/VisibilityOutlined'
import { useNavigate } from 'react-router'
import { Button, IconButton, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { cancelPurchase, listPurchases, PURCHASE_STATUSES } from '../../api/purchases'
import { listVendors } from '../../api/vendors'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import { useNotify } from '../../context/NotificationContext'
import { purchaseHistoryColumns, purchasePath } from './purchaseColumns'
import PurchaseFormDialog from './PurchaseFormDialog'
import ReceivePurchaseDialog from './ReceivePurchaseDialog'
import { receivedMessage } from './receiveForm'

export const CANCEL_PURCHASE_MESSAGE =
  'Cancelling is final: the purchase can no longer be edited or received. Nothing is deleted and no stock changes. Its invoice / reference number can be used again for this vendor.'

export default function PurchasesPage() {
  const notify = useNotify()
  const navigate = useNavigate()

  const [statusFilter, setStatusFilter] = useState('') // '', 'draft', 'received', 'cancelled'
  const [vendorFilter, setVendorFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('') // purchase date range, both days included ("YYYY-MM-DD")
  const [dateTo, setDateTo] = useState('')
  const badRange = Boolean(dateFrom && dateTo && dateFrom > dateTo)
  // While any filter is set: "No matches" for an empty result, with a button to clear (D9).
  const filtersActive = Boolean(statusFilter || vendorFilter || dateFrom || dateTo)
  const clearFilters = () => {
    setStatusFilter('')
    setVendorFilter('')
    setDateFrom('')
    setDateTo('')
  }
  const [vendors, setVendors] = useState([])
  const [reloadKey, setReloadKey] = useState(0)
  const reload = () => setReloadKey((n) => n + 1)

  // Which dialog is open: { type: 'create' | 'edit' | 'cancel' | 'receive', purchase }
  const [dialog, setDialog] = useState(null)
  const close = () => setDialog(null)

  // Vendor filter: every vendor, active or not (old purchases keep their vendor).
  useEffect(() => {
    listVendors({ page: 1, pageSize: 100, sort: 'name' })
      .then((data) => setVendors(data.items))
      .catch(() => setVendors([])) // the filter just stays empty; the list still works
  }, [])

  const fetchRows = useCallback(
    (args) => listPurchases({ ...args, status: statusFilter, vendorId: vendorFilter, dateFrom, dateTo }),
    [statusFilter, vendorFilter, dateFrom, dateTo],
  )

  const doCancel = async () => {
    const p = dialog.purchase
    try {
      await cancelPurchase(p.id)
      notify.success(`${p.purchase_number} cancelled.`)
      close()
      reload()
    } catch (error) {
      notify.error(getErrorMessage(error)) // box stays open so they can try again
    }
  }

  const columns = [
    ...purchaseHistoryColumns(),
    {
      field: 'actions',
      label: 'Actions',
      align: 'right',
      render: (p) => {
        const draft = p.status === 'draft'
        return (
          <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
            <Tooltip title="View details">
              <IconButton size="small" aria-label={`View ${p.purchase_number}`} onClick={() => navigate(purchasePath(p))}>
                <VisibilityOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            {draft ? (
              <Tooltip title="Edit">
                <IconButton
                  size="small"
                  aria-label={`Edit ${p.purchase_number}`}
                  onClick={() => setDialog({ type: 'edit', purchase: p })}
                >
                  <EditOutlined fontSize="small" />
                </IconButton>
              </Tooltip>
            ) : null}
            {draft ? (
              <Tooltip title="Receive">
                <IconButton
                  size="small"
                  color="primary"
                  aria-label={`Receive ${p.purchase_number}`}
                  onClick={() => setDialog({ type: 'receive', purchase: p })}
                >
                  <MoveToInboxOutlined fontSize="small" />
                </IconButton>
              </Tooltip>
            ) : null}
            {draft ? (
              <Tooltip title="Cancel purchase">
                <IconButton
                  size="small"
                  color="error"
                  aria-label={`Cancel ${p.purchase_number}`}
                  onClick={() => setDialog({ type: 'cancel', purchase: p })}
                >
                  <BlockOutlined fontSize="small" />
                </IconButton>
              </Tooltip>
            ) : null}
          </Stack>
        )
      },
    },
  ]

  const filters = (
    <>
      <TextField
        select
        size="small"
        label="Status"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        sx={{ minWidth: 140 }}
      >
        <MenuItem value="">All</MenuItem>
        {PURCHASE_STATUSES.map((s) => (
          <MenuItem key={s.value} value={s.value}>
            {s.label}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        select
        size="small"
        label="Vendor"
        value={vendorFilter}
        onChange={(e) => setVendorFilter(e.target.value)}
        sx={{ minWidth: 200 }}
      >
        <MenuItem value="">All vendors</MenuItem>
        {vendors.map((v) => (
          <MenuItem key={v.id} value={v.id}>
            {v.name}
            {v.status !== 'active' ? ' (inactive)' : ''}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        type="date"
        size="small"
        label="Purchase date from"
        value={dateFrom}
        onChange={(e) => setDateFrom(e.target.value)}
        slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: dateTo || undefined } }}
        sx={{ minWidth: 170 }}
      />
      <TextField
        type="date"
        size="small"
        label="to"
        value={dateTo}
        onChange={(e) => setDateTo(e.target.value)}
        error={badRange}
        helperText={badRange ? 'Must be on or after the “from” date.' : undefined}
        slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: dateFrom || undefined } }}
        sx={{ minWidth: 150 }}
      />
      {filtersActive ? (
        <Button size="small" onClick={clearFilters}>
          Clear filters
        </Button>
      ) : null}
    </>
  )

  const target = dialog?.purchase

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" component="h1">
          Purchases
        </Typography>
        <Button variant="contained" startIcon={<AddOutlined />} onClick={() => setDialog({ type: 'create' })}>
          New purchase
        </Button>
      </Stack>

      <DataTable
        columns={columns}
        fetchRows={fetchRows}
        defaultSort="-purchase_number"
        searchPlaceholder="Search reference, vendor or purchase no."
        emptyTitle="No purchases yet"
        emptyMessage="Create the first one with “New purchase”. It starts as a draft and changes no stock."
        reloadKey={reloadKey}
        toolbar={filters}
        filtersActive={filtersActive}
        onClearFilters={clearFilters}
        canRetry={(error) => getErrorCode(error) !== 'invalid_date_range'} // fixing the dates is the way out
      />

      {dialog?.type === 'create' || dialog?.type === 'edit' ? (
        <PurchaseFormDialog
          open
          purchaseId={dialog.type === 'edit' ? target.id : null}
          onClose={close}
          onSaved={(saved, created) => {
            notify.success(created ? `Draft ${saved.purchase_number} saved.` : `${saved.purchase_number} saved.`)
            close()
            reload()
          }}
          onReceive={(p) => setDialog({ type: 'receive', purchase: p })}
        />
      ) : null}

      {dialog?.type === 'receive' ? (
        <ReceivePurchaseDialog
          open
          purchaseId={target.id}
          onClose={close}
          onReceived={(saved) => {
            notify.success(receivedMessage(saved))
            close()
            reload()
          }}
        />
      ) : null}

      <ConfirmDialog
        open={dialog?.type === 'cancel'}
        title={`Cancel purchase ${target?.purchase_number ?? ''}?`}
        message={CANCEL_PURCHASE_MESSAGE}
        confirmLabel="Cancel purchase"
        cancelLabel="Keep draft"
        destructive
        onCancel={close}
        onConfirm={doCancel}
      />
    </Stack>
  )
}
