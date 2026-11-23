// Assign an asset to an employee (Slice 5.1: ASN-01 to ASN-04, EMP-05, BR-02, BR-03,
// BR-05; owner's answers N1, N2, N3), opened from the asset page's "Assign…" button
// (only for Available assets).
// Form: employee (ACTIVE employees only, with or without a login), assignment date (today
// by default; earlier allowed; not in the future; not before the asset was added) and an
// optional expected return date (on or after the assignment date; cannot be changed later).
// Then a confirm box: "Assign AST-000003 to Asha Kumar (EMP-001)?". The server checks
// everything again; its problems are shown under the field they belong to.
import { useState } from 'react'
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from '@mui/material'

import { assignAsset } from '../../api/assets'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import ConfirmDialog from '../../components/ConfirmDialog'
import EmployeePicker from '../../components/EmployeePicker'
import FormField from '../../components/FormField'
import { formatPlainDate, todayInCompanyTimezone } from '../../utils/dates'

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  employee_not_found: 'employee',
  employee_inactive: 'employee',
  assignment_date_in_future: 'assignmentDate',
  assignment_date_before_asset_created: 'assignmentDate',
  invalid_expected_return_date: 'expectedReturnDate',
}

/** "Asha Kumar (EMP-001)" */
export function employeeName(employee) {
  return employee ? `${employee.full_name} (${employee.employee_code})` : ''
}

/** The day the asset was added, in the company timezone ("YYYY-MM-DD"), N1. */
export function assetCreatedOn(asset) {
  return todayInCompanyTimezone(new Date(asset.created_at))
}

export function validateAssignment({ employee, assignmentDate, expectedReturnDate }, createdOn, today = todayInCompanyTimezone()) {
  const errors = {}
  if (!employee) errors.employee = 'Choose the employee.'
  if (!assignmentDate) errors.assignmentDate = 'Please enter the assignment date.'
  else if (assignmentDate > today) errors.assignmentDate = 'The assignment date cannot be in the future.'
  else if (assignmentDate < createdOn) {
    errors.assignmentDate = `The assignment date cannot be before the asset was added (${formatPlainDate(createdOn)}).`
  }
  if (expectedReturnDate && assignmentDate && expectedReturnDate < assignmentDate) {
    errors.expectedReturnDate = 'The expected return date cannot be before the assignment date.'
  }
  return errors
}

export default function AssetAssignDialog({ open, asset, onClose, onAssigned }) {
  const today = todayInCompanyTimezone()
  const createdOn = assetCreatedOn(asset)
  const [employee, setEmployee] = useState(null)
  const [values, setValues] = useState({ assignmentDate: today, expectedReturnDate: '' })
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [confirming, setConfirming] = useState(false)

  const set = (field) => (event) => {
    setValues((v) => ({ ...v, [field]: event.target.value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }

  const review = (event) => {
    event.preventDefault()
    const found = validateAssignment({ employee, ...values }, createdOn, today)
    setErrors(found)
    if (Object.keys(found).length === 0) setConfirming(true)
  }

  const save = async () => {
    try {
      const saved = await assignAsset(asset.asset_code, {
        employeeId: employee.id,
        assignmentDate: values.assignmentDate,
        expectedReturnDate: values.expectedReturnDate || undefined,
      })
      onAssigned(saved)
    } catch (error) {
      setConfirming(false)
      const field = FIELD_FOR_CODE[getErrorCode(error)]
      if (field) setErrors((e) => ({ ...e, [field]: getErrorMessage(error) }))
      else setFormError(getErrorMessage(error)) // e.g. someone else assigned it a moment ago
    }
  }

  const details = [
    `${asset.name} · serial ${asset.serial_number}.`,
    `Assignment date: ${formatPlainDate(values.assignmentDate)}.`,
    values.expectedReturnDate
      ? `Expected return: ${formatPlainDate(values.expectedReturnDate)}.`
      : 'No expected return date.',
    'The asset becomes Assigned. The expected return date cannot be changed later.',
  ]

  return (
    <>
      <Dialog open={open && !confirming} onClose={onClose} maxWidth="sm" fullWidth>
        <form onSubmit={review} noValidate>
          <DialogTitle>Assign {asset.asset_code}</DialogTitle>
          <DialogContent>
            {formError ? (
              <Alert severity="error" sx={{ mb: 1 }}>
                {formError}
              </Alert>
            ) : null}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {asset.name} · serial {asset.serial_number}
            </Typography>
            <EmployeePicker
              label="Employee"
              required
              value={employee}
              onChange={(picked) => {
                setEmployee(picked)
                setErrors((x) => ({ ...x, employee: '' }))
                setFormError('')
              }}
              onlyWithoutLogin={false}
              error={errors.employee}
              helperText="Active employees only. A login is not needed."
            />
            <FormField
              label="Assignment date"
              required
              type="date"
              value={values.assignmentDate}
              onChange={set('assignmentDate')}
              error={errors.assignmentDate}
              helperText={`Today or earlier, not before the asset was added (${formatPlainDate(createdOn)}).`}
              slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: createdOn, max: today } }}
            />
            <FormField
              label="Expected return date (optional)"
              type="date"
              value={values.expectedReturnDate}
              onChange={set('expectedReturnDate')}
              error={errors.expectedReturnDate}
              helperText="On or after the assignment date. Cannot be changed later."
              slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: values.assignmentDate || undefined } }}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={onClose}>Cancel</Button>
            <Button type="submit" variant="contained">
              Assign…
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      <ConfirmDialog
        open={open && confirming}
        title={`Assign ${asset.asset_code} to ${employeeName(employee)}?`}
        confirmLabel="Assign"
        cancelLabel="Go back"
        onCancel={() => setConfirming(false)}
        onConfirm={save}
      >
        {details.map((line) => (
          <Typography key={line} variant="body2" sx={{ mb: 0.5 }} data-testid="assign-confirm-line">
            {line}
          </Typography>
        ))}
      </ConfirmDialog>
    </>
  )
}
