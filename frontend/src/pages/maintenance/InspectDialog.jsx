// The inspection after a repair (Slice 6.3: MNT-07, workflow 7.4; owner's answers in decisions.md
// section 35). Opened from the request page and the asset page with the same form, for a request that is
// Completed, or Cancelled after work started (`awaiting_inspection`).
//
// Form (same wording as the return's inspection, N4 / K8): inspection date (today by default, between the
// completion date - or the day it was cancelled - and today), outcome (Available / Damaged / Retired) and
// condition notes (0 / 1,000; required for Damaged and Retired; for Retired they are the reason for
// retiring, so 0 / 500). Then a confirm box; for Retired it says this is permanent.
//
//   <InspectDialog request={r} onClose onSaved />   onSaved(the request with its history)
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

import { getErrorCode, getErrorMessage } from '../../api/errors'
import {
  CONDITION_NOTES_MAX,
  earliestInspectionDate,
  INSPECTION_OUTCOME_LABELS,
  INSPECTION_RETIRE_NOTES_MAX,
  inspectRequest,
} from '../../api/maintenance'
import ConfirmDialog from '../../components/ConfirmDialog'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'

const FIELD_FOR_CODE = {
  invalid_inspection_outcome: 'outcome',
  condition_notes_required: 'notes',
  invalid_condition_notes: 'notes',
  invalid_retire_reason: 'notes',
  inspection_date_in_future: 'date',
  inspection_date_before_completion: 'date',
}

/** Notes are required unless the outcome is Available (as N4). */
export function inspectionNotesRequired(outcome) {
  return Boolean(outcome) && outcome !== 'available'
}

/** The notes limit: 500 for Retired (the retirement reason, A3), otherwise 1,000. */
export function inspectionNotesMax(outcome) {
  return outcome === 'retired' ? INSPECTION_RETIRE_NOTES_MAX : CONDITION_NOTES_MAX
}

export function validateInspection({ date, outcome, notes }, earliest, today = todayInCompanyTimezone()) {
  const errors = {}
  if (!date) errors.date = 'Please enter the inspection date.'
  else if (date > today) errors.date = 'The inspection date cannot be in the future.'
  else if (earliest && date < earliest) errors.date = `The inspection date cannot be before ${formatPlainDate(earliest)}.`
  if (!outcome) errors.outcome = 'Choose the inspection outcome.'
  const text = notes.trim()
  if (!text && inspectionNotesRequired(outcome)) {
    errors.notes = `Please describe the condition: required when the outcome is ${INSPECTION_OUTCOME_LABELS[outcome]}.`
  } else if (text.length > inspectionNotesMax(outcome)) {
    errors.notes = `Use at most ${inspectionNotesMax(outcome).toLocaleString('en-IN')} characters.`
  }
  return errors
}

/** The confirm box's lines: what happens to the asset. */
export function inspectionConfirmLines({ date, outcome, notes }, request) {
  const code = request.asset.asset_code
  const label = INSPECTION_OUTCOME_LABELS[outcome]
  const text = notes.trim()
  return [
    `${code} becomes ${label}.`,
    outcome === 'available' ? 'It can be assigned again.' : null,
    outcome === 'damaged' ? 'It cannot be assigned. A new problem can be reported for it.' : null,
    outcome === 'retired' ? 'This retires the asset permanently. It cannot be undone, and the asset becomes read-only.' : null,
    `Inspected on ${formatPlainDate(date)}.`,
    text ? `${outcome === 'retired' ? 'Reason for retiring' : 'Condition'}: ${text}` : 'No condition notes.',
    'An inspection is final and cannot be changed.',
  ].filter(Boolean)
}

