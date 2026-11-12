// Pick an employee to link to a login (Users screen, Slice 2.2, closes B12).
// Lists only ACTIVE employees WITHOUT a login, searched on the server by
// employee ID, name or department as you type. The employee already linked to
// this user (when editing) is always offered too.
//
//   <EmployeePicker value={employee} onChange={setEmployee} required error={errors.employee} />
import { useEffect, useState } from 'react'
import { Autocomplete, TextField } from '@mui/material'

import { employeeLabel, listEmployees } from '../api/employees'
import { getErrorMessage } from '../api/errors'

const SEARCH_DELAY_MS = 300

export default function EmployeePicker({
  value,
  onChange,
  current = null, // the employee already linked to this user (edit)
  label = 'Employee record',
  required = false,
  error = '',
  helperText = '',
  disabled = false,
}) {
  const [input, setInput] = useState('')
  const [options, setOptions] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    let cancelled = false
    const timer = setTimeout(() => {
      setLoading(true)
      setLoadError('')
      // While an option is shown in the box, its label is the input: search everything instead.
      const search = value && input === employeeLabel(value) ? '' : input.trim()
      listEmployees({ status: 'active', hasLogin: false, search, pageSize: 20, sort: 'full_name' })
        .then((data) => {
          if (cancelled) return
          const found = data.items
          if (current && !found.some((e) => e.id === current.id)) found.unshift(current)
          setOptions(found)
        })
        .catch((err) => !cancelled && setLoadError(getErrorMessage(err)))
        .finally(() => !cancelled && setLoading(false))
    }, SEARCH_DELAY_MS)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [input, value, current])

  return (
    <Autocomplete
      value={value}
      onChange={(_e, picked) => onChange(picked)}
      inputValue={input}
      onInputChange={(_e, text) => setInput(text)}
      options={options}
      loading={loading}
      filterOptions={(x) => x} // the server already filtered
      getOptionLabel={employeeLabel}
      isOptionEqualToValue={(a, b) => a.id === b.id}
      noOptionsText={input ? 'No active employee without a login matches' : 'No active employees without a login'}
      disabled={disabled}
      renderOption={(props, option) => {
        const { key, ...rest } = props
        return (
          <li key={key} {...rest}>
            {employeeLabel(option)}
            {option.department ? ` (${option.department})` : ''}
          </li>
        )
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          required={required}
          error={Boolean(error || loadError)}
          helperText={error || loadError || helperText || ' '}
          margin="dense"
          fullWidth
        />
      )}
    />
  )
}
