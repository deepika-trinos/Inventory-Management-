// The Add category / Edit category form, shown in a pop-up dialog.
//   Fields: name (required), description (optional), tracking type (required).
//   Active status has its own confirmed action on the list.
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
  MenuItem,
} from '@mui/material'

import { createCategory, TRACKING_TYPES, updateCategory } from '../../api/categories'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import FormField from '../../components/FormField'

// Same limits as the server (backend/app/modules/categories/models.py).
const NAME_MAX = 100
const DESCRIPTION_MAX = 500

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  category_name_taken: 'name',
  invalid_name: 'name',
  tracking_type_locked: 'trackingType',
}

function validate(values) {
  const errors = {}
  if (!values.name.trim()) errors.name = 'Please enter a category name.'
  else if (values.name.trim().length > NAME_MAX) errors.name = `Use at most ${NAME_MAX} characters.`
  if (values.description.trim().length > DESCRIPTION_MAX)
    errors.description = `Use at most ${DESCRIPTION_MAX} characters.`
  if (!values.trackingType) errors.trackingType = 'Please choose how items are tracked.'
  return errors
}

export default function CategoryFormDialog({ open, category, onClose, onSaved }) {
  const isCreate = !category
  const [values, setValues] = useState({
    name: category?.name ?? '',
    description: category?.description ?? '',
    trackingType: category?.tracking_type ?? '',
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
    const found = validate(values)
    setErrors(found)
    if (Object.keys(found).length) return

    const name = values.name.trim()
    const description = values.description.trim() || null
    setSaving(true)
    try {
      const saved = isCreate
        ? await createCategory({ name, description, trackingType: values.trackingType })
        : await updateCategory(category.id, { name, description, tracking_type: values.trackingType })
      onSaved(saved, isCreate)
    } catch (error) {
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error))
      setSaving(false)
    }
  }

  const selectedType = TRACKING_TYPES.find((t) => t.value === values.trackingType)

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>{isCreate ? 'Add category' : 'Edit category'}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              {formError}
            </Alert>
          ) : null}
          <FormField
            label="Name"
            required
            autoFocus
            autoComplete="off"
            value={values.name}
            onChange={handleChange('name')}
            error={errors.name}
            helperText="Must be unique (upper/lower case does not matter)."
            disabled={saving}
            slotProps={{ htmlInput: { maxLength: NAME_MAX } }}
          />
          <FormField
            label="Description"
            multiline
            minRows={2}
            value={values.description}
            onChange={handleChange('description')}
            error={errors.description}
            helperText="Optional."
            disabled={saving}
            slotProps={{ htmlInput: { maxLength: DESCRIPTION_MAX } }}
          />
          <FormField
            select
            label="Tracking type"
            required
            value={values.trackingType}
            onChange={handleChange('trackingType')}
            error={errors.trackingType}
            helperText={
              selectedType?.hint ??
              'Cannot be changed later once items or assets use this category.'
            }
            disabled={saving}
          >
            {TRACKING_TYPES.map((t) => (
              <MenuItem key={t.value} value={t.value}>
                {t.label}
              </MenuItem>
            ))}
          </FormField>
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
            {isCreate ? 'Add category' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
