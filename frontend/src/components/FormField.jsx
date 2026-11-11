// A labelled text box for forms, so every form looks and behaves the same.
//   - label         : text above the box
//   - required      : adds the * marker
//   - error         : the problem to show under the box (empty = no problem)
//   - helperText    : a hint shown when there is no error
// Any other prop (type, value, onChange, autoComplete...) goes to MUI's TextField.
import { TextField } from '@mui/material'

export default function FormField({ label, required = false, error = '', helperText = '', ...props }) {
  return (
    <TextField
      label={label}
      required={required}
      error={Boolean(error)}
      helperText={error || helperText || ' '} // ' ' keeps the height steady
      fullWidth
      margin="dense"
      {...props}
    />
  )
}
