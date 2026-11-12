// Employees page (Admin and IT Manager, Slice 2.2, EMP-01 to EMP-03): list and
// search employees by ID, name or department; filter by status and department;
// add and edit them; deactivate (after a confirm box) or activate them.
// There is no delete: employees are deactivated (BR-12). Deactivating also
// deactivates a linked login (decision B21). The server enforces every rule again.
import { useCallback, useEffect, useState } from 'react'
import AddOutlined from '@mui/icons-material/AddOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import { Box, Button, IconButton, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import { listDepartments, listEmployees, setEmployeeActive } from '../../api/employees'
import { getErrorMessage } from '../../api/errors'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import StatusBadge, { recordStatusLabel } from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import EmployeeFormDialog from './EmployeeFormDialog'

const dash = (
  <Typography variant="body2" color="text.secondary" component="span">
    —
  </Typography>
)

export default function EmployeesPage() {
  const notify = useNotify()

  // Filters
  const [statusFilter, setStatusFilter] = useState('') // '', 'active', 'inactive'
  const [departmentFilter, setDepartmentFilter] = useState('')
  const [departments, setDepartments] = useState([])
  const [reloadKey, setReloadKey] = useState(0)
  const reload = () => setReloadKey((n) => n + 1)

  // Which dialog is open: { type: 'create' | 'edit' | 'active', employee }
  const [dialog, setDialog] = useState(null)
  const close = () => setDialog(null)

  // Department filter choices: refreshed after every save (a new one may have been typed).
  useEffect(() => {
    listDepartments()
      .then(setDepartments)
      .catch(() => setDepartments([]))
  }, [reloadKey])

  const fetchRows = useCallback(
    (args) => listEmployees({ ...args, status: statusFilter, department: departmentFilter }),
    [statusFilter, departmentFilter],
  )

  const toggleActive = async () => {
    const e = dialog.employee
    const activate = e.status !== 'active'
    try {
      const saved = await setEmployeeActive(e.id, activate)
      const loginNote = !activate && e.user?.is_active && !saved.user?.is_active ? ' Their login was deactivated too.' : ''
      notify.success(`${e.full_name} ${activate ? 'activated' : 'deactivated'}.${loginNote}`)
      close()
      reload()
    } catch (error) {
      notify.error(getErrorMessage(error)) // box stays open so they can try again
    }
  }

  const columns = [
    { field: 'employee_code', label: 'Employee ID', sortable: true },
    {
      field: 'full_name',
      label: 'Name',
      sortable: true,
      render: (e) => (
        <Box>
          <Typography variant="body2">{e.full_name}</Typography>
          {e.work_email ? (
            <Typography variant="caption" color="text.secondary">
              {e.work_email}
            </Typography>
          ) : null}
        </Box>
      ),
    },
    { field: 'department', label: 'Department', sortable: true, render: (e) => e.department || dash },
    { field: 'designation', label: 'Designation', sortable: true, render: (e) => e.designation || dash },
    { field: 'phone', label: 'Phone', render: (e) => e.phone || dash },
    {
      field: 'user',
      label: 'Login',
      render: (e) =>
        e.user ? (
          <Tooltip title={e.user.is_active ? 'Active login' : 'Login deactivated'}>
            <Typography variant="body2" color={e.user.is_active ? 'text.primary' : 'text.secondary'}>
              {e.user.email}
            </Typography>
          </Tooltip>
        ) : (
          dash
        ),
    },
    {
      field: 'status',
      label: 'Status',
      sortable: true,
      render: (e) => <StatusBadge status={recordStatusLabel(e.status)} />,
    },
    {
      field: 'actions',
      label: 'Actions',
      align: 'right',
      render: (e) => {
        const active = e.status === 'active'
        return (
          <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
            <Tooltip title="Edit">
              <IconButton size="small" aria-label={`Edit ${e.full_name}`} onClick={() => setDialog({ type: 'edit', employee: e })}>
                <EditOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title={active ? 'Deactivate' : 'Activate'}>
              <IconButton
                size="small"
                aria-label={`${active ? 'Deactivate' : 'Activate'} ${e.full_name}`}
                color={active ? 'error' : 'success'}
                onClick={() => setDialog({ type: 'active', employee: e })}
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
        label="Department"
        value={departmentFilter}
        onChange={(e) => setDepartmentFilter(e.target.value)}
        sx={{ minWidth: 170 }}
      >
        <MenuItem value="">All departments</MenuItem>
        {departments.map((d) => (
          <MenuItem key={d} value={d}>
            {d}
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

  const target = dialog?.employee
  const targetActive = target?.status === 'active'
  const deactivateMessage = target?.user?.is_active
    ? `Their login (${target.user.email}) will be deactivated too, so they can no longer sign in. Nothing is deleted. Activating the employee later does not reactivate the login; an Admin does that on the Users page.`
    : 'Nothing is deleted. You can activate them again later.'

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" component="h1">
          Employees
        </Typography>
        <Button variant="contained" startIcon={<AddOutlined />} onClick={() => setDialog({ type: 'create' })}>
          Add employee
        </Button>
      </Stack>

      <DataTable
        columns={columns}
        fetchRows={fetchRows}
        defaultSort="full_name"
        searchPlaceholder="Search ID, name or department"
        emptyTitle="No employees yet"
        emptyMessage="Add the first one with “Add employee”."
        reloadKey={reloadKey}
        toolbar={filters}
      />

      {dialog?.type === 'create' || dialog?.type === 'edit' ? (
        <EmployeeFormDialog
          open
          employee={dialog.type === 'edit' ? target : null}
          onClose={close}
          onSaved={(saved, created) => {
            notify.success(created ? `${saved.full_name} added.` : `${saved.full_name} saved.`)
            close()
            reload()
          }}
        />
      ) : null}

      <ConfirmDialog
        open={dialog?.type === 'active'}
        title={targetActive ? `Deactivate ${target?.full_name}?` : `Activate ${target?.full_name ?? ''}?`}
        message={targetActive ? deactivateMessage : 'They can be chosen for new records again.'}
        confirmLabel={targetActive ? 'Deactivate' : 'Activate'}
        destructive={targetActive}
        onCancel={close}
        onConfirm={toggleActive}
      />
    </Stack>
  )
}
