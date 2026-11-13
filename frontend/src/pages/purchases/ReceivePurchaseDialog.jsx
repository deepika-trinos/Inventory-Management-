// Receive a draft purchase of one-by-one items (Slice 3.2, PUR-05, PUR-06, BR-07, BR-08).
//
// One step for the whole purchase (B55):
//   - the received date (not before the purchase date, not in the future);
//   - for every line, how many arrived (0 to ordered, P4: fewer closes the line);
//   - one row per unit: serial number and model required; name (defaults to the
//     line's description), brand, warranty expiry and location optional (P5).
// A confirm box comes first (PRD 13). Then each unit becomes an asset with a new
// asset ID, and the purchase is Received (final, P6). Everything is saved together
// or not at all: one bad row (e.g. a serial number already used) saves nothing.
// A purchase with by-quantity lines cannot be received until Slice 3.3 (B56).
import { useEffect, useMemo, useState } from 'react'
import ContentCopyOutlined from '@mui/icons-material/ContentCopyOutlined'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { getPurchase, receivePurchase } from '../../api/purchases'
import ConfirmDialog from '../../components/ConfirmDialog'
import ErrorMessage from '../../components/ErrorMessage'
import FormField from '../../components/FormField'
import LoadingState from '../../components/LoadingState'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'
import {
  BRAND_MAX,
  bulkLineNumbers,
  copyFirstUnitToAll,
  LOCATION_MAX,
  MODEL_MAX,
  NAME_MAX,
  parseReceived,
  receiptValuesFromPurchase,
  SERIAL_MAX,
  setReceivedQuantity,
  toReceivePayload,
  totalUnits,
  validateReceipt,
} from './receiveForm'

// Server errors about a unit (details.line and details.unit) -> the field to mark.
const UNIT_FIELD_FOR_CODE = {
  serial_number_taken: 'serial_number',
  serial_number_duplicate: 'serial_number',
  invalid_serial_number: 'serial_number',
  invalid_model: 'model',
  invalid_asset_name: 'name',
  invalid_brand: 'brand',
  invalid_location: 'location',
}
// Server errors about a line's received quantity (details.line).
const LINE_CODES = new Set(['received_quantity_too_high', 'unit_count_mismatch', 'receipt_line_missing'])
const DATE_CODES = new Set(['received_date_in_future', 'received_date_before_purchase'])

const UNIT_COLUMNS = [
  { field: 'serial_number', label: 'Serial number', required: true, max: SERIAL_MAX, minWidth: 160 },
  { field: 'model', label: 'Model', required: true, max: MODEL_MAX, minWidth: 150 },
  { field: 'name', label: 'Name', max: NAME_MAX, minWidth: 200 },
  { field: 'brand', label: 'Brand', max: BRAND_MAX, minWidth: 120 },
  { field: 'warranty_expiry', label: 'Warranty expiry', type: 'date', minWidth: 150 },
  { field: 'location', label: 'Location', max: LOCATION_MAX, minWidth: 180 },
]

export const receiveConfirmMessage = (count, short) =>
  `This creates ${count} ${count === 1 ? 'asset' : 'assets'}, each with a new asset ID and status Available, ` +
  'and marks the purchase Received. Receiving is final: the purchase can no longer be edited or cancelled.' +
  (short ? ' Lines with fewer units than ordered are closed: the missing units will not be received later.' : '')