export default function InspectDialog({ request, onClose, onSaved }) {
  const today = todayInCompanyTimezone()
  const earliest = earliestInspectionDate(request)
  const [values, setValues] = useState({ date: today, outcome: '', notes: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [confirming, setConfirming] = useState(false)

  const set = (field) => (event) => {
    const value = event.target.value
    setValues((v) => ({ ...v, [field]: value }))
    // Changing the outcome can make the notes required or change their limit: re-check them then.
    setErrors((e) => ({ ...e, [field]: '', ...(field === 'outcome' ? { notes: '' } : {}) }))
    setFormError('')
  }

  const review = (event) => {
    event.preventDefault()
    const found = validateInspection(values, earliest, today)
    setErrors(found)
    if (Object.keys(found).length === 0) setConfirming(true)
  }

  const save = async () => {
    try {
      const saved = await inspectRequest(request.request_number, {
        outcome: values.outcome,
        inspectionDate: values.date,
        notes: values.notes.trim(),
      })
      onSaved(saved)
    } catch (error) {
      setConfirming(false)
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error)) // e.g. someone else inspected it a moment ago
    }
  }

  const required = inspectionNotesRequired(values.outcome)
  const max = inspectionNotesMax(values.outcome)
  const label = INSPECTION_OUTCOME_LABELS[values.outcome]
  const after = request.completion_date ? 'the completion date' : 'the day the request was cancelled'

  return (
    <>
      <Dialog open={!confirming} onClose={onClose} maxWidth="sm" fullWidth>
        <form onSubmit={review} noValidate>
          <DialogTitle>
            Inspect {request.asset.asset_code} after {request.request_number}
          </DialogTitle>
          <DialogContent>
            {formError ? (
              <Alert severity="error" sx={{ mb: 1 }} data-testid="inspect-form-error">
                {formError}
              </Alert>
            ) : null}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              The outcome becomes the asset&apos;s status. It stays Under Maintenance until the inspection is saved.
            </Typography>
            <FormField
              label="Inspection date"
              required
              type="date"
              value={values.date}
              onChange={set('date')}
              error={errors.date}
              helperText={`Today or earlier, not before ${after} (${formatPlainDate(earliest)}).`}
              slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: earliest, max: today } }}
            />
            <FormLabel id="inspect-outcome-label" required sx={{ mt: 1, display: 'block' }}>
              Inspection outcome
            </FormLabel>
            <RadioGroup aria-labelledby="inspect-outcome-label" value={values.outcome} onChange={set('outcome')}>
              {Object.entries(INSPECTION_OUTCOME_LABELS).map(([value, text]) => (
                <FormControlLabel key={value} value={value} control={<Radio />} label={text} />
              ))}
            </RadioGroup>
            {errors.outcome ? (
              <Typography variant="caption" color="error" role="alert">
                {errors.outcome}
              </Typography>
            ) : null}
            <FormField
              label={
                values.outcome === 'retired'
                  ? 'Condition notes (reason for retiring)'
                  : required
                    ? 'Condition notes'
                    : 'Condition notes (optional)'
              }
              required={required}
              multiline
              minRows={3}
              value={values.notes}
              onChange={set('notes')}
              error={errors.notes}
              helperText={`${values.notes.trim().length} / ${max.toLocaleString('en-IN')}${required ? ' · required for this outcome' : ''}`}
              placeholder={required ? 'e.g. Hinge still loose' : 'e.g. Tested, works fine'}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Close</Button>
            <Button type="submit" variant="contained">
              Inspect…
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <ConfirmDialog
        open={confirming}
        title={`Inspect ${request.asset.asset_code} after ${request.request_number} — result: ${label}?`}
        confirmLabel={values.outcome === 'retired' ? 'Retire the asset' : 'Save inspection'}
        cancelLabel="Go back"
        destructive={values.outcome !== 'available'}
        onCancel={() => setConfirming(false)}
        onConfirm={save}
      >
        {inspectionConfirmLines(values, request).map((line) => (
          <Typography key={line} variant="body2" sx={{ mb: 0.5 }} data-testid="inspect-confirm-line">
            {line}
          </Typography>
        ))}
      </ConfirmDialog>
    </>
  )
}
