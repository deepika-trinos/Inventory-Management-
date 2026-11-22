// Edit an asset (Slice 4.2, AST-04; owner's answer A2), opened from the asset page.
//   Editable: name, brand, model, serial number (unique, any case), location, warranty expiry.
//   Shown read-only: asset ID, status, category and the purchase facts (purchase, purchase
//   date, cost): they come from the invoice and stay locked (P6). Status changes only
//   through actions such as Retire (AST-07).
// The server checks everything again; its problems are shown under the right field.
import { useState } from 'react'
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Typography,
} from '@mui/material'

import { assetStatusLabel, updateAsset } from '../../api/assets'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import FormField from '../../components/FormField'
import { formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'

// Same limits and checks as the server (backend/app/modules/assets, decisions B57, B61, P5).
const LIMITS = { name: 200, brand: 100, model: 100, serial_number: 100, location: 200 }
const TEXT_FIELDS = ['name', 'brand', 'model', 'serial_number', 'location']
const REQUIRED = { name: 'name', model: 'model', serial_number: 'serial number' }

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  serial_number_taken: 'serial_number',
  invalid_serial_number: 'serial_number',
  invalid_model: 'model',
  invalid_asset_name: 'name',
  invalid_brand: 'brand',
  invalid_location: 'location',
  invalid_warranty_expiry: 'warranty_expiry',
}

export function validateAssetEdit(values, purchaseDate) {
  const errors = {}
  for (const [field, label] of Object.entries(REQUIRED)) {
    if (!values[field].trim()) errors[field] = `Please enter the ${label}.`
  }
  for (const field of TEXT_FIELDS) {
    if (values[field].trim().length > LIMITS[field]) errors[field] = `Use at most ${LIMITS[field]} characters.`
  }
  if (values.warranty_expiry && purchaseDate && values.warranty_expiry < purchaseDate) {
    errors.warranty_expiry = `Cannot be before the purchase date (${formatPlainDate(purchaseDate)}).`
  }
  return errors
}

function ReadOnly({ label, value }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2">{value || '—'}</Typography>
    </Box>
  )
}

export default function AssetEditDialog({ open, asset, onClose, onSaved }) {
  const [values, setValues] = useState(() => ({
    ...Object.fromEntries(TEXT_FIELDS.map((f) => [f, asset[f] ?? ''])),
    warranty_expiry: asset.warranty_expiry ?? '',
  }))
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
    const found = validateAssetEdit(values, asset.purchase_date)
    setErrors(found)
    if (Object.keys(found).length) return

    // Trimmed values; an empty optional field is sent as null (= cleared). The server
    // saves only what really changed (and records nothing if nothing did).
    const payload = Object.fromEntries(TEXT_FIELDS.map((f) => [f, values[f].trim() || null]))
    payload.warranty_expiry = values.warranty_expiry || null
    setSaving(true)
    try {
      const saved = await updateAsset(asset.asset_code, payload)
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

  const purchase = asset.purchase

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>Edit {asset.asset_code}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              {formError}
            </Alert>
          ) : null}
          {text('name', 'Name', { required: true, autoFocus: true })}
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
                label="Warranty expiry"
                value={values.warranty_expiry}
                onChange={handleChange('warranty_expiry')}
                error={errors.warranty_expiry}
                disabled={saving}
                helperText={asset.purchase_date ? `Not before ${formatPlainDate(asset.purchase_date)}.` : 'Optional.'}
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: asset.purchase_date || undefined } }}
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2" component="h3" gutterBottom>
            Cannot be changed here
          </Typography>
          <Box
            data-testid="asset-locked-fields"
            sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr 1fr', sm: '1fr 1fr 1fr' } }}
          >
            <ReadOnly label="Asset ID" value={asset.asset_code} />
            <ReadOnly label="Status" value={assetStatusLabel(asset.status)} />
            <ReadOnly label="Category" value={asset.category.name} />
            <ReadOnly label="Purchase" value={purchase ? `${purchase.purchase_number} · ${purchase.vendor}` : null} />
            <ReadOnly label="Purchase date" value={asset.purchase_date ? formatPlainDate(asset.purchase_date) : null} />
            <ReadOnly label="Cost" value={asset.cost ? formatAmount(asset.cost) : null} />
          </Box>
          <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1 }}>
            Category, purchase, purchase date and cost come from the invoice. Status changes only through
            actions (for example Retire).
          </Typography>
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
            Save
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
