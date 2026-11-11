// The Create user / Edit user form, shown in a pop-up dialog.
//   Create: email, temporary password (typed twice), role.
//   Edit:   email only (role and active status have their own confirmed actions).
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
import FormField from '../../components/FormField'
import { ROLES } from '../../routes/navigation'

const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
export const PASSWORD_MIN_LENGTH = 12 // same as PASSWORD_MIN_LENGTH on the server (decision B2)

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  email_taken: 'email',
  invalid_email: 'email',
  weak_password: 'password',
}

function validate(values, isCreate) {
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
  return errors
}

export default function UserFormDialog({ open, user, onClose, onSaved }) {
  const isCreate = !user
  const [values, setValues] = useState({
    email: user?.email ?? '',
    password: '',
    confirm: '',
    role: '',
  })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const handleChange = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const found = validate(values, isCreate)
    setErrors(found)
    if (Object.keys(found).length) return

    setSaving(true)
    try {
      const saved = isCreate
        ? await createUser({ email: values.email.trim(), password: values.password, role: values.role })
        : await updateUser(user.id, { email: values.email.trim() })
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
                {Object.values(ROLES).map((role) => (
                  <MenuItem key={role} value={role}>
                    {role}
                  </MenuItem>
                ))}
              </FormField>
            </>
          ) : null}
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
