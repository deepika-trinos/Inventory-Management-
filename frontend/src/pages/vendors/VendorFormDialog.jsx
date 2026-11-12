// The Add vendor / Edit vendor form, shown in a pop-up dialog (VEN-01, VEN-02).
//   Required: name (unique, any case, decision B30).
//   Optional ("where available", B31): contact person, email, phone, address.
//   Active status has its own confirmed action.
// Problems are shown under the field they belong to, e.g. "name already used".
import { useState } from 'react'
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
} from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { createVendor, updateVendor } from '../../api/vendors'
import FormField from '../../components/FormField'

// Same limits and checks as the server (backend/app/modules/vendors, app/core/text.py).
const LIMITS = { name: 150, contact_person: 150, email: 255, phone: 30, address: 500 }
const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const PHONE_SHAPE = /^\+?[0-9 ()./-]{3,30}$/
const FIELDS = ['name', 'contact_person', 'email', 'phone', 'address']

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  vendor_name_taken: 'name',
  invalid_name: 'name',
  invalid_email: 'email',
  invalid_phone: 'phone',
}

function validate(values) {
  const errors = {}
  if (!values.name.trim()) errors.name = "Please enter the vendor's name."
  const email = values.email.trim()
  if (email && !EMAIL_SHAPE.test(email)) errors.email = 'Please enter a valid email address.'
  const phone = values.phone.trim()
  if (phone && !PHONE_SHAPE.test(phone)) errors.phone = 'Use digits, spaces, + ( ) . / and - only.'
  for (const field of FIELDS) {
    if (values[field].trim().length > LIMITS[field]) errors[field] = `Use at most ${LIMITS[field]} characters.`
  }
  return errors
}

export default function VendorFormDialog({ open, vendor, onClose, onSaved }) {
  const isCreate = !vendor
  const [values, setValues] = useState(() => Object.fromEntries(FIELDS.map((f) => [f, vendor?.[f] ?? ''])))
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
    const found = validate(values)
    setErrors(found)
    if (Object.keys(found).length) return

    // Trimmed values; empty optional fields are sent as null (= cleared).
    const payload = Object.fromEntries(FIELDS.map((f) => [f, values[f].trim() || null]))
    setSaving(true)
    try {
      const saved = isCreate ? await createVendor(payload) : await updateVendor(vendor.id, payload)
      onSaved(saved, isCreate)
    } catch (error) {
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error))
      setSaving(false)
    }
  }

  const text = (field, label, props = {}) => (
    <FormField
      label={label}
      value={values[field]}
      onChange={handleChange(field)}
      error={errors[field]}
      disabled={saving}
      autoComplete="off"
      slotProps={{ htmlInput: { maxLength: LIMITS[field] } }}
      {...props}
    />
  )

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>{isCreate ? 'Add vendor' : 'Edit vendor'}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              {formError}
            </Alert>
          ) : null}
          {text('name', 'Vendor name', {
            required: true,
            autoFocus: true,
            helperText: 'Must be unique (upper/lower case does not matter).',
          })}
          <Grid container columnSpacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>{text('contact_person', 'Contact person')}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{text('phone', 'Phone', { type: 'tel' })}</Grid>
          </Grid>
          {text('email', 'Email', { type: 'email' })}
          {text('address', 'Address', { multiline: true, minRows: 2 })}
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
            {isCreate ? 'Add vendor' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
