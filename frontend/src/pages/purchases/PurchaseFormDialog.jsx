// The New purchase / Edit draft form (Slice 3.1, PUR-01 to PUR-04).
//   Vendor (ACTIVE vendors only, B33), invoice / reference number, purchase date
//   (not in the future, P3), notes, and an editable list of lines (P1):
//     - "By quantity": pick an ACTIVE stock item.
//     - "One-by-one": pick an ACTIVE one-by-one category and type a description.
//   Each line has a quantity and a unit cost in ₹ (0 allowed, 2 decimals, P2).
//   Line totals and the grand total are shown as you type; the server calculates
//   the real ones (they are never sent).
// A purchase that is not a draft opens read-only (received and cancelled are final).
// Problems are shown under the field (or line) they belong to.
// Slice 3.2: a saved draft has a "Receive…" button (save changes first); a received
// purchase shows, per line, how many arrived and the asset IDs created (click one to view it).
import { useEffect, useMemo, useState } from 'react'
import AddOutlined from '@mui/icons-material/AddOutlined'
import DeleteOutline from '@mui/icons-material/DeleteOutlined'
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
  IconButton,
  Link,
  MenuItem,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'

import { listCategories } from '../../api/categories'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import { createPurchase, getPurchase, purchaseStatusLabel, updatePurchase } from '../../api/purchases'
import { listStockItems, unitLabel } from '../../api/stockItems'
import { listVendors } from '../../api/vendors'
import ErrorMessage from '../../components/ErrorMessage'
import FormField from '../../components/FormField'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { todayInCompanyTimezone } from '../../utils/dates'
import { formatPaise } from '../../utils/money'
import AssetDetailsDialog from '../assets/AssetDetailsDialog'
import {
  DESCRIPTION_MAX,
  emptyLine,
  emptyValues,
  grandTotalPaise,
  LINE_TYPES,
  lineTotalPaise,
  NOTES_MAX,
  REFERENCE_MAX,
  switchLineType,
  toPayload,
  validatePurchase,
  valuesFromPurchase,
} from './purchaseForm'

const PICKER_PAGE_SIZE = 100

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  vendor_inactive: 'vendor_id',
  vendor_not_found: 'vendor_id',
  purchase_reference_taken: 'reference_number',
  invalid_reference: 'reference_number',
  purchase_date_in_future: 'purchase_date',
}
// Errors about one line (the server sends details.line = 1, 2, ...).
const LINE_FIELD_FOR_CODE = {
  stock_item_inactive: 'stock_item_id',
  stock_item_not_found: 'stock_item_id',
  category_inactive: 'category_id',
  category_not_found: 'category_id',
  category_not_serialized: 'category_id',
  invalid_line: 'line',
}

// Add `extra` records (already on this purchase, maybe deactivated since) to a picker list.
function withExtras(found, extra) {
  const list = [...found]
  for (const record of extra) if (record && !list.some((r) => r.id === record.id)) list.push(record)
  return list
}

const inactiveMark = (record) => (record.status && record.status !== 'active' ? ' (inactive)' : '')

// The request body a set of form values would send, as text: to spot unsaved changes.
const payloadKey = (values) => JSON.stringify(toPayload(values))

