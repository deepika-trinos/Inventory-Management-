// Report a problem with an asset (Slice 6.1: MNT-01 to MNT-03; owner's answers Q9, Q10, O4, O5, O8, O10).
//
//   <ReportProblemDialog open asset={asset} staff onClose onReported />   (asset page, Admin / IT Manager)
//   <ReportProblemDialog open asset={asset} onClose onReported />         (My Assets, Employee)
//
// Staff: issue (counter 0 / 1,000), optional priority (None / Low / Medium / High, Q10) and the
// reported date (today by default, between the day the asset was added and today, O5).
// Employee: the issue only; the date is today and the IT Manager sets any priority later (Q10, O8).
// No confirm box (O10): reporting does not change the asset's status (Q9). The server checks
// everything again; its problems are shown under the field they belong to.
import { useState } from 'react'
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Typography } from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { ISSUE_MAX, PRIORITY_LABELS, reportMyProblem, reportProblem } from '../../api/maintenance'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'
import { assetCreatedOn } from '../assets/AssetAssignDialog'

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  invalid_issue_description: 'issue',
  reported_date_in_future: 'reportedDate',
  reported_date_before_asset_created: 'reportedDate',
}

export function validateReport({ issue, reportedDate }, { staff, addedDate, today = todayInCompanyTimezone() }) {
  const errors = {}
  const text = issue.trim()
  if (!text) errors.issue = 'Please describe the problem.'
  else if (text.length > ISSUE_MAX) errors.issue = `Use at most ${ISSUE_MAX.toLocaleString('en-IN')} characters.`
  if (staff) {
    if (!reportedDate) errors.reportedDate = 'Please enter the reported date.'
    else if (reportedDate > today) errors.reportedDate = 'The reported date cannot be in the future.'
    else if (addedDate && reportedDate < addedDate) {
      errors.reportedDate = `The reported date cannot be before the asset was added (${formatPlainDate(addedDate)}).`
    }
  }
  return errors
}

export default function ReportProblemDialog({ open, asset, staff = false, onClose, onReported }) {
  const today = todayInCompanyTimezone()
  const addedDate = staff ? assetCreatedOn(asset) : null // O5: not before the asset was added
  const [values, setValues] = useState({ issue: '', priority: '', reportedDate: today })
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
    const found = validateReport(values, { staff, addedDate, today })
    setErrors(found)
    if (Object.keys(found).length > 0) return
    setSaving(true)
    try {
      const issue = values.issue.trim()
      const saved = staff
        ? await reportProblem(asset.asset_code, { issue, priority: values.priority, reportedDate: values.reportedDate })
        : await reportMyProblem(asset.id, issue)
      onReported(saved)
    } catch (error) {
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error)) // e.g. a request is already open, or the asset was returned
    } finally {
      setSaving(false)
    }
  }

  const count = values.issue.trim().length

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <form onSubmit={submit} noValidate>
        <DialogTitle>Report a problem with {asset.asset_code}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }} data-testid="report-form-error">
              {formError}
            </Alert>
          ) : null}
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {asset.name} · {asset.serial_number}.{' '}
            {staff
              ? 'The request starts as Reported; the asset keeps its status until work starts.'
              : 'The IT team will review it. Keep using the asset unless told otherwise.'}
          </Typography>
          <FormField
            label="What is wrong?"
            required
            autoFocus
            multiline
            minRows={3}
            value={values.issue}
            onChange={set('issue')}
            error={errors.issue}
            helperText={`${count} / ${ISSUE_MAX.toLocaleString('en-IN')}`}
            placeholder="e.g. Screen flickers after 10 minutes; battery lasts under an hour."
          />
          {staff ? (
            <>
              <FormField select label="Priority (optional)" value={values.priority} onChange={set('priority')}>
                <MenuItem value="">None</MenuItem>
                {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </FormField>
              <FormField
                label="Reported date"
                required
                type="date"
                value={values.reportedDate}
                onChange={set('reportedDate')}
                error={errors.reportedDate}
                helperText={
                  addedDate
                    ? `Today or earlier, not before the asset was added (${formatPlainDate(addedDate)}).`
                    : 'Today or earlier.'
                }
                slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: addedDate ?? undefined, max: today } }}
              />
            </>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={saving}>
            Report problem
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
