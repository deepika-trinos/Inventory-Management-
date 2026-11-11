// A small coloured label for an asset's status (PRD 8.1), always the same colour
// for the same status everywhere in the app.
import { Chip } from '@mui/material'

const COLORS = {
  Available: 'success', // green: can be assigned
  Assigned: 'info', // blue: with an employee
  'Under Maintenance': 'warning', // orange: being repaired
  Damaged: 'error', // red: not fit for use
  Retired: 'default', // grey: permanently out of use
}

export const ASSET_STATUSES = Object.keys(COLORS)

export default function StatusBadge({ status, size = 'small' }) {
  return (
    <Chip
      label={status}
      color={COLORS[status] ?? 'default'}
      size={size}
      variant={status === 'Retired' ? 'outlined' : 'filled'}
    />
  )
}
