// Categories page (Admin and IT Manager, Slice 2.1, AST-02): list, search and
// filter asset categories; add and edit them; deactivate (after a confirm box)
// or activate them. There is no delete: categories are deactivated (BR-12).
// The server enforces every rule again (roles, unique names, tracking-type lock).
import { useCallback, useState } from 'react'
import AddOutlined from '@mui/icons-material/AddOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import { Button, IconButton, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import { listCategories, setCategoryActive, TRACKING_TYPES, trackingTypeLabel } from '../../api/categories'
import { getErrorMessage } from '../../api/errors'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import StatusBadge, { recordStatusLabel } from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatDateTime } from '../../utils/dates'
import CategoryFormDialog from './CategoryFormDialog'

export default function CategoriesPage() {
  const notify = useNotify()

  // Filters
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('') // '', 'active', 'inactive'
  const [reloadKey, setReloadKey] = useState(0)
  const reload = () => setReloadKey((n) => n + 1)

  // Which dialog is open: { type: 'create' | 'edit' | 'active', category }
  const [dialog, setDialog] = useState(null)
  const close = () => setDialog(null)

  const fetchRows = useCallback(
    (args) => listCategories({ ...args, trackingType: typeFilter, status: statusFilter }),
    [typeFilter, statusFilter],
  )

  const toggleActive = async () => {
    const c = dialog.category
    const activate = c.status !== 'active'
    try {
      await setCategoryActive(c.id, activate)
      notify.success(`Category ${c.name} ${activate ? 'activated' : 'deactivated'}.`)
      close()
      reload()
    } catch (error) {
      notify.error(getErrorMessage(error)) // box stays open so they can try again
    }
  }

  const columns = [
    { field: 'name', label: 'Name', sortable: true },
    {
      field: 'description',
      label: 'Description',
      render: (c) =>
        c.description ? (
          c.description
        ) : (
          <Typography variant="body2" color="text.secondary">
            —
          </Typography>
        ),
    },
    { field: 'tracking_type', label: 'Tracking', sortable: true, render: (c) => trackingTypeLabel(c.tracking_type) },
    {
      field: 'status',
      label: 'Status',
      sortable: true,
      render: (c) => <StatusBadge status={recordStatusLabel(c.status)} />,
    },
    { field: 'updated_at', label: 'Last changed', sortable: true, render: (c) => formatDateTime(c.updated_at) },
    {
      field: 'actions',
      label: 'Actions',
      align: 'right',
      render: (c) => {
        const active = c.status === 'active'
        return (
          <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
            <Tooltip title="Edit">
              <IconButton size="small" aria-label={`Edit ${c.name}`} onClick={() => setDialog({ type: 'edit', category: c })}>
                <EditOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title={active ? 'Deactivate' : 'Activate'}>
              <IconButton
                size="small"
                aria-label={`${active ? 'Deactivate' : 'Activate'} ${c.name}`}
                color={active ? 'error' : 'success'}
                onClick={() => setDialog({ type: 'active', category: c })}
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
        label="Tracking"
        value={typeFilter}
        onChange={(e) => setTypeFilter(e.target.value)}
        sx={{ minWidth: 150 }}
      >
        <MenuItem value="">All</MenuItem>
        {TRACKING_TYPES.map((t) => (
          <MenuItem key={t.value} value={t.value}>
            {t.label}
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

  const target = dialog?.category
  const targetActive = target?.status === 'active'

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" component="h1">
          Categories
        </Typography>
        <Button variant="contained" startIcon={<AddOutlined />} onClick={() => setDialog({ type: 'create' })}>
          Add category
        </Button>
      </Stack>

      <DataTable
        columns={columns}
        fetchRows={fetchRows}
        defaultSort="name"
        searchPlaceholder="Search category name"
        emptyTitle="No categories yet"
        emptyMessage="Add one, e.g. Laptops (one-by-one) or Mice (by quantity)."
        reloadKey={reloadKey}
        toolbar={filters}
      />

      {dialog?.type === 'create' || dialog?.type === 'edit' ? (
        <CategoryFormDialog
          open
          category={dialog.type === 'edit' ? target : null}
          onClose={close}
          onSaved={(saved, created) => {
            notify.success(created ? `Category ${saved.name} added.` : `Category ${saved.name} saved.`)
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
            ? 'It can no longer be chosen for new items or assets. Existing records keep it, and nothing is deleted. You can activate it again later.'
            : 'It can be chosen for new items and assets again.'
        }
        confirmLabel={targetActive ? 'Deactivate' : 'Activate'}
        destructive={targetActive}
        onCancel={close}
        onConfirm={toggleActive}
      />
    </Stack>
  )
}
