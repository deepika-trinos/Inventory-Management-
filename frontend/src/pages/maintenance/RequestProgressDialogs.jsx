// The request page's forms (Slice 6.2: MNT-04, MNT-05; owner's answers S1-S12). Each status change is
// a form, then a confirm box (PRD 13); Edit details saves directly. The server checks everything
// again; its problems are shown under the field they belong to (or on top).
//
//   <StartWorkDialog request={r} onClose onSaved />   Reported -> In Progress (asset Under Maintenance)
//   <CompleteDialog request={r} onClose onSaved />    In Progress -> Completed (asset stays Under Maintenance)
//   <CancelDialog request={r} onClose onSaved />      Reported / In Progress -> Cancelled (final)
//   <EditRequestDialog request={r} onClose onSaved /> priority, provider, notes, cost while open
import { useState } from 'react'
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Typography } from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import {
  CANCEL_REASON_MAX,
  cancelRequest,
  completeWork,
  PRIORITY_LABELS,
  REPAIR_NOTES_MAX,
  SERVICE_PROVIDER_MAX,
  startWork,
  updateRequest,
} from '../../api/maintenance'
import ConfirmDialog from '../../components/ConfirmDialog'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'
import { formatAmount } from '../../utils/money'

const COST_PATTERN = /^\d{1,10}(\.\d{1,2})?$/ // S6: 0 or more, 2 decimals, NUMERIC(12,2)

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  started_date_in_future: 'date',
  started_date_before_reported: 'date',
  completion_date_in_future: 'date',
  completion_date_before_start: 'date',
  invalid_service_provider: 'provider',
  invalid_repair_notes: 'notes',
  invalid_cancel_reason: 'reason',
}

const count = (value, max) => `${value.trim().length} / ${max.toLocaleString('en-IN')}`

export function validateProgress(kind, values, request, today = todayInCompanyTimezone()) {
  const errors = {}
  const minDate = kind === 'start' ? request.reported_date : request.started_date
  if (kind === 'start' || kind === 'complete') {
    if (!values.date) errors.date = 'Please enter the date.'
    else if (values.date > today) errors.date = 'The date cannot be in the future.'
    else if (minDate && values.date < minDate) {
      errors.date =
        kind === 'start'
          ? `Work cannot start before the problem was reported (${formatPlainDate(minDate)}).`
          : `The completion date cannot be before work started (${formatPlainDate(minDate)}).`
    }
    if (values.provider.trim().length > SERVICE_PROVIDER_MAX) errors.provider = `Use at most ${SERVICE_PROVIDER_MAX} characters.`
  }
  if (kind === 'complete') {
    const notes = values.notes.trim()
    if (!notes) errors.notes = 'Please describe what was done.'
    else if (notes.length > REPAIR_NOTES_MAX) errors.notes = `Use at most ${REPAIR_NOTES_MAX.toLocaleString('en-IN')} characters.`
    if (values.cost.trim() && !COST_PATTERN.test(values.cost.trim())) errors.cost = 'Enter an amount of 0 or more with up to 2 decimals.'
  }
  if (kind === 'cancel') {
    const reason = values.reason.trim()
    if (!reason) errors.reason = 'Please give the reason for cancelling.'
    else if (reason.length > CANCEL_REASON_MAX) errors.reason = `Use at most ${CANCEL_REASON_MAX} characters.`
  }
  return errors
}

const KINDS = {
  start: {
    title: (r) => `Start work on ${r.request_number}`,
    button: 'Start work…',
    confirmTitle: (r) => `Start work on ${r.request_number}?`,
    confirmLabel: 'Start work',
  },
  complete: {
    title: (r) => `Mark ${r.request_number} completed`,
    button: 'Mark completed…',
    confirmTitle: (r) => `Mark ${r.request_number} completed?`,
    confirmLabel: 'Mark completed',
  },
  cancel: {
    title: (r) => `Cancel ${r.request_number}`,
    button: 'Cancel request…',
    confirmTitle: (r) => `Cancel ${r.request_number}?`,
    confirmLabel: 'Cancel request',
  },
}

