// Return an asset with its inspection, on ONE form (Slice 5.2: ASN-05, ASN-06, BR-04;
// owner's answers Q5, N4, N5), opened from the asset page's "Return…" button (only while
// the asset is Assigned).
// Form: return date (today by default; earlier allowed; not before the assignment date; never
// in the future), inspection outcome (Available / Under Maintenance / Damaged) and condition
// notes (counter 0 / 1,000; required when the outcome is not Available). Then a confirm box
// with the holder, the dates and the new status. Under Maintenance sets the status only: no
// maintenance request is opened (N5). The server checks everything again; its problems are
// shown under the field they belong to.
import { useState } from 'react'
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  FormLabel,
  Radio,
  RadioGroup,
  Typography,
} from '@mui/material'

import { assetStatusLabel, RETURN_OUTCOMES, returnAsset } from '../../api/assets'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import ConfirmDialog from '../../components/ConfirmDialog'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'
import { employeeName } from './AssetAssignDialog'

export const NOTES_MAX = 1000

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  return_date_in_future: 'returnDate',
  return_date_before_assignment: 'returnDate',
  invalid_inspection_outcome: 'outcome',
  condition_notes_required: 'notes',
  invalid_condition_notes: 'notes',
}

/** Notes are required unless the outcome is Available (N4). */
export function notesRequired(outcome) {
  return Boolean(outcome) && outcome !== 'available'
}

export function validateReturn({ returnDate, outcome, notes }, assignmentDate, today = todayInCompanyTimezone()) {
  const errors = {}
  if (!returnDate) errors.returnDate = 'Please enter the return date.'
  else if (returnDate > today) errors.returnDate = 'The return date cannot be in the future.'
  else if (returnDate < assignmentDate) {
    errors.returnDate = `The return date cannot be before the assignment date (${formatPlainDate(assignmentDate)}).`
  }
  if (!outcome) errors.outcome = 'Choose the inspection outcome.'
  const text = notes.trim()
  if (!text && notesRequired(outcome)) {
    errors.notes = `Please describe the condition: required when the outcome is ${assetStatusLabel(outcome)}.`
  } else if (text.length > NOTES_MAX) errors.notes = `Use at most ${NOTES_MAX.toLocaleString('en-IN')} characters.`
  return errors
}

export default function AssetReturnDialog({ open, asset, onClose, onReturned }) {
  const holder = asset.current_assignment
  const today = todayInCompanyTimezone()
  const [values, setValues] = useState({ returnDate: today, outcome: '', notes: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [confirming, setConfirming] = useState(false)

  const set = (field) => (event) => {
    const value = event.target.value
    setValues((v) => ({ ...v, [field]: value }))
    // Changing the outcome can make the notes required or not: re-check them then.
    setErrors((e) => ({ ...e, [field]: '', ...(field === 'outcome' ? { notes: '' } : {}) }))
    setFormError('')
  }

  const review = (event) => {
    event.preventDefault()
    const found = validateReturn(values, holder.assignment_date, today)
    setErrors(found)
    if (Object.keys(found).length === 0) setConfirming(true)
  }

  const save = async () => {
    try {
      const saved = await returnAsset(asset.asset_code, {
        returnDate: values.returnDate,
        outcome: values.outcome,
        notes: values.notes.trim(),
      })
      onReturned(saved, values.outcome)
    } catch (error) {
      setConfirming(false)
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error)) // e.g. someone else returned it a moment ago
    }
  }

  const required = notesRequired(values.outcome)
  const count = values.notes.trim().length
  const note = values.notes.trim()
  const details = [
    `Returned by ${employeeName(holder.employee)}.`,
    `Assigned on ${formatPlainDate(holder.assignment_date)} · returned on ${formatPlainDate(values.returnDate)}.`,
    `New status: ${assetStatusLabel(values.outcome)}.`,
    note ? `Condition: ${note}` : 'No condition notes.',
    values.outcome === 'under_maintenance' ? 'This sets the status only; no maintenance request is opened.' : null,
  ].filter(Boolean)

  return (
    <>
      <Dialog open={open && !confirming} onClose={onClose} maxWidth="sm" fullWidth>
        <form onSubmit={review} noValidate>
          <DialogTitle>Return {asset.asset_code}</DialogTitle>
          <DialogContent>
            {formError ? (
              <Alert severity="error" sx={{ mb: 1 }}>
                {formError}
              </Alert>
            ) : null}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }} data-testid="return-holder">
              Held by {employeeName(holder.employee)} since {formatPlainDate(holder.assignment_date)}
            </Typography>
            <FormField
              label="Return date"
              required
              type="date"
              value={values.returnDate}
              onChange={set('returnDate')}
              error={errors.returnDate}
              helperText={`Today or earlier, not before the assignment date (${formatPlainDate(holder.assignment_date)}).`}
              slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: holder.assignment_date, max: today } }}
            />
            <FormLabel id="return-outcome-label" required sx={{ mt: 1, display: 'block' }}>
              Inspection outcome
            </FormLabel>
            <RadioGroup aria-labelledby="return-outcome-label" value={values.outcome} onChange={set('outcome')}>
              {RETURN_OUTCOMES.map((value) => (
                <FormControlLabel key={value} value={value} control={<Radio />} label={assetStatusLabel(value)} />
              ))}
            </RadioGroup>
            {errors.outcome ? (
              <Typography variant="caption" color="error" role="alert">
                {errors.outcome}
              </Typography>
            ) : null}
            <FormField
              label={required ? 'Condition notes' : 'Condition notes (optional)'}
              required={required}
              multiline
              minRows={3}
              value={values.notes}
              onChange={set('notes')}
              error={errors.notes}
              helperText={`${count} / ${NOTES_MAX.toLocaleString('en-IN')}${required ? ' · required for this outcome' : ''}`}
              placeholder={required ? 'e.g. Screen cracked' : 'e.g. Minor scratches, works fine'}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="submit" variant="contained">
              Return…
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <ConfirmDialog
        open={open && confirming}
        title={`Return ${asset.asset_code} as ${assetStatusLabel(values.outcome)}?`}
        confirmLabel="Return"
        cancelLabel="Go back"
        destructive={values.outcome !== 'available'}
        onCancel={() => setConfirming(false)}
        onConfirm={save}
      >
        {details.map((line) => (
          <Typography key={line} variant="body2" sx={{ mb: 0.5 }} data-testid="return-confirm-line">
            {line}
          </Typography>
        ))}
      </ConfirmDialog>
    </>
  )
}
