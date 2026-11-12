// Users page (Admin only, AUTH-05): list, search and filter users; create and
// edit them; change role and activate/deactivate, each after a confirm box.
// Slice 2.2: Employee logins must be linked to an employee record. Old unlinked
// ones (R3) are flagged "Needs employee link"; changing a role to Employee asks
// for the employee when the user has none.
// The server enforces every rule again (Admin only, not yourself, last Admin, link).
import { useCallback, useState } from 'react'
import AddOutlined from '@mui/icons-material/AddOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import CheckCircleOutline from '@mui/icons-material/CheckCircleOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import ManageAccountsOutlined from '@mui/icons-material/ManageAccountsOutlined'
import { Box, Button, Chip, IconButton, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import { getErrorMessage } from '../../api/errors'
import { changeUserRole, listUsers, setUserActive } from '../../api/users'
import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import { useAuth } from '../../context/AuthContext'
import { useNotify } from '../../context/NotificationContext'
import EmployeePicker from '../../components/EmployeePicker'
import { ROLES } from '../../routes/navigation'
import { formatDateTime } from '../../utils/dates'
import UserFormDialog from './UserFormDialog'

const SELF_HINT = 'You cannot change your own role or status. Ask another Admin.'

export default function UsersPage() {
  const { user: me } = useAuth()
  const notify = useNotify()

  // Filters
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('') // '', 'true', 'false'
  const [reloadKey, setReloadKey] = useState(0)
  const reload = () => setReloadKey((n) => n + 1)

  // Which dialog is open: { type: 'create' | 'edit' | 'role' | 'active', user }
  const [dialog, setDialog] = useState(null)
  const [newRole, setNewRole] = useState('')
  const [roleEmployee, setRoleEmployee] = useState(null) // employee to link when changing to Employee
  const close = () => setDialog(null)

  const fetchRows = useCallback(
    (args) => listUsers({ ...args, role: roleFilter, isActive: statusFilter }),
    [roleFilter, statusFilter],
  )

  // Runs the action, shows a message, refreshes the list. Errors keep the box open.
  const runAction = async (action, successText) => {
    try {
      await action()
      notify.success(successText)
      close()
      reload()
    } catch (error) {
      notify.error(getErrorMessage(error))
    }
  }

  const columns = [
    {
      field: 'email',
      label: 'User',
      sortable: true,
      render: (u) => (
        <Box>
          <Typography variant="body2">{u.email}</Typography>
          {u.employee ? (
            <Typography variant="caption" color="text.secondary">
              {u.employee.full_name} ({u.employee.employee_code})
            </Typography>
          ) : null}
          {u.needs_employee_link ? (
            <Tooltip title="Created before employee records existed. Edit the user to link one.">
              <Chip size="small" color="warning" variant="outlined" label="Needs employee link" sx={{ ml: 1 }} />
            </Tooltip>
          ) : null}
        </Box>
      ),
    },
    { field: 'role', label: 'Role', sortable: true, render: (u) => u.role.name },
    {
      field: 'is_active',
      label: 'Status',
      sortable: true,
      render: (u) => (
        <Chip
          size="small"
          label={u.is_active ? 'Active' : 'Inactive'}
          color={u.is_active ? 'success' : 'default'}
          variant={u.is_active ? 'filled' : 'outlined'}
        />
      ),
    },
    {
      field: 'last_login_at',
      label: 'Last login',
      sortable: true,
      render: (u) => (u.last_login_at ? formatDateTime(u.last_login_at) : 'Never'),
    },
    { field: 'created_at', label: 'Created', sortable: true, render: (u) => formatDateTime(u.created_at) },
    {
      field: 'actions',
      label: 'Actions',
      align: 'right',
      render: (u) => {
        const isMe = u.id === me?.id
        return (
          <Stack direction="row" spacing={0.5} sx={{ justifyContent: 'flex-end' }}>
            <Tooltip title="Edit email or employee record">
              <IconButton size="small" aria-label={`Edit ${u.email}`} onClick={() => setDialog({ type: 'edit', user: u })}>
                <EditOutlined fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title={isMe ? SELF_HINT : 'Change role'}>
              <span>
                <IconButton
                  size="small"
                  aria-label={`Change role of ${u.email}`}
                  disabled={isMe}
                  onClick={() => {
                    setNewRole(u.role.name)
                    setRoleEmployee(null)
                    setDialog({ type: 'role', user: u })
                  }}
                >
                  <ManageAccountsOutlined fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title={isMe ? SELF_HINT : u.is_active ? 'Deactivate' : 'Activate'}>
              <span>
                <IconButton
                  size="small"
                  aria-label={`${u.is_active ? 'Deactivate' : 'Activate'} ${u.email}`}
                  disabled={isMe}
                  color={u.is_active ? 'error' : 'success'}
                  onClick={() => setDialog({ type: 'active', user: u })}
                >
                  {u.is_active ? <BlockOutlined fontSize="small" /> : <CheckCircleOutline fontSize="small" />}
                </IconButton>
              </span>
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
        label="Role"
        value={roleFilter}
        onChange={(e) => setRoleFilter(e.target.value)}
        sx={{ minWidth: 150 }}
      >
        <MenuItem value="">All roles</MenuItem>
        {Object.values(ROLES).map((r) => (
          <MenuItem key={r} value={r}>
            {r}
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
        <MenuItem value="true">Active</MenuItem>
        <MenuItem value="false">Inactive</MenuItem>
      </TextField>
    </>
  )

  const target = dialog?.user
  // Changing to Employee needs an employee link when the user has none (order fix b).
  const roleNeedsEmployee = newRole === ROLES.EMPLOYEE && !target?.employee

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" component="h1">
          Users
        </Typography>
        <Button variant="contained" startIcon={<AddOutlined />} onClick={() => setDialog({ type: 'create' })}>
          Create user
        </Button>
      </Stack>

      <DataTable
        columns={columns}
        fetchRows={fetchRows}
        defaultSort="email"
        searchPlaceholder="Search email or name"
        emptyTitle="No users found"
        reloadKey={reloadKey}
        toolbar={filters}
      />

      {dialog?.type === 'create' || dialog?.type === 'edit' ? (
        <UserFormDialog
          open
          user={dialog.type === 'edit' ? target : null}
          onClose={close}
          onSaved={(saved, created) => {
            notify.success(created ? `User ${saved.email} created.` : `User ${saved.email} saved.`)
            close()
            reload()
          }}
        />
      ) : null}

      <ConfirmDialog
        open={dialog?.type === 'role'}
        title={`Change role of ${target?.email ?? ''}?`}
        message={`Current role: ${target?.role.name ?? ''}. The new role applies on their next action.`}
        confirmLabel="Change role"
        confirmDisabled={!newRole || newRole === target?.role.name || (roleNeedsEmployee && !roleEmployee)}
        onCancel={close}
        onConfirm={() =>
          runAction(
            () => changeUserRole(target.id, newRole, roleNeedsEmployee ? roleEmployee?.id : null),
            `${target.email} is now ${newRole}.`,
          )
        }
      >
        <TextField
          select
          fullWidth
          label="New role"
          value={newRole}
          onChange={(e) => setNewRole(e.target.value)}
          sx={{ mt: 2 }}
        >
          {Object.values(ROLES).map((r) => (
            <MenuItem key={r} value={r}>
              {r}
            </MenuItem>
          ))}
        </TextField>
        {roleNeedsEmployee ? (
          <EmployeePicker
            value={roleEmployee}
            onChange={setRoleEmployee}
            required
            helperText="An Employee login must be linked to an employee record."
          />
        ) : null}
      </ConfirmDialog>

      <ConfirmDialog
        open={dialog?.type === 'active'}
        title={target?.is_active ? `Deactivate ${target?.email}?` : `Activate ${target?.email ?? ''}?`}
        message={
          target?.is_active
            ? 'They will be signed out on their next action and cannot log in until reactivated. Nothing is deleted.'
            : 'They will be able to log in again with their existing password.'
        }
        confirmLabel={target?.is_active ? 'Deactivate' : 'Activate'}
        destructive={Boolean(target?.is_active)}
        onCancel={close}
        onConfirm={() =>
          runAction(
            () => setUserActive(target.id, !target.is_active),
            `${target.email} ${target.is_active ? 'deactivated' : 'activated'}.`,
          )
        }
      />
    </Stack>
  )
}
