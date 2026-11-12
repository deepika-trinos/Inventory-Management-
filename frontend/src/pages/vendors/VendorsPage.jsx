// Vendors page (Admin and IT Manager, Slice 2.3, VEN-01 to VEN-03): list and
// search vendors by name, contact person, email or phone; filter by status;
// add and edit them; deactivate (after a confirm box) or activate them.
// Click a vendor's name to open its detail page (/vendors/:id).
// There is no delete: vendors are deactivated (BR-12, VEN-05).
import { useCallback, useState } from 'react'
import { Link as RouterLink } from 'react-router'
import AddOutlined from '@mui/icons-material/AddOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import { Button, IconButton, Link, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import { getErrorMessage } from '../../api/errors'
import { listVendors, setVendorActive } from '../../api/vendors'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import StatusBadge, { recordStatusLabel } from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import VendorFormDialog from './VendorFormDialog'

export const DEACTIVATE_VENDOR_MESSAGE =
  'New purchases can no longer be created from this vendor. Existing purchases keep it, and nothing is deleted. You can activate it again later.'

const dash = (
  <Typography variant="body2" color="text.secondary" component="span">
    —
  </Typography>
)

export default function VendorsPage() {
  const notify = useNotify()

  const [statusFilter, setStatusFilter] = useState('') // '', 'active', 'inactive'
  const [reloadKey, setReloadKey] = useState(0)
  const reload = () => setReloadKey((n) => n + 1)

  // Which dialog is open: { type: 'create' | 'edit' | 'active', vendor }
  const [dialog, setDialog] = useState(null)
  const close = () => setDialog(null)

  const fetchRows = useCallback((args) => listVendors({ ...args, status: statusFilter }), [statusFilter])

  const toggleActive = async () => {
    const v = dialog.vendor
    const activate = v.status !== 'active'
    try {
      await setVendorActive(v.id, activate)
      notify.success(`${v.name} ${activate ? 'activated' : 'deactivated'}.`)
      close()
      reload()
    } catch (error) {
      notify.error(getErrorMessage(error)) // box stays open so they can try again
    }
  }

  const columns = [
    {
      field: 'name',
      label: 'Vendor',
      sortable: true,
      render: (v) => (
        <Link component={RouterLink} to={`/vendors/${v.id}`} underline="hover">
          {v.name}
        </Link>
      ),
    },
    { field: 'contact_person', label: 'Contact person', sortable: true, render: (v) => v.contact_person || dash },
    { field: 'email', label: 'Email', sortable: true, render: (v) => v.email || dash },
    { field: 'phone', label: 'Phone', render: (v) => v.phone || dash },
    {
      field: 'status',
      label: 'Status',
      sortable: true,
      render: (v) => <StatusBadge status={recordStatusLabel(v.status)} />,
    },
    {
      field: 'actions',
      label: 'Actions',
      align: 'right',
      render: (v) => {
        const active = v.status === 'active'
        return (
          <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
            <Tooltip title="Edit">
              <IconButton size="small" aria-label={`Edit ${v.name}`} onClick={() => setDialog({ type: 'edit', vendor: v })}>
                <EditOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title={active ? 'Deactivate' : 'Activate'}>
              <IconButton
                size="small"
                aria-label={`${active ? 'Deactivate' : 'Activate'} ${v.name}`}
                color={active ? 'error' : 'success'}
                onClick={() => setDialog({ type: 'active', vendor: v })}
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
  )

  const target = dialog?.vendor
  const targetActive = target?.status === 'active'

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" component="h1">
          Vendors
        </Typography>
        <Button variant="contained" startIcon={<AddOutlined />} onClick={() => setDialog({ type: 'create' })}>
          Add vendor
        </Button>
      </Stack>

      <DataTable
        columns={columns}
        fetchRows={fetchRows}
        defaultSort="name"
        searchPlaceholder="Search name, contact, email or phone"
        emptyTitle="No vendors yet"
        emptyMessage="Add the first one with “Add vendor”."
        reloadKey={reloadKey}
        toolbar={filters}
      />

      {dialog?.type === 'create' || dialog?.type === 'edit' ? (
        <VendorFormDialog
          open
          vendor={dialog.type === 'edit' ? target : null}
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
        message={targetActive ? DEACTIVATE_VENDOR_MESSAGE : 'New purchases can be created from this vendor again.'}
        confirmLabel={targetActive ? 'Deactivate' : 'Activate'}
        destructive={targetActive}
        onCancel={close}
        onConfirm={toggleActive}
      />
    </Stack>
  )
}