export default function PurchaseFormDialog({ open, purchaseId = null, onClose, onSaved, onReceive }) {
  const theme = useTheme()
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'))
  const isCreate = !purchaseId
  const today = useMemo(() => todayInCompanyTimezone(), [])

  const [purchase, setPurchase] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [loading, setLoading] = useState(!isCreate)
  const [attempt, setAttempt] = useState(0)
  const [values, setValues] = useState(() => emptyValues(today))
  const [options, setOptions] = useState({ vendors: [], stockItems: [], categories: [], loaded: false })
  const [optionsError, setOptionsError] = useState('')
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)
  const [savedKey, setSavedKey] = useState(null) // what is saved on the server (for "unsaved changes")
  const [viewAsset, setViewAsset] = useState(null) // asset ID opened from a received line

  // Existing purchase: load it (with its lines).
  useEffect(() => {
    if (isCreate) return undefined
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    getPurchase(purchaseId)
      .then((found) => {
        if (cancelled) return
        const loaded = valuesFromPurchase(found)
        setPurchase(found)
        setValues(loaded)
        setSavedKey(payloadKey(loaded))
      })
      .catch((err) => !cancelled && setLoadError(err))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [isCreate, purchaseId, attempt])

  const readOnly = Boolean(purchase && purchase.status !== 'draft')

  // Picker lists: only ACTIVE vendors, stock items and one-by-one categories can be
  // chosen. What the draft already uses is always offered too (it may have been
  // deactivated since; the server only re-checks what changes, B45).
  useEffect(() => {
    if (!isCreate && !purchase) return undefined
    let cancelled = false
    const base = { page: 1, pageSize: PICKER_PAGE_SIZE, sort: 'name', status: 'active' }
    Promise.all([
      listVendors(base),
      listStockItems(base),
      listCategories({ ...base, trackingType: 'serialized' }),
    ])
      .then(([vendors, stockItems, categories]) => {
        if (cancelled) return
        const lines = purchase?.lines ?? []
        setOptions({
          vendors: withExtras(vendors.items, [purchase?.vendor]),
          stockItems: withExtras(stockItems.items, lines.map((l) => l.stock_item)),
          categories: withExtras(categories.items, lines.map((l) => l.category)),
          moreVendors: vendors.total > vendors.items.length,
          loaded: true,
        })
      })
      .catch((err) => !cancelled && setOptionsError(getErrorMessage(err)))
    return () => {
      cancelled = true
    }
  }, [isCreate, purchase])

  const clearError = (field) => {
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }

  const handleChange = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }))
    clearError(field)
  }

  const updateLine = (index, change) => {
    setValues((v) => ({ ...v, lines: v.lines.map((line, i) => (i === index ? change(line) : line)) }))
    setErrors((e) => {
      if (!e.lines?.[index]) return e
      const lines = [...e.lines]
      lines[index] = {}
      return { ...e, lines }
    })
    setFormError('')
  }

  const handleLineChange = (index, field) => (event) => updateLine(index, (line) => ({ ...line, [field]: event.target.value }))

  const addLine = () => {
    setValues((v) => ({ ...v, lines: [...v.lines, emptyLine()] }))
    setErrors((e) => ({ ...e, linesError: '' }))
  }

  const removeLine = (index) => {
    setValues((v) => ({ ...v, lines: v.lines.filter((_, i) => i !== index) }))
    setErrors((e) => ({ ...e, lines: e.lines?.filter((_, i) => i !== index) }))
  }

  const showServerError = (error) => {
    const code = getErrorCode(error)
    const message = getErrorMessage(error)
    const lineNumber = error?.response?.data?.error?.details?.line
    const field = FIELD_FOR_CODE[code]
    const lineField = LINE_FIELD_FOR_CODE[code]
    if (field) {
      setErrors((e) => ({ ...e, [field]: message }))
    } else if (code === 'lines_required') {
      setErrors((e) => ({ ...e, linesError: message }))
    } else if (lineField && lineNumber) {
      setErrors((e) => {
        const lines = values.lines.map((_, i) => e.lines?.[i] ?? {})
        lines[lineNumber - 1] = { ...lines[lineNumber - 1], [lineField]: message }
        return { ...e, lines }
      })
    } else {
      setFormError(message)
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (readOnly) return
    const found = validatePurchase(values, today)
    setErrors(found)
    if (Object.keys(found).length) {
      setFormError('Please fix the highlighted fields.')
      return
    }
    setFormError('')
    setSaving(true)
    try {
      const payload = toPayload(values)
      const saved = isCreate ? await createPurchase(payload) : await updatePurchase(purchaseId, payload)
      onSaved(saved, isCreate)
    } catch (error) {
      showServerError(error)
      setSaving(false)
    }
  }

  const total = grandTotalPaise(values.lines)
  const disabled = saving || readOnly
  const noVendors = options.loaded && options.vendors.length === 0
  const canReceive = Boolean(onReceive && purchase && purchase.status === 'draft' && !loadError)
  const unsaved = canReceive && savedKey !== null && payloadKey(values) !== savedKey

  let title = 'New purchase'
  if (!isCreate) title = readOnly ? `Purchase ${purchase?.purchase_number ?? ''}` : `Edit draft ${purchase?.purchase_number ?? ''}`

  let content
  if (loading) {
    content = <LoadingState message="Loading purchase…" />
  } else if (loadError) {
    content = <ErrorMessage error={loadError} onRetry={() => setAttempt((n) => n + 1)} />
  } else {
    content = (
      <>
        {readOnly ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            This purchase is {purchaseStatusLabel(purchase.status).toLowerCase()} and can no longer be changed.
          </Alert>
        ) : null}
        {formError ? (
          <Alert severity="error" sx={{ mb: 1 }} role="alert">
            {formError}
          </Alert>
        ) : null}
        {optionsError ? (
          <Alert severity="error" sx={{ mb: 1 }}>
            Could not load the vendor, stock item and category lists: {optionsError}
          </Alert>
        ) : null}

        <Grid container columnSpacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <FormField
              select
              label="Vendor"
              required
              value={options.loaded ? values.vendor_id : ''}
              onChange={handleChange('vendor_id')}
              error={errors.vendor_id}
              helperText={
                noVendors
                  ? 'No active vendor yet. Add one on the Vendors page first.'
                  : options.moreVendors
                    ? `Only active vendors are listed (first ${PICKER_PAGE_SIZE} by name).`
                    : 'Only active vendors are listed.'
              }
              disabled={disabled || !options.loaded || noVendors}
            >
              {options.vendors.map((v) => (
                <MenuItem key={v.id} value={v.id}>
                  {v.name}
                  {inactiveMark(v)}
                </MenuItem>
              ))}
            </FormField>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <FormField
              label="Invoice / reference no."
              required
              autoComplete="off"
              value={values.reference_number}
              onChange={handleChange('reference_number')}
              error={errors.reference_number}
              helperText="Unique for this vendor."
              disabled={disabled}
              slotProps={{ htmlInput: { maxLength: REFERENCE_MAX } }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <FormField
              label="Purchase date"
              required
              type="date"
              value={values.purchase_date}
              onChange={handleChange('purchase_date')}
              error={errors.purchase_date}
              helperText="Today or earlier."
              disabled={disabled}
              slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: today } }}
            />
          </Grid>
        </Grid>
        <FormField
          label="Notes"
          multiline
          minRows={2}
          value={values.notes}
          onChange={handleChange('notes')}
          error={errors.notes}
          disabled={disabled}
          slotProps={{ htmlInput: { maxLength: NOTES_MAX } }}
        />

        <Typography variant="subtitle1" component="h3" sx={{ mt: 1, mb: 1 }}>
          Lines
        </Typography>
        <Stack spacing={1.5}>
          {values.lines.map((line, index) => (
            <LineRow
              key={line.key}
              index={index}
              line={line}
              errors={errors.lines?.[index] ?? {}}
              options={options}
              disabled={disabled}
              canRemove={!readOnly && values.lines.length > 1}
              onChange={(field) => handleLineChange(index, field)}
              onTypeChange={(event) => updateLine(index, (l) => switchLineType(l, event.target.value))}
              onRemove={() => removeLine(index)}
              received={purchase?.status === 'received' ? purchase.lines[index] : null}
              onViewAsset={setViewAsset}
            />
          ))}
        </Stack>
        {errors.linesError ? (
          <Alert severity="error" sx={{ mt: 1 }}>
            {errors.linesError}
          </Alert>
        ) : null}

        <Stack direction="row" sx={{ mt: 1.5, justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
          {!readOnly ? (
            <Button startIcon={<AddOutlined />} onClick={addLine} disabled={disabled}>
              Add line
            </Button>
          ) : (
            <span />
          )}
          <Typography variant="h6" component="p" data-testid="purchase-grand-total">
            Total: {formatPaise(total)}
          </Typography>
        </Stack>
      </>
    )
  }

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="lg" fullWidth fullScreen={fullScreen}>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {title}
          {purchase ? <StatusBadge status={purchaseStatusLabel(purchase.status)} /> : null}
        </DialogTitle>
        <DialogContent dividers>{content}</DialogContent>
        <DialogActions>
          {canReceive ? (
            <Tooltip title={unsaved ? 'Save your changes first: receiving uses the saved draft.' : ''}>
              <span style={{ marginRight: 'auto' }}>
                <Button
                  variant="outlined"
                  onClick={() => onReceive(purchase)}
                  disabled={saving || unsaved}
                >
                  Receive…
                </Button>
              </span>
            </Tooltip>
          ) : null}
          <Button onClick={onClose} disabled={saving}>
            {readOnly || loadError ? 'Close' : 'Cancel'}
          </Button>
          {!readOnly && !loadError ? (
            <Button
              type="submit"
              variant="contained"
              disabled={saving || loading || !options.loaded}
              startIcon={saving ? <CircularProgress size={16} color="inherit" /> : null}
            >
              {isCreate ? 'Save draft' : 'Save changes'}
            </Button>
          ) : null}
        </DialogActions>
      </form>
      {viewAsset ? <AssetDetailsDialog open assetRef={viewAsset} onClose={() => setViewAsset(null)} /> : null}
    </Dialog>
  )
}