export default function ReceivePurchaseDialog({ open, purchaseId, onClose, onReceived }) {
  const theme = useTheme()
  const fullScreen = useMediaQuery(theme.breakpoints.down('md'))
  const today = useMemo(() => todayInCompanyTimezone(), [])

  const [purchase, setPurchase] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [attempt, setAttempt] = useState(0)
  const [values, setValues] = useState(null)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoadError(null)
    getPurchase(purchaseId)
      .then((found) => {
        if (cancelled) return
        setPurchase(found)
        setValues(receiptValuesFromPurchase(found, today))
      })
      .catch((err) => !cancelled && setLoadError(err))
    return () => {
      cancelled = true
    }
  }, [purchaseId, attempt, today])

  const bulkLines = purchase ? bulkLineNumbers(purchase) : []
  const canReceive = Boolean(purchase && purchase.status === 'draft' && bulkLines.length === 0)

  const clearLineErrors = (index) => {
    setErrors((e) => {
      if (!e.lines?.[index]) return e
      const lines = [...e.lines]
      lines[index] = { units: [] }
      return { ...e, lines }
    })
    setFormError('')
  }

  const updateLine = (index, change) => {
    setValues((v) => ({ ...v, lines: v.lines.map((line, i) => (i === index ? change(line) : line)) }))
    clearLineErrors(index)
  }

  const updateUnit = (lineIndex, unitIndex, field, value) =>
    updateLine(lineIndex, (line) => ({
      ...line,
      units: line.units.map((u, i) => (i === unitIndex ? { ...u, [field]: value } : u)),
    }))

  const showServerError = (error) => {
    const code = getErrorCode(error)
    const message = getErrorMessage(error)
    const details = error?.response?.data?.error?.details ?? {}
    const lineIndex = details.line ? details.line - 1 : -1
    const unitIndex = details.unit ? details.unit - 1 : -1
    const unitField = UNIT_FIELD_FOR_CODE[code]

    if (DATE_CODES.has(code)) {
      setErrors((e) => ({ ...e, received_date: message }))
    } else if (unitField && lineIndex >= 0 && unitIndex >= 0 && values.lines[lineIndex]) {
      setErrors((e) => {
        const lines = values.lines.map((l, i) => e.lines?.[i] ?? { units: [] })
        const units = values.lines[lineIndex].units.map((_, i) => lines[lineIndex].units?.[i] ?? {})
        units[unitIndex] = { ...units[unitIndex], [unitField]: message }
        lines[lineIndex] = { ...lines[lineIndex], units }
        return { ...e, lines }
      })
      setFormError('Please fix the highlighted fields. Nothing was saved.')
      return
    } else if (LINE_CODES.has(code) && lineIndex >= 0 && values.lines[lineIndex]) {
      setErrors((e) => {
        const lines = values.lines.map((l, i) => e.lines?.[i] ?? { units: [] })
        lines[lineIndex] = { ...lines[lineIndex], received_quantity: message }
        return { ...e, lines }
      })
    }
    setFormError(`${message} Nothing was saved.`)
  }

  // "Receive…": check the form, then ask for confirmation.
  const handleSubmit = (event) => {
    event.preventDefault()
    if (!canReceive) return
    const found = validateReceipt(values, { purchaseDate: purchase.purchase_date, today })
    setErrors(found)
    if (Object.keys(found).length) {
      setFormError(found.form ?? 'Please fix the highlighted fields.')
      return
    }
    setFormError('')
    setConfirming(true)
  }

  const doReceive = async () => {
    try {
      const saved = await receivePurchase(purchase.id, toReceivePayload(values))
      setConfirming(false)
      onReceived(saved)
    } catch (error) {
      setConfirming(false)
      showServerError(error)
    }
  }

  const count = values ? totalUnits(values) : 0
  const short = values ? values.lines.some((line) => (parseReceived(line) ?? line.ordered) < line.ordered) : false

  let content
  if (loadError) {
    content = <ErrorMessage error={loadError} onRetry={() => setAttempt((n) => n + 1)} />
  } else if (!purchase || !values) {
    content = <LoadingState message="Loading purchase…" />
  } else {
    content = (
      <>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {purchase.vendor.name} · Invoice / ref. {purchase.reference_number} · Purchased{' '}
          {formatPlainDate(purchase.purchase_date)}
        </Typography>

        {purchase.status !== 'draft' ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Only a draft purchase can be received. {purchase.purchase_number} is {purchase.status}.
          </Alert>
        ) : null}
        {purchase.status === 'draft' && bulkLines.length ? (
          <Alert severity="warning" sx={{ mb: 2 }}>
            This purchase has by-quantity {bulkLines.length === 1 ? 'line' : 'lines'} ({bulkLines.map((n) => `line ${n}`).join(', ')}).
            Receiving by-quantity items arrives in Slice 3.3, so this purchase cannot be received yet.
          </Alert>
        ) : null}
        {formError ? (
          <Alert severity="error" sx={{ mb: 1 }} role="alert">
            {formError}
          </Alert>
        ) : null}

        {canReceive ? (
          <>
            <Grid container columnSpacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <FormField
                  label="Received date"
                  required
                  type="date"
                  value={values.received_date}
                  onChange={(e) => {
                    setValues((v) => ({ ...v, received_date: e.target.value }))
                    setErrors((er) => ({ ...er, received_date: '' }))
                    setFormError('')
                  }}
                  error={errors.received_date}
                  helperText={`From ${formatPlainDate(purchase.purchase_date)} to today.`}
                  slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: purchase.purchase_date, max: today } }}
                />
              </Grid>
            </Grid>

            <Stack spacing={2} sx={{ mt: 1 }}>
              {values.lines.map((line, index) => (
                <ReceiveLine
                  key={line.line_id}
                  line={line}
                  errors={errors.lines?.[index] ?? { units: [] }}
                  onQuantityChange={(value) => updateLine(index, (l) => setReceivedQuantity(l, value))}
                  onUnitChange={(unitIndex, field, value) => updateUnit(index, unitIndex, field, value)}
                  onCopyFirst={() => updateLine(index, copyFirstUnitToAll)}
                />
              ))}
            </Stack>
          </>
        ) : null}
      </>
    )
  }

  return (
    <Dialog open={open} onClose={confirming ? undefined : onClose} maxWidth="xl" fullWidth fullScreen={fullScreen}>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>Receive {purchase?.purchase_number ?? 'purchase'}</DialogTitle>
        <DialogContent dividers>{content}</DialogContent>
        <DialogActions>
          {canReceive ? (
            <Typography variant="body2" color="text.secondary" sx={{ mr: 'auto', pl: 1 }} data-testid="receive-count">
              {count} {count === 1 ? 'asset' : 'assets'} will be created
            </Typography>
          ) : null}
          <Button onClick={onClose}>{canReceive ? 'Cancel' : 'Close'}</Button>
          {canReceive ? (
            <Button type="submit" variant="contained">
              Receive…
            </Button>
          ) : null}
        </DialogActions>
      </form>

      <ConfirmDialog
        open={confirming}
        title={`Receive ${purchase?.purchase_number ?? ''}?`}
        message={receiveConfirmMessage(count, short)}
        confirmLabel="Receive"
        cancelLabel="Go back"
        onCancel={() => setConfirming(false)}
        onConfirm={doReceive}
      />
    </Dialog>
  )
}

