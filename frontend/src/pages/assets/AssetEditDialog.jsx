// Edit an asset (Slice 4.2, AST-04; owner's answer A2), opened from the asset page.
//   Editable: name, brand, model, serial number (unique, any case), location, warranty expiry.
//   Shown read-only: asset ID, status, category and the purchase facts (purchase, purchase
//   date, cost): they come from the invoice and stay locked (P6). Status changes only
//   through actions such as Retire (AST-07).
// Slice 4.5 (I4): on an asset ENTERED BY HAND (no purchase) the category (active, one by
//   one), purchase date (today or earlier) and cost are editable too; on a received asset
//   they stay locked.
// The server checks everything again; its problems are shown under the right field.
import { useEffect, useState } from 'react'
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
  MenuItem,
  Typography,
} from '@mui/material'

import { assetStatusLabel, enteredByHand, updateAsset } from '../../api/assets'
import { listCategories } from '../../api/categories'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'
import { AMOUNT_PATTERN, formatAmount } from '../../utils/money'

// Same limits and checks as the server (backend/app/modules/assets, decisions B57, B61, P5).
export const LIMITS = { name: 200, brand: 100, model: 100, serial_number: 100, location: 200 }
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
  purchase_date_in_future: 'purchase_date',
  category_inactive: 'category_id',
  category_not_serialized: 'category_id',
  category_not_found: 'category_id',
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

/** Purchase date and cost of an asset entered by hand (I1, I4): no future date; INR, 2 decimals, 0 allowed. */
export function validatePurchaseFacts(values, today = todayInCompanyTimezone()) {
  const errors = {}
  if (values.purchase_date && values.purchase_date > today) errors.purchase_date = 'The purchase date cannot be in the future.'
  const cost = String(values.cost ?? '').trim()
  if (cost && !AMOUNT_PATTERN.test(cost)) errors.cost = 'Enter an amount of 0 or more, with up to 2 decimals (e.g. 45000.50).'
  if (!values.category_id) errors.category_id = 'Please choose a category.'
  return errors
}

export default function AssetEditDialog({ open, asset, onClose, onSaved }) {
  const manual = enteredByHand(asset)
  const today = todayInCompanyTimezone()
  const [values, setValues] = useState(() => ({
    ...Object.fromEntries(TEXT_FIELDS.map((f) => [f, asset[f] ?? ''])),
    warranty_expiry: asset.warranty_expiry ?? '',
    category_id: asset.category.id,
    purchase_date: asset.purchase_date ?? '',
    cost: asset.cost ?? '',
  }))
  // Manual entries: the categories it can move to (active, one by one) plus its current one.
  const [categories, setCategories] = useState([asset.category])
  useEffect(() => {
    if (!manual) return
    listCategories({ page: 1, pageSize: 100, sort: 'name', trackingType: 'serialized', status: 'active' })
      .then((data) => {
        const others = data.items.filter((c) => c.id !== asset.category.id)
        setCategories([asset.category, ...others].sort((a, b) => a.name.localeCompare(b.name)))
      })
      .catch(() => {})
  }, [manual, asset.category])
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
    const purchaseDate = manual ? values.purchase_date || null : asset.purchase_date
    const found = { ...validateAssetEdit(values, purchaseDate), ...(manual ? validatePurchaseFacts(values, today) : {}) }
    setErrors(found)
    if (Object.keys(found).length) return

    // Trimmed values; an empty optional field is sent as null (= cleared). The server
    // saves only what really changed (and records nothing if nothing did).
    const payload = Object.fromEntries(TEXT_FIELDS.map((f) => [f, values[f].trim() || null]))
    payload.warranty_expiry = values.warranty_expiry || null
    if (manual) {
      payload.category_id = Number(values.category_id)
      payload.purchase_date = values.purchase_date || null
      payload.cost = String(values.cost).trim() || null
    }
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
  const warrantyMin = manual ? values.purchase_date : asset.purchase_date

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
                helperText={warrantyMin ? `Not before ${formatPlainDate(warrantyMin)}.` : 'Optional.'}
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: warrantyMin || undefined } }}
              />
            </Grid>
            {manual ? (
              <>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormField
                    select
                    label="Category"
                    required
                    value={values.category_id}
                    onChange={handleChange('category_id')}
                    error={errors.category_id}
                    disabled={saving}
                    helperText="Active categories tracked one by one."
                  >
                    {categories.map((c) => (
                      <MenuItem key={c.id} value={c.id}>
                        {c.name}
                        {c.status && c.status !== 'active' ? ' (inactive)' : ''}
                      </MenuItem>
                    ))}
                  </FormField>
                </Grid>
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
              </>
            ) : null}
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
            {manual ? (
              <ReadOnly label="Purchase" value="None (entered by hand)" />
            ) : (
              <>
                <ReadOnly label="Category" value={asset.category.name} />
                <ReadOnly label="Purchase" value={`${purchase.purchase_number} · ${purchase.vendor}`} />
                <ReadOnly label="Purchase date" value={asset.purchase_date ? formatPlainDate(asset.purchase_date) : null} />
                <ReadOnly label="Cost" value={asset.cost ? formatAmount(asset.cost) : null} />
              </>
            )}
          </Box>
          <Typography variant="caption" color="text.secondary" component="p" sx={{ mt: 1 }}>
            {manual
              ? 'Status changes only through actions (for example Retire).'
              : 'Category, purchase, purchase date and cost come from the invoice. Status changes only through actions (for example Retire).'}
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
