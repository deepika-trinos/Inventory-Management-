// The Add item / Edit item form for items tracked BY QUANTITY (Slice 2.4, INV-01).
//   Name, category (only ACTIVE categories tracked by quantity are offered, PRD 9.2),
//   unit of measure (fixed list, B35) and reorder threshold (required, 0 or more, B37).
//   Quantity on hand is shown read-only when editing: only stock movements change it.
// Problems are shown under the field they belong to.
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
} from '@mui/material'

import { listCategories } from '../../api/categories'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import { createStockItem, UNITS, updateStockItem } from '../../api/stockItems'
import FormField from '../../components/FormField'

const NAME_MAX = 150

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  stock_item_name_taken: 'name',
  invalid_name: 'name',
  category_not_bulk: 'category_id',
  category_inactive: 'category_id',
  category_not_found: 'category_id',
  unit_locked: 'unit_of_measure',
}

function validate(values) {
  const errors = {}
  if (!values.name.trim()) errors.name = "Please enter the item's name."
  else if (values.name.trim().length > NAME_MAX) errors.name = `Use at most ${NAME_MAX} characters.`
  if (!values.category_id) errors.category_id = 'Please choose a category.'
  if (!values.unit_of_measure) errors.unit_of_measure = 'Please choose a unit.'
  const threshold = String(values.reorder_threshold).trim()
  if (threshold === '') errors.reorder_threshold = 'Please enter a reorder threshold (0 or more).'
  else if (!/^\d+$/.test(threshold)) errors.reorder_threshold = 'Use a whole number, 0 or more.'
  return errors
}

export default function StockItemFormDialog({ open, item, onClose, onSaved }) {
  const isCreate = !item
  const [values, setValues] = useState({
    name: item?.name ?? '',
    category_id: item?.category.id ?? '',
    unit_of_measure: item?.unit_of_measure ?? 'pieces',
    reorder_threshold: item?.reorder_threshold ?? 0,
  })
  const [categories, setCategories] = useState([])
  const [categoriesError, setCategoriesError] = useState('')
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  // Only active categories tracked by quantity can be chosen. When editing, the
  // item's current category is always offered too (it may have been deactivated since).
  useEffect(() => {
    listCategories({ page: 1, pageSize: 100, sort: 'name', trackingType: 'bulk', status: 'active' })
      .then((data) => {
        const found = data.items
        if (item && !found.some((c) => c.id === item.category.id)) found.push(item.category)
        setCategories(found)
      })
      .catch((err) => setCategoriesError(getErrorMessage(err)))
  }, [item])

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

    const payload = {
      name: values.name.trim(),
      category_id: Number(values.category_id),
      unit_of_measure: values.unit_of_measure,
      reorder_threshold: Number(values.reorder_threshold),
    }
    setSaving(true)
    try {
      const saved = isCreate ? await createStockItem(payload) : await updateStockItem(item.id, payload)
      onSaved(saved, isCreate)
    } catch (error) {
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error))
      setSaving(false)
    }
  }

  const noCategories = !categoriesError && categories.length === 0

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>{isCreate ? 'Add stock item' : 'Edit stock item'}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              {formError}
            </Alert>
          ) : null}
          {categoriesError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              Could not load categories: {categoriesError}
            </Alert>
          ) : null}
          <FormField
            label="Item name"
            required
            autoFocus
            autoComplete="off"
            value={values.name}
            onChange={handleChange('name')}
            error={errors.name}
            helperText="e.g. USB mouse. Must be unique within its category."
            disabled={saving}
            slotProps={{ htmlInput: { maxLength: NAME_MAX } }}
          />
          <FormField
            select
            label="Category"
            required
            value={values.category_id}
            onChange={handleChange('category_id')}
            error={errors.category_id}
            helperText={
              noCategories
                ? 'No active "By quantity" category yet. Add one on the Categories page first.'
                : 'Only active categories tracked by quantity are listed.'
            }
            disabled={saving || noCategories}
          >
            {categories.map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
                {c.status !== 'active' ? ' (inactive)' : ''}
              </MenuItem>
            ))}
          </FormField>
          <Grid container columnSpacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormField
                select
                label="Unit of measure"
                required
                value={values.unit_of_measure}
                onChange={handleChange('unit_of_measure')}
                error={errors.unit_of_measure}
                helperText={isCreate ? ' ' : 'Locked once the item has stock.'}
                disabled={saving}
              >
                {UNITS.map((u) => (
                  <MenuItem key={u.value} value={u.value}>
                    {u.label}
                  </MenuItem>
                ))}
              </FormField>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormField
                label="Reorder threshold"
                required
                type="number"
                value={values.reorder_threshold}
                onChange={handleChange('reorder_threshold')}
                error={errors.reorder_threshold}
                helperText="Low stock at or below this quantity."
                disabled={saving}
                slotProps={{ htmlInput: { min: 0, step: 1, inputMode: 'numeric' } }}
              />
            </Grid>
          </Grid>
          {!isCreate ? (
            <FormField
              label="Quantity on hand"
              value={`${item.quantity_on_hand}`}
              helperText="Read-only. Changes only through receiving, issuing or adjusting stock."
              disabled
            />
          ) : null}
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
            {isCreate ? 'Add item' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