/** The confirm box's lines for each kind (what will happen to the asset). */
export function confirmLines(kind, values, request) {
  const code = request.asset.asset_code
  if (kind === 'start') {
    return [
      `${code} becomes Under Maintenance and cannot be assigned until it is inspected.`,
      `Work started on ${formatPlainDate(values.date)}.`,
      values.provider.trim() ? `Service provider: ${values.provider.trim()}` : null,
    ]
  }
  if (kind === 'complete') {
    return [
      `${code} stays Under Maintenance until it is inspected.`,
      `Completed on ${formatPlainDate(values.date)}.`,
      `Repair notes: ${values.notes.trim()}`,
      values.provider.trim() ? `Service provider: ${values.provider.trim()}` : null,
      values.cost.trim() ? `Cost: ${formatAmount(values.cost.trim())}` : 'No cost recorded.',
      'A completed request cannot be changed any more.',
    ]
  }
  return [
    `Reason: ${values.reason.trim()}`,
    request.status === 'in_progress'
      ? `${code} stays Under Maintenance until it is inspected.`
      : `${code} keeps its status.`,
    'This cannot be undone.',
  ]
}

function ProgressDialog({ kind, request, onClose, onSaved }) {
  const today = todayInCompanyTimezone()
  const [values, setValues] = useState({
    date: today,
    provider: request.service_provider ?? '',
    notes: request.repair_notes ?? '',
    cost: request.cost ?? '',
    reason: '',
  })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [confirming, setConfirming] = useState(false)
  const k = KINDS[kind]

  const set = (field) => (event) => {
    const value = event.target.value
    setValues((v) => ({ ...v, [field]: value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }

  const review = (event) => {
    event.preventDefault()
    const found = validateProgress(kind, values, request, today)
    setErrors(found)
    if (Object.keys(found).length === 0) setConfirming(true)
  }

  const save = async () => {
    const ref = request.request_number
    try {
      let saved
      if (kind === 'start') saved = await startWork(ref, { startedDate: values.date, serviceProvider: values.provider.trim() })
      else if (kind === 'complete') {
        saved = await completeWork(ref, {
          repairNotes: values.notes.trim(),
          completionDate: values.date,
          serviceProvider: values.provider.trim(),
          cost: values.cost.trim(),
        })
      } else saved = await cancelRequest(ref, values.reason.trim())
      onSaved(saved)
    } catch (error) {
      setConfirming(false)
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error)) // e.g. asset_assigned, invalid_status_change
    }
  }

  const minDate = kind === 'start' ? request.reported_date : request.started_date

  return (
    <>
      <Dialog open={!confirming} onClose={onClose} maxWidth="sm" fullWidth>
        <form onSubmit={review} noValidate>
          <DialogTitle>{k.title(request)}</DialogTitle>
          <DialogContent>
            {formError ? (
              <Alert severity="error" sx={{ mb: 1 }} data-testid="progress-form-error">
                {formError}
              </Alert>
            ) : null}
            {kind === 'cancel' ? (
              <FormField
                label="Reason for cancelling"
                required
                autoFocus
                multiline
                minRows={2}
                value={values.reason}
                onChange={set('reason')}
                error={errors.reason}
                helperText={count(values.reason, CANCEL_REASON_MAX)}
              />
            ) : (
              <>
                <FormField
                  label={kind === 'start' ? 'Work started on' : 'Completed on'}
                  required
                  type="date"
                  value={values.date}
                  onChange={set('date')}
                  error={errors.date}
                  helperText={
                    kind === 'start'
                      ? `Today or earlier, not before the problem was reported (${formatPlainDate(minDate)}).`
                      : `Today or earlier, not before work started (${formatPlainDate(minDate)}).`
                  }
                  slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: minDate, max: today } }}
                />
                {kind === 'complete' ? (
                  <FormField
                    label="Repair notes (what was done)"
                    required
                    multiline
                    minRows={3}
                    value={values.notes}
                    onChange={set('notes')}
                    error={errors.notes}
                    helperText={count(values.notes, REPAIR_NOTES_MAX)}
                  />
                ) : null}
                <FormField
                  label="Service provider or responsible person (optional)"
                  value={values.provider}
                  onChange={set('provider')}
                  error={errors.provider}
                  helperText="An outside company or the staff member doing the repair."
                />
                {kind === 'complete' ? (
                  <FormField
                    label="Cost in ₹ (optional)"
                    value={values.cost}
                    onChange={set('cost')}
                    error={errors.cost}
                    helperText="0 or more, up to 2 decimals."
                    slotProps={{ htmlInput: { inputMode: 'decimal' } }}
                  />
                ) : null}
              </>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Close</Button>
            <Button type="submit" variant="contained" color={kind === 'cancel' ? 'error' : 'primary'}>
              {k.button}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
      <ConfirmDialog
        open={confirming}
        title={k.confirmTitle(request)}
        confirmLabel={k.confirmLabel}
        cancelLabel="Go back"
        destructive={kind === 'cancel'}
        onCancel={() => setConfirming(false)}
        onConfirm={save}
      >
        {confirmLines(kind, values, request)
          .filter(Boolean)
          .map((line) => (
            <Typography key={line} variant="body2" sx={{ mb: 0.5 }} data-testid="progress-confirm-line">
              {line}
            </Typography>
          ))}
      </ConfirmDialog>
    </>
  )
}

