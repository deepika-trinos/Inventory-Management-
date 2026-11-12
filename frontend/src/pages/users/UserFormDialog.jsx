// The Create user / Edit user form, shown in a pop-up dialog.
//   Create: email, temporary password (typed twice), role, employee record.
//   Edit:   email and employee record (role and active status have their own
//           confirmed actions).
// Employee record (Slice 2.2, closes B12): picked from ACTIVE employees without a
// login. REQUIRED for the Employee role (order fix b); optional for other roles.
// Problems are shown under the field they belong to, e.g. "email already used".
import { useState } from 'react'
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
} from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { createUser, updateUser } from '../../api/users'
import EmployeePicker from '../../components/EmployeePicker'
import FormField from '../../components/FormField'
import { ROLES } from '../../routes/navigation'

const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
export const PASSWORD_MIN_LENGTH = 12 // same as PASSWORD_MIN_LENGTH on the server (decision B2)

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  email_taken: 'email',
  invalid_email: 'email',
  weak_password: 'password',
  employee_link_required: 'employee',
  employee_has_login: 'employee',
  employee_inactive: 'employee',
  employee_not_found: 'employee',
}

function validate(values, isCreate, needsEmployee) {
  const errors = {}
  if (!values.email.trim()) errors.email = 'Please enter an email.'
  else if (!EMAIL_SHAPE.test(values.email.trim())) errors.email = 'Please enter a valid email address.'
  if (isCreate) {
    if (!values.password) errors.password = 'Please enter a temporary password.'
    else if (values.password.length < PASSWORD_MIN_LENGTH)
      errors.password = `Use at least ${PASSWORD_MIN_LENGTH} characters.`
    if (values.confirm !== values.password) errors.confirm = 'The two passwords do not match.'
    if (!values.role) errors.role = 'Please choose a role.'
  }
  if (needsEmployee && !values.employee) errors.employee = 'An Employee login must be linked to an employee record.'
  return errors
}

export default function UserFormDialog({ open, user, onClose, onSaved }) {
  const isCreate = !user
  const [values, setValues] = useState({
    email: user?.email ?? '',
    password: '',
    confirm: '',
    role: '',
    employee: user?.employee ?? null,
  })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const role = isCreate ? values.role : user.role.name
  const needsEmployee = role === ROLES.EMPLOYEE

  const setField = (field, value) => {
    setValues((v) => ({ ...v, [field]: value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }
  const handleChange = (field) => (event) => setField(field, event.target.value)

  const handleSubmit = async (event) => {
    event.preventDefault()
    const found = validate(values, isCreate, needsEmployee)
    setErrors(found)
    if (Object.keys(found).length) return

    const employeeId = values.employee?.id ?? null
    setSaving(true)
    try {
      let saved
      if (isCreate) {
        saved = await createUser({
          email: values.email.trim(),
          password: values.password,
          role: values.role,
          employeeId,
        })
      } else {
        const changes = { email: values.email.trim() }
        if (employeeId !== (user.employee?.id ?? null)) changes.employee_id = employeeId
        saved = await updateUser(user.id, changes)
      }
      onSaved(saved, isCreate)
    } catch (error) {
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error))
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="xs" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>{isCreate ? 'Create user' : 'Edit user'}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              {formError}
            </Alert>
          ) : null}
          {!isCreate && user.needs_employee_link ? (
            <Alert severity="warning" sx={{ mb: 1 }}>
              This Employee login is not linked to an employee record yet. Please pick one.
            </Alert>
          ) : null}
          <FormField
            label="Email"
            type="email"
            required
            autoFocus
            autoComplete="off"
            value={values.email}
            onChange={handleChange('email')}
            error={errors.email}
            disabled={saving}
          />
          {isCreate ? (
            <>
              <FormField
                label="Temporary password"
                type="password"
                required
                autoComplete="new-password"
                value={values.password}
                onChange={handleChange('password')}
                error={errors.password}
                helperText={`At least ${PASSWORD_MIN_LENGTH} characters. Give it to the user privately.`}
                disabled={saving}
              />
              <FormField
                label="Repeat password"
                type="password"
                required
                autoComplete="new-password"
                value={values.confirm}
                onChange={handleChange('confirm')}
                error={errors.confirm}
                disabled={saving}
              />
              <FormField
                select
                label="Role"
                required
                value={values.role}
                onChange={handleChange('role')}
                error={errors.role}
                disabled={saving}
              >
                {Object.values(ROLES).map((r) => (
                  <MenuItem key={r} value={r}>
                    {r}
                  </MenuItem>
                ))}
              </FormField>
            </>
          ) : null}
          <EmployeePicker
            value={values.employee}
            onChange={(picked) => setField('employee', picked)}
            current={user?.employee ?? null}
            required={needsEmployee}
            error={errors.employee}
            helperText={
              needsEmployee
                ? 'Required for the Employee role. Only active employees without a login are listed.'
                : 'Optional for this role. Only active employees without a login are listed.'
            }
            disabled={saving}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={saving}
            startIcon={saving ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {isCreate ? 'Create user' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
