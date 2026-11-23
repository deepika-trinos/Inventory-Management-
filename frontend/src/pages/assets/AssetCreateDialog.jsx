// Add existing asset (Slice 4.5, AST-01, PRD question 4; owner's answer A7), opened from the
// Assets page: equipment the company already owns, entered by hand without a purchase.
//   Required: an ACTIVE one-by-one category, name, serial number (unique, any case), model.
//   Optional: brand, location, purchase date (today or earlier), warranty expiry (not before
//   the purchase date, B61), cost (INR, 2 decimals, 0 allowed, P2).
//   No vendor and no quantity: one asset per entry. The asset ID comes from the same
//   sequence as received assets; the status is always Available.
// The server checks everything again; its problems are shown under the right field.
import { useEffect, useState } from 'react'
import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  Typography,
} from '@mui/material'

import { createAsset } from '../../api/assets'
import { listCategories } from '../../api/categories'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'
import { LIMITS, validateAssetEdit, validatePurchaseFacts } from './AssetEditDialog'

const TEXT_FIELDS = ['name', 'serial_number', 'model', 'brand', 'location']

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  serial_number_taken: 'serial_number',
  invalid_serial_number: 'serial_number',
  invalid_model: 'model',
  invalid_asset_name: 'name',
  invalid_brand: 'brand',
  invalid_location: 'location',
  invalid_warranty_expiry: 'warranty_expiry',
  purchase_date_in_future: 'purchase_date',
  category_inactive: 'category_id',
  category_not_serialized: 'category_id',
  category_not_found: 'category_id',
}

const EMPTY = {
  category_id: '',
  name: '',
  serial_number: '',
  model: '',
  brand: '',
  location: '',
  purchase_date: '',
  warranty_expiry: '',
  cost: '',
}

export function validateAssetCreate(values, today = todayInCompanyTimezone()) {
  return {
    ...validateAssetEdit(values, values.purchase_date || null),
    ...validatePurchaseFacts(values, today),
  }
}

export default function AssetCreateDialog({ open, onClose, onSaved }) {
  const today = todayInCompanyTimezone()
  const [values, setValues] = useState(EMPTY)
  const [categories, setCategories] = useState(null) // null while loading
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  // Only ACTIVE categories tracked one by one can take a new asset (B13, A7).
  useEffect(() => {
    listCategories({ page: 1, pageSize: 100, sort: 'name', trackingType: 'serialized', status: 'active' })
      .then((data) => setCategories(data.items))
      .catch(() => setCategories([]))
  }, [])

  const handleChange = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const found = validateAssetCreate(values, today)
    setErrors(found)
    if (Object.keys(found).length) return

    const payload = { category_id: Number(values.category_id) }
    for (const f of TEXT_FIELDS) payload[f] = values[f].trim() || null
    payload.purchase_date = values.purchase_date || null
    payload.warranty_expiry = values.warranty_expiry || null
    payload.cost = values.cost.trim() || null
    setSaving(true)
    try {
      const saved = await createAsset(payload)
      onSaved(saved)
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

  const noCategories = categories !== null && categories.length === 0

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>Add existing asset</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            For equipment the company already owns. It gets the next asset ID and starts as Available, with no
            purchase or vendor. Items bought now should be received on a purchase instead.
          </Typography>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              {formError}
            </Alert>
          ) : null}
          {noCategories ? (
            <Alert severity="info" sx={{ mb: 1 }}>
              There is no active one-by-one category. Add or activate one on the Categories page first.
            </Alert>
          ) : null}
          <FormField
            select
            label="Category"
            required
            autoFocus
            value={values.category_id}
            onChange={handleChange('category_id')}
            error={errors.category_id}
            disabled={saving || categories === null}
            helperText="Active categories tracked one by one."
          >
            {(categories ?? []).map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </FormField>
          {text('name', 'Name', { required: true, placeholder: 'e.g. Dell Latitude 7490' })}
          <Grid container columnSpacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              {text('serial_number', 'Serial number', {
                required: true,
                helperText: 'Must be unique (upper/lower case does not matter).',
              })}
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{text('model', 'Model', { required: true })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{text('brand', 'Brand')}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{text('location', 'Location')}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormField
                type="date"
                label="Purchase date"
                value={values.purchase_date}
                onChange={handleChange('purchase_date')}
                error={errors.purchase_date}
                disabled={saving}
                helperText="Optional. Today or earlier."
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: today } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormField
                type="date"
                label="Warranty expiry"
                value={values.warranty_expiry}
                onChange={handleChange('warranty_expiry')}
                error={errors.warranty_expiry}
                disabled={saving}
                helperText={values.purchase_date ? `Optional. Not before ${formatPlainDate(values.purchase_date)}.` : 'Optional.'}
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: values.purchase_date || undefined } }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormField
                label="Cost (₹)"
                value={values.cost}
                onChange={handleChange('cost')}
                error={errors.cost}
                disabled={saving}
                autoComplete="off"
                helperText="Optional. INR, up to 2 decimals."
                slotProps={{ htmlInput: { inputMode: 'decimal' } }}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={saving || noCategories}
            startIcon={saving ? <CircularProgress size={16} color="inherit" /> : null}
          >
            Add asset
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
