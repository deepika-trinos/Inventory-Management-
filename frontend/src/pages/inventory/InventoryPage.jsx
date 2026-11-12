// Inventory page (Admin and IT Manager): items tracked BY QUANTITY (Slice 2.4, INV-01).
// List, search by name, filter by category and status; add and edit items;
// deactivate (after a confirm box) or activate them. No delete (BR-12).
// Quantity on hand is read-only (0 until stock is received in Slice 3.3).
// Slice 4.3 adds the low-stock flag and movement history to this page.
import { useCallback, useEffect, useState } from 'react'
import AddOutlined from '@mui/icons-material/AddOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import { Button, IconButton, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import { listCategories } from '../../api/categories'
import { getErrorMessage } from '../../api/errors'
import { listStockItems, setStockItemActive, unitLabel } from '../../api/stockItems'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import StatusBadge, { recordStatusLabel } from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import StockItemFormDialog from './StockItemFormDialog'

export default function InventoryPage() {
  const notify = useNotify()

  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [bulkCategories, setBulkCategories] = useState([])
  const [reloadKey, setReloadKey] = useState(0)
  const reload = () => setReloadKey((n) => n + 1)

  // Which dialog is open: { type: 'create' | 'edit' | 'active', item }
  const [dialog, setDialog] = useState(null)
  const close = () => setDialog(null)

  // Category filter: every category tracked by quantity (active or not).
  useEffect(() => {
    listCategories({ page: 1, pageSize: 100, sort: 'name', trackingType: 'bulk' })
      .then((data) => setBulkCategories(data.items))
      .catch(() => setBulkCategories([]))
  }, [reloadKey])

  const fetchRows = useCallback(
    (args) => listStockItems({ ...args, categoryId: categoryFilter, status: statusFilter }),
    [categoryFilter, statusFilter],
  )

  const toggleActive = async () => {
    const it = dialog.item
    const activate = it.status !== 'active'
    try {
      await setStockItemActive(it.id, activate)
      notify.success(`${it.name} ${activate ? 'activated' : 'deactivated'}.`)
      close()
      reload()
    } catch (error) {
      notify.error(getErrorMessage(error)) // box stays open so they can try again
    }
  }

  const columns = [
    { field: 'name', label: 'Item', sortable: true },
    { field: 'category', label: 'Category', sortable: true, render: (it) => it.category.name },
    { field: 'unit_of_measure', label: 'Unit', sortable: true, render: (it) => unitLabel(it.unit_of_measure) },
    { field: 'reorder_threshold', label: 'Reorder threshold', sortable: true, align: 'right' },
    {
      field: 'quantity_on_hand',
      label: 'On hand',
      sortable: true,
      align: 'right',
      render: (it) => (
        <Tooltip title="Read-only: changes only through receiving, issuing or adjusting stock">
          <span>{it.quantity_on_hand}</span>
        </Tooltip>
      ),
    },
    {
      field: 'status',
      label: 'Status',
      sortable: true,
      render: (it) => <StatusBadge status={recordStatusLabel(it.status)} />,
    },
    {
      field: 'actions',
      label: 'Actions',
      align: 'right',
      render: (it) => {
        const active = it.status === 'active'
        return (
          <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
            <Tooltip title="Edit">
              <IconButton size="small" aria-label={`Edit ${it.name}`} onClick={() => setDialog({ type: 'edit', item: it })}>
                <EditOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title={active ? 'Deactivate' : 'Activate'}>
              <IconButton
                size="small"
                aria-label={`${active ? 'Deactivate' : 'Activate'} ${it.name}`}
                color={active ? 'error' : 'success'}
                onClick={() => setDialog({ type: 'active', item: it })}
              >
                {active ? <BlockOutlined fontSize="small" /> : <CheckCircleOutline fontSize="small" />}
              </IconButton>
            </Tooltip>
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
        label="Category"
        value={categoryFilter}
        onChange={(e) => setCategoryFilter(e.target.value)}
        sx={{ minWidth: 170 }}
      >
        <MenuItem value="">All categories</MenuItem>
        {bulkCategories.map((c) => (
          <MenuItem key={c.id} value={c.id}>
            {c.name}
            {c.status !== 'active' ? ' (inactive)' : ''}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        select
        size="small"
        label="Status"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        sx={{ minWidth: 130 }}
      >
        <MenuItem value="">All</MenuItem>
        <MenuItem value="active">Active</MenuItem>
        <MenuItem value="inactive">Inactive</MenuItem>
      </TextField>
    </>
  )

  const target = dialog?.item
  const targetActive = target?.status === 'active'

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <div>
          <Typography variant="h5" component="h1">
            Inventory
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Items tracked by quantity, such as mice, keyboards and cables. Laptops and monitors are assets, not stock.
          </Typography>
        </div>
        <Button variant="contained" startIcon={<AddOutlined />} onClick={() => setDialog({ type: 'create' })}>
          Add stock item
        </Button>
      </Stack>

      <DataTable
        columns={columns}
        fetchRows={fetchRows}
        defaultSort="name"
        searchPlaceholder="Search item name"
        emptyTitle="No stock items yet"
        emptyMessage="Add one, e.g. USB mouse in a “By quantity” category."
        reloadKey={reloadKey}
        toolbar={filters}
      />

      {dialog?.type === 'create' || dialog?.type === 'edit' ? (
        <StockItemFormDialog
          open
          item={dialog.type === 'edit' ? target : null}
          onClose={close}
          onSaved={(saved, created) => {
            notify.success(created ? `${saved.name} added.` : `${saved.name} saved.`)
            close()
            reload()
          }}
        />
      ) : null}

      <ConfirmDialog
        open={dialog?.type === 'active'}
        title={targetActive ? `Deactivate ${target?.name}?` : `Activate ${target?.name ?? ''}?`}
        message={
          targetActive
            ? 'It can no longer be used for new purchases or stock issues. Nothing is deleted, and you can activate it again later. Items with stock left cannot be deactivated.'
            : 'It can be used for new purchases and stock issues again.'
        }
        confirmLabel={targetActive ? 'Deactivate' : 'Activate'}
        destructive={targetActive}
        onCancel={close}
        onConfirm={toggleActive}
      />
    </Stack>
  )
}
