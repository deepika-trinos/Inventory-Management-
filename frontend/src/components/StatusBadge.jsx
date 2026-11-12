// A small coloured label for a status, always the same colour for the same
// status everywhere in the app.
//   - Asset statuses (PRD 8.1): Available, Assigned, Under Maintenance, Damaged, Retired
//   - Record statuses for master data (Slice 2.1+): Active, Inactive
import { Chip } from '@mui/material'

const ASSET_COLORS = {
  Available: 'success', // green: can be assigned
  Assigned: 'info', // blue: with an employee
  'Under Maintenance': 'warning', // orange: being repaired
  Damaged: 'error', // red: not fit for use
  Retired: 'default', // grey: permanently out of use
}

// Master data (categories, later employees, vendors, stock items): never deleted,
// only deactivated (BR-12).
const RECORD_COLORS = {
  Active: 'success',
  Inactive: 'default',
}

const COLORS = { ...ASSET_COLORS, ...RECORD_COLORS }
const OUTLINED = new Set(['Retired', 'Inactive']) // "out of use" looks lighter

export const ASSET_STATUSES = Object.keys(ASSET_COLORS)

// 'active' -> 'Active' (the server sends record statuses in lower case)
export function recordStatusLabel(status) {
  return status === 'active' ? 'Active' : status === 'inactive' ? 'Inactive' : status
}

export default function StatusBadge({ status, size = 'small' }) {
  return (
    <Chip
      label={status}
      color={COLORS[status] ?? 'default'}
      size={size}
      variant={OUTLINED.has(status) ? 'outlined' : 'filled'}
    />
  )
}