export function StartWorkDialog(props) {
  return <ProgressDialog kind="start" {...props} />
}

export function CompleteDialog(props) {
  return <ProgressDialog kind="complete" {...props} />
}

export function CancelDialog(props) {
  return <ProgressDialog kind="cancel" {...props} />
}

export function EditRequestDialog({ request, onClose, onSaved }) {
  const [values, setValues] = useState({
    priority: request.priority ?? '',
    provider: request.service_provider ?? '',
    notes: request.repair_notes ?? '',
    cost: request.cost ?? '',
  })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const set = (field) => (event) => {
    const value = event.target.value
    setValues((v) => ({ ...v, [field]: value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }

  const submit = async (event) => {
    event.preventDefault()
    const found = {}
    if (values.provider.trim().length > SERVICE_PROVIDER_MAX) found.provider = `Use at most ${SERVICE_PROVIDER_MAX} characters.`
    if (values.notes.trim().length > REPAIR_NOTES_MAX) found.notes = `Use at most ${REPAIR_NOTES_MAX.toLocaleString('en-IN')} characters.`
    if (values.cost.trim() && !COST_PATTERN.test(values.cost.trim())) found.cost = 'Enter an amount of 0 or more with up to 2 decimals.'
    setErrors(found)
    if (Object.keys(found).length > 0) return
    setSaving(true)
    try {
      const saved = await updateRequest(request.request_number, {
        priority: values.priority || null,
        service_provider: values.provider.trim() || null,
        repair_notes: values.notes.trim() || null,
        cost: values.cost.trim() || null,
      })
      onSaved(saved)
    } catch (error) {
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error)) // e.g. maintenance_request_closed
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={submit} noValidate>
        <DialogTitle>Edit {request.request_number}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }} data-testid="edit-form-error">
              {formError}
            </Alert>
          ) : null}
          <FormField select label="Priority" value={values.priority} onChange={set('priority')}>
            <MenuItem value="">None</MenuItem>
            {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
              <MenuItem key={value} value={value}>
                {label}
              </MenuItem>
            ))}
          </FormField>
          <FormField
            label="Service provider or responsible person"
            value={values.provider}
            onChange={set('provider')}
            error={errors.provider}
          />
          <FormField
            label="Repair notes"
            multiline
            minRows={3}
            value={values.notes}
            onChange={set('notes')}
            error={errors.notes}
            helperText={count(values.notes, REPAIR_NOTES_MAX)}
          />
          <FormField
            label="Cost in ₹"
            value={values.cost}
            onChange={set('cost')}
            error={errors.cost}
            helperText="0 or more, up to 2 decimals."
            slotProps={{ htmlInput: { inputMode: 'decimal' } }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
          <Button type="submit" variant="contained" disabled={saving}>
            Save
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