// On a received purchase: "Received 2 of 3: AST-000001, AST-000002" (each ID opens the asset).
function ReceivedInfo({ line, onViewAsset }) {
  const assets = line.assets ?? []
  return (
    <Typography variant="body2" sx={{ mt: 0.5 }} data-testid={`line-received-${line.id}`}>
      Received {line.received_quantity ?? 0} of {line.quantity}
      {assets.length ? ': ' : ''}
      {assets.map((a, i) => (
        <span key={a.id}>
          {i ? ', ' : ''}
          <Link component="button" type="button" underline="hover" onClick={() => onViewAsset(a.asset_code)} sx={{ verticalAlign: 'baseline' }}>
            {a.asset_code}
          </Link>
        </span>
      ))}
    </Typography>
  )
}

function LineRow({ index, line, errors, options, disabled, canRemove, onChange, onTypeChange, onRemove, received, onViewAsset }) {
  const number = index + 1
  const isBulk = line.line_type === 'bulk'
  const lineTotal = lineTotalPaise(line)
  const item = isBulk ? options.stockItems.find((s) => s.id === line.stock_item_id) : null
  const noStockItems = options.loaded && options.stockItems.length === 0
  const noCategories = options.loaded && options.categories.length === 0

  return (
    <Paper variant="outlined" sx={{ p: 1.5 }} role="group" aria-label={`Line ${number}`}>
      <Grid container columnSpacing={1.5} sx={{ alignItems: 'flex-start' }}>
        <Grid size={{ xs: 12, sm: 4, md: 2 }}>
          <FormField
            select
            size="small"
            label="Type"
            value={line.line_type}
            onChange={onTypeChange}
            disabled={disabled}
          >
            {LINE_TYPES.map((t) => (
              <MenuItem key={t.value} value={t.value}>
                {t.label}
              </MenuItem>
            ))}
          </FormField>
        </Grid>

        {isBulk ? (
          <Grid size={{ xs: 12, sm: 8, md: 4 }}>
            <FormField
              select
              size="small"
              label="Stock item"
              required
              value={options.loaded ? line.stock_item_id : ''}
              onChange={onChange('stock_item_id')}
              error={errors.stock_item_id}
              helperText={noStockItems ? 'No active stock item yet. Add one on the Inventory page.' : item ? `Unit: ${unitLabel(item.unit_of_measure)}` : ' '}
              disabled={disabled || !options.loaded || noStockItems}
            >
              {options.stockItems.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                  {inactiveMark(s)}
                </MenuItem>
              ))}
            </FormField>
          </Grid>
        ) : (
          <>
            <Grid size={{ xs: 12, sm: 8, md: 2 }}>
              <FormField
                select
                size="small"
                label="Category"
                required
                value={options.loaded ? line.category_id : ''}
                onChange={onChange('category_id')}
                error={errors.category_id}
                helperText={noCategories ? 'No active one-by-one category yet.' : ' '}
                disabled={disabled || !options.loaded || noCategories}
              >
                {options.categories.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                    {inactiveMark(c)}
                  </MenuItem>
                ))}
              </FormField>
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <FormField
                size="small"
                label="Description"
                required
                autoComplete="off"
                placeholder="Laptops: Dell Latitude 5440"
                value={line.description}
                onChange={onChange('description')}
                error={errors.description}
                disabled={disabled}
                slotProps={{ htmlInput: { maxLength: DESCRIPTION_MAX } }}
              />
            </Grid>
          </>
        )}

        <Grid size={{ xs: 4, md: 1.5 }}>
          <FormField
            size="small"
            label="Quantity"
            required
            type="number"
            value={line.quantity}
            onChange={onChange('quantity')}
            error={errors.quantity}
            disabled={disabled}
            slotProps={{ htmlInput: { min: 1, step: 1, inputMode: 'numeric' } }}
          />
        </Grid>
        <Grid size={{ xs: 8, md: 1.5 }}>
          <FormField
            size="small"
            label="Unit cost (₹)"
            required
            autoComplete="off"
            value={line.unit_cost}
            onChange={onChange('unit_cost')}
            error={errors.unit_cost}
            disabled={disabled}
            slotProps={{ htmlInput: { inputMode: 'decimal' } }}
          />
        </Grid>
        <Grid size={{ xs: 10, md: 2.5 }} sx={{ display: 'flex', alignItems: 'center', minHeight: 56 }}>
          <Box>
            <Typography variant="caption" color="text.secondary" component="div">
              Line total
            </Typography>
            <Typography variant="body1" data-testid={`line-total-${number}`}>
              {lineTotal === null ? '—' : formatPaise(lineTotal)}
            </Typography>
          </Box>
        </Grid>
        <Grid size={{ xs: 2, md: 0.5 }} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', minHeight: 56 }}>
          {canRemove ? (
            <Tooltip title="Remove line">
              <span>
                <IconButton aria-label={`Remove line ${number}`} onClick={onRemove} disabled={disabled} size="small">
                  <DeleteOutline fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          ) : null}
        </Grid>
      </Grid>
      {errors.line ? (
        <>
          <Divider sx={{ my: 1 }} />
          <Typography variant="body2" color="error">
            {errors.line}
          </Typography>
        </>
      ) : null}
      {received ? <ReceivedInfo line={received} onViewAsset={onViewAsset} /> : null}
    </Paper>
  )
}
