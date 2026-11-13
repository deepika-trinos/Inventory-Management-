// Purchases page (Admin and IT Manager, Slice 3.1, PUR-01 to PUR-04, PUR-08).
// List and search purchases by reference number, vendor name or purchase number;
// filter by status and vendor. Create a draft, edit a draft, or cancel a draft
// (after a confirm box). Received and cancelled purchases open read-only.
// A draft or cancelled purchase never changes stock (PUR-08, BR-06). No delete (BR-12).
// Receive a draft of one-by-one items (Slice 3.2): each unit becomes an asset.
// By-quantity receiving arrives in Slice 3.3; the full history screens in Slice 3.4.
import { useCallback, useEffect, useState } from 'react'
import AddOutlined from '@mui/icons-material/AddOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import MoveToInboxOutlined from '@mui/icons-material/MoveToInboxOutlined'
import VisibilityOutlined from '@mui/icons-material/VisibilityOutlined'
import { Button, IconButton, Link, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import { getErrorMessage } from '../../api/errors'
import { cancelPurchase, listPurchases, PURCHASE_STATUSES, purchaseStatusLabel } from '../../api/purchases'
import { listVendors } from '../../api/vendors'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'
import PurchaseFormDialog from './PurchaseFormDialog'
import ReceivePurchaseDialog from './ReceivePurchaseDialog'
import { receivedMessage } from './receiveForm'

export const CANCEL_PURCHASE_MESSAGE =
  'Cancelling is final: the purchase can no longer be edited or received. Nothing is deleted and no stock changes. Its invoice / reference number can be used again for this vendor.'

export default function PurchasesPage() {
  const notify = useNotify()

  const [statusFilter, setStatusFilter] = useState('') // '', 'draft', 'received', 'cancelled'
  const [vendorFilter, setVendorFilter] = useState('')
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
    (args) => listPurchases({ ...args, status: statusFilter, vendorId: vendorFilter }),
    [statusFilter, vendorFilter],
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
    {
      field: 'purchase_number',
      label: 'Purchase no.',
      sortable: true,
      render: (p) => (
        <Link
          component="button"
          type="button"
          underline="hover"
          onClick={() => setDialog({ type: 'edit', purchase: p })}
          sx={{ verticalAlign: 'baseline' }}
        >
          {p.purchase_number}
        </Link>
      ),
    },
    { field: 'vendor', label: 'Vendor', sortable: true, render: (p) => p.vendor.name },
    { field: 'reference_number', label: 'Invoice / ref.', sortable: true },
    { field: 'purchase_date', label: 'Date', sortable: true, render: (p) => formatPlainDate(p.purchase_date) },
    { field: 'line_count', label: 'Lines', align: 'right' },
    { field: 'total_amount', label: 'Total', align: 'right', render: (p) => formatAmount(p.total_amount) },
    {
      field: 'status',
      label: 'Status',
      sortable: true,
      render: (p) => <StatusBadge status={purchaseStatusLabel(p.status)} />,
    },
    {
      field: 'actions',
      label: 'Actions',
      align: 'right',
      render: (p) => {
        const draft = p.status === 'draft'
        return (
          <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
            <Tooltip title={draft ? 'Edit' : 'View'}>
              <IconButton
                size="small"
                aria-label={`${draft ? 'Edit' : 'View'} ${p.purchase_number}`}
                onClick={() => setDialog({ type: 'edit', purchase: p })}
              >
                {draft ? <EditOutlined fontSize="small" /> : <VisibilityOutlined fontSize="small" />}
              </IconButton>
            </Tooltip>
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
