// The Add employee / Edit employee form, shown in a pop-up dialog (EMP-01, EMP-02).
//   Required: employee ID, name. Optional: department (typed, with suggestions
//   of departments already used, decision B23), designation, work email, phone.
//   Active status has its own confirmed action on the list.
// Problems are shown under the field they belong to, e.g. "employee ID already used".
import { useEffect, useState } from 'react'
import {
  Alert,
  Autocomplete,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
} from '@mui/material'

import { createEmployee, listDepartments, updateEmployee } from '../../api/employees'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import FormField from '../../components/FormField'

// Same limits and checks as the server (backend/app/modules/employees).
const LIMITS = { employee_code: 30, full_name: 150, department: 100, designation: 100, work_email: 255, phone: 30 }
const EMAIL_SHAPE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const PHONE_SHAPE = /^\+?[0-9 ()./-]{3,30}$/

// Which field a server error belongs to.
const FIELD_FOR_CODE = {
  employee_code_taken: 'employee_code',
  invalid_employee_code: 'employee_code',
  invalid_full_name: 'full_name',
  work_email_taken: 'work_email',
  invalid_email: 'work_email',
  invalid_phone: 'phone',
}

const FIELDS = ['employee_code', 'full_name', 'department', 'designation', 'work_email', 'phone']

function validate(values) {
  const errors = {}
  if (!values.employee_code.trim()) errors.employee_code = 'Please enter an employee ID.'
  if (!values.full_name.trim()) errors.full_name = "Please enter the employee's name."
  const email = values.work_email.trim()
  if (email && !EMAIL_SHAPE.test(email)) errors.work_email = 'Please enter a valid email address.'
  const phone = values.phone.trim()
  if (phone && !PHONE_SHAPE.test(phone)) errors.phone = 'Use digits, spaces, + ( ) . / and - only.'
  for (const field of FIELDS) {
    if (values[field].trim().length > LIMITS[field]) errors[field] = `Use at most ${LIMITS[field]} characters.`
  }
  return errors
}

export default function EmployeeFormDialog({ open, employee, onClose, onSaved }) {
  const isCreate = !employee
  const [values, setValues] = useState(() =>
    Object.fromEntries(FIELDS.map((f) => [f, employee?.[f] ?? ''])),
  )
  const [departments, setDepartments] = useState([])
  const [errors, setErrors] = useState({})
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listDepartments()
      .then(setDepartments)
      .catch(() => setDepartments([])) // suggestions only: typing still works
  }, [])

  const setField = (field, value) => {
    setValues((v) => ({ ...v, [field]: value }))
    setErrors((e) => ({ ...e, [field]: '' }))
    setFormError('')
  }
  const handleChange = (field) => (event) => setField(field, event.target.value)

  const handleSubmit = async (event) => {
    event.preventDefault()
    const found = validate(values)
    setErrors(found)
    if (Object.keys(found).length) return

    // Trimmed values; empty optional fields are sent as null (= cleared).
    const payload = Object.fromEntries(FIELDS.map((f) => [f, values[f].trim() || null]))
    setSaving(true)
    try {
      const saved = isCreate ? await createEmployee(payload) : await updateEmployee(employee.id, payload)
      onSaved(saved, isCreate)
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

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="sm" fullWidth>
      <form onSubmit={handleSubmit} noValidate>
        <DialogTitle>{isCreate ? 'Add employee' : 'Edit employee'}</DialogTitle>
        <DialogContent>
          {formError ? (
            <Alert severity="error" sx={{ mb: 1 }}>
              {formError}
            </Alert>
          ) : null}
          <Grid container columnSpacing={2}>
            <Grid size={{ xs: 12, sm: 5 }}>
              {text('employee_code', 'Employee ID', { required: true, autoFocus: true, helperText: 'Must be unique.' })}
            </Grid>
            <Grid size={{ xs: 12, sm: 7 }}>{text('full_name', 'Full name', { required: true })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Autocomplete
                freeSolo
                options={departments}
                inputValue={values.department}
                onInputChange={(_e, value) => setField('department', value)}
                disabled={saving}
                renderInput={(params) => (
                  <FormField
                    {...params}
                    label="Department"
                    error={errors.department}
                    helperText="Pick one already used, or type a new one."
                    slotProps={{
                      ...params.slotProps,
                      htmlInput: { ...params.slotProps?.htmlInput, maxLength: LIMITS.department },
                    }}
                  />
                )}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{text('designation', 'Designation')}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{text('work_email', 'Work email', { type: 'email' })}</Grid>
            <Grid size={{ xs: 12, sm: 6 }}>{text('phone', 'Phone', { type: 'tel' })}</Grid>
          </Grid>
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
            {isCreate ? 'Add employee' : 'Save'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  )
}
