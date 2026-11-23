// Issue or adjust stock (Slice 4.4: INV-04, INV-07, BR-09, BR-10; owner's answers Q7, A4,
// A5, A4-5a/b), opened from the stock item page as two separate actions:
//   mode="issue"  : quantity, required reason, optional ACTIVE employee who received it
//   mode="adjust" : Add or Remove, quantity, required reason
//   mode="opening": quantity, optional note (Slice 4.5, INV-01; owner's answer A6): once
//                   per item, only while it has no movements; the history shows "Opening stock"
// All: date (today by default; earlier allowed; never in the future). After the form,
// a confirm box shows the balance now and after the change (no approval step, Q7).
// Stock never goes below 0: the screen checks first and the server refuses it again
// (insufficient_stock). Server problems are shown under the field they belong to.
import { useState } from 'react'
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Radio,
  RadioGroup,
  Typography,
} from '@mui/material'

import { employeeLabel } from '../../api/employees'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import { adjustStock, enterOpeningStock, issueStock, unitLabel } from '../../api/stockItems'
import ConfirmDialog from '../../components/ConfirmDialog'
import EmployeePicker from '../../components/EmployeePicker'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'

export const REASON_MAX = 500
export const QUANTITY_MAX = 1_000_000

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  insufficient_stock: 'quantity',
  invalid_reason: 'reason',
  movement_date_in_future: 'movementDate',
  employee_inactive: 'employee',
  employee_not_found: 'employee',
}

const OPENING_HINT = 'Opening stock can be entered once, before any other movement. Later corrections are made with Adjust.'

/** The change in stock: negative for an issue or a removal. */
export function stockChange(mode, direction, quantity) {
  return mode === 'issue' || direction === 'remove' ? -quantity : quantity
}

export function validateStockChange({ mode, direction, quantity, reason, movementDate }, onHand, today = todayInCompanyTimezone()) {
  const errors = {}
  const n = Number(quantity)
  if (!/^\d+$/.test(String(quantity).trim()) || n < 1) errors.quantity = 'Enter a whole number, 1 or more.'
  else if (n > QUANTITY_MAX) errors.quantity = `Use at most ${QUANTITY_MAX.toLocaleString('en-IN')}.`
  else if ((mode === 'issue' || direction === 'remove') && n > onHand) {
    errors.quantity = onHand === 0 ? 'Nothing is in stock.' : `Only ${onHand} in stock.`
  }
  if (mode === 'adjust' && !direction) errors.direction = 'Choose Add or Remove.'
  const text = reason.trim()
  if (!text && mode !== 'opening') errors.reason = 'Please enter the reason.'
  else if (text.length > REASON_MAX) errors.reason = `Use at most ${REASON_MAX} characters.`
  if (!movementDate) errors.movementDate = 'Please enter the date.'
  else if (movementDate > today) errors.movementDate = 'The date cannot be in the future.'
  return errors
}

