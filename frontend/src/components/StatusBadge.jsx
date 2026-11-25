// A small coloured label for a status, always the same colour for the same
// status everywhere in the app.
//   - Asset statuses (PRD 8.1): Available, Assigned, Under Maintenance, Damaged, Retired
//   - Record statuses for master data (Slice 2.1+): Active, Inactive
//   - Purchase statuses (Slice 3.1, PUR-04): Draft, Received, Cancelled
//   - Maintenance request statuses (Slice 6.1, MNT-04): Reported, In Progress, Completed, Cancelled
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

// Purchases: a draft is waiting; received is done; cancelled is final and changed nothing.
const PURCHASE_COLORS = {
  Draft: 'warning',
  Received: 'success',
  Cancelled: 'default',
}

// Maintenance requests (Slice 6.1, MNT-04). Cancelled shares the purchase colour above.
const MAINTENANCE_COLORS = {
  Reported: 'warning',
  'In Progress': 'info',
  Completed: 'success',
}

const COLORS = { ...ASSET_COLORS, ...RECORD_COLORS, ...PURCHASE_COLORS, ...MAINTENANCE_COLORS }
const OUTLINED = new Set(['Retired', 'Inactive', 'Cancelled']) // "out of use" looks lighter

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