function ReceiveLine({ line, errors, onQuantityChange, onUnitChange, onCopyFirst }) {
  const received = parseReceived(line)
  return (
    <Paper variant="outlined" sx={{ p: 1.5 }} role="group" aria-label={`Line ${line.number}`}>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { sm: 'flex-start' } }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle1" component="h3">
            Line {line.number}: {line.description}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {line.category} · Ordered: {line.ordered}
          </Typography>
        </Box>
        <Box sx={{ width: { xs: '100%', sm: 220 } }}>
          <FormField
            size="small"
            label="Received quantity"
            required
            type="number"
            value={line.received_quantity}
            onChange={(e) => onQuantityChange(e.target.value)}
            error={errors.received_quantity}
            helperText={`0 to ${line.ordered}. Fewer closes the line.`}
            slotProps={{ htmlInput: { min: 0, max: line.ordered, step: 1, inputMode: 'numeric' } }}
          />
        </Box>
      </Stack>

      {received === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Nothing arrived for this line. It will be closed with 0 received.
        </Typography>
      ) : null}

      {line.units.length ? (
        <>
          {line.units.length > 1 ? (
            <Button size="small" startIcon={<ContentCopyOutlined />} onClick={onCopyFirst} sx={{ mt: 1 }}>
              Copy unit 1&apos;s model, brand, warranty and location to all units
            </Button>
          ) : null}
          <TableContainer sx={{ mt: 1, overflowX: 'auto' }}>
            <Table size="small" aria-label={`Units for line ${line.number}`}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: 40 }}>#</TableCell>
                  {UNIT_COLUMNS.map((c) => (
                    <TableCell key={c.field} sx={{ minWidth: c.minWidth }}>
                      {c.label}
                      {c.required ? ' *' : ''}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {line.units.map((unit, ui) => (
                  <TableRow key={unit.key}>
                    <TableCell>{ui + 1}</TableCell>
                    {UNIT_COLUMNS.map((c) => {
                      const problem = errors.units?.[ui]?.[c.field]
                      return (
                        <TableCell key={c.field} sx={{ verticalAlign: 'top' }}>
                          <TextField
                            size="small"
                            fullWidth
                            type={c.type ?? 'text'}
                            value={unit[c.field]}
                            onChange={(e) => onUnitChange(ui, c.field, e.target.value)}
                            error={Boolean(problem)}
                            helperText={problem || (c.field === 'name' && !unit.name ? 'Empty = line description' : '')}
                            placeholder={c.field === 'name' ? line.description : undefined}
                            autoComplete="off"
                            slotProps={{
                              htmlInput: {
                                'aria-label': `Line ${line.number} unit ${ui + 1} ${c.label.toLowerCase()}`,
                                ...(c.max ? { maxLength: c.max } : {}),
                              },
                            }}
                          />
                        </TableCell>
                      )
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : null}
    </Paper>
  )
}