export default function StockChangeDialog({ open, mode, item, onClose, onSaved }) {
  const issue = mode === 'issue'
  const opening = mode === 'opening'
  const unit = unitLabel(item.unit_of_measure).toLowerCase()
  const today = todayInCompanyTimezone()
  const [values, setValues] = useState({ direction: issue ? 'remove' : opening ? 'add' : '', quantity: '', reason: '', movementDate: today })
  const [employee, setEmployee] = useState(null)
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [confirming, setConfirming] = useState(false)

  const set = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }

  const quantity = Number(values.quantity)
  const change = stockChange(mode, values.direction, quantity)
  const after = item.quantity_on_hand + change

  const review = (event) => {
    event.preventDefault()
    const found = validateStockChange({ mode, ...values }, item.quantity_on_hand, today)
    setErrors(found)
    if (Object.keys(found).length === 0) setConfirming(true)
  }

  const save = async () => {
    const common = { quantity, reason: values.reason.trim(), movementDate: values.movementDate }
    try {
      let result
      if (issue) result = await issueStock(item.id, { ...common, employeeId: employee?.id })
      else if (opening) result = await enterOpeningStock(item.id, { quantity, note: common.reason, movementDate: values.movementDate })
      else result = await adjustStock(item.id, { ...common, direction: values.direction })
      onSaved(result)
    } catch (error) {
      setConfirming(false)
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error))
    }
  }

  const title = issue ? `Issue ${item.name}` : opening ? `Opening stock: ${item.name}` : `Adjust ${item.name}`
  const verb = issue ? 'Issue' : opening ? 'Enter' : values.direction === 'add' ? 'Add' : 'Remove'
  const confirmTitle = opening
    ? `Enter opening stock of ${quantity} ${unit} for ${item.name}?`
    : `${verb} ${quantity} ${unit}${issue ? ' of' : values.direction === 'add' ? ' to' : ' from'} ${item.name}?`
  const note = values.reason.trim()
  const details = [
    opening
      ? `On hand: ${item.quantity_on_hand} → ${after} ${unit}.`
      : `On hand now: ${item.quantity_on_hand} ${unit} · after: ${after} ${unit}.`,
    issue && employee ? `Issued to ${employeeLabel(employee)}.` : null,
    opening
      ? `Date: ${formatPlainDate(values.movementDate)}.${note ? ` Note: ${note}` : ''}`
      : `Date: ${formatPlainDate(values.movementDate)}. Reason: ${note}`,
    opening ? OPENING_HINT : 'Stock movements are permanent: a mistake is corrected with a new adjustment.',
  ].filter(Boolean)

  return (
    <>
      <Dialog open={open && !confirming} onClose={onClose} maxWidth="sm" fullWidth>
        <form onSubmit={review} noValidate>
          <DialogTitle>{title}</DialogTitle>
          <DialogContent>
            {formError ? (
              <Alert severity="error" sx={{ mb: 1 }}>
                {formError}
              </Alert>
            ) : null}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }} data-testid="stock-change-on-hand">
              On hand now: {item.quantity_on_hand} {unit}
              {values.quantity && !errors.quantity && quantity > 0 ? ` · after: ${after} ${unit}` : ''}
            </Typography>
            {opening ? (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                The count already on the shelf when you start using the system. {OPENING_HINT}
              </Typography>
            ) : null}
            {!issue && !opening ? (
              <>
                <RadioGroup row aria-label="Add or remove" value={values.direction} onChange={set('direction')}>
                  <FormControlLabel value="add" control={<Radio />} label="Add (found, counted more)" />
                  <FormControlLabel value="remove" control={<Radio />} label="Remove (broken, lost, counted less)" />
                </RadioGroup>
                {errors.direction ? (
                  <Typography variant="caption" color="error" role="alert">
                    {errors.direction}
                  </Typography>
                ) : null}
              </>
            ) : null}
            <FormField
              label="Quantity"
              required
              autoFocus
              type="number"
              value={values.quantity}
              onChange={set('quantity')}
              error={errors.quantity}
              helperText={`In ${unit}.`}
              slotProps={{ htmlInput: { min: 1, step: 1 } }}
            />
            {issue ? (
              <EmployeePicker
                label="Issued to (optional)"
                value={employee}
                onChange={(e) => {
                  setEmployee(e)
                  setErrors((x) => ({ ...x, employee: '' }))
                }}
                onlyWithoutLogin={false}
                error={errors.employee}
                helperText="Leave empty for a room, event or team, and say so in the reason."
              />
            ) : null}
            <FormField
              label={opening ? 'Note (optional)' : 'Reason'}
              required={!opening}
              multiline
              minRows={2}
              value={values.reason}
              onChange={set('reason')}
              error={errors.reason}
              helperText={`${values.reason.trim().length} / ${REASON_MAX}`}
              placeholder={issue ? 'e.g. New joiner kit for Asha Kumar' : opening ? 'e.g. Counted in the store room' : 'e.g. Three broken, scrapped'}
            />
            <FormField
              label="Date"
              required
              type="date"
              value={values.movementDate}
              onChange={set('movementDate')}
              error={errors.movementDate}
              helperText="Today or earlier."
              slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: today } }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="submit" variant="contained">
              {issue ? 'Issue…' : opening ? 'Continue…' : 'Adjust…'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <ConfirmDialog
        open={open && confirming}
        title={confirmTitle}
        confirmLabel={issue ? 'Issue' : opening ? 'Enter opening stock' : verb}
        cancelLabel="Go back"
        destructive={change < 0}
        onCancel={() => setConfirming(false)}
        onConfirm={save}
      >
        {details.map((line) => (
          <Typography key={line} variant="body2" sx={{ mb: 0.5 }} data-testid="stock-change-confirm-line">
            {line}
          </Typography>
        ))}
      </ConfirmDialog>
    </>
  )
}
