// How maintenance audit rows read in a history (Slice 6.1 / 6.2 / 6.3; owner's answer S13: the history is the
// asset's audit rows). Used by the asset page's History and the request page's History.
import { assetStatusLabel } from '../../api/assets'
import { INSPECTION_OUTCOME_LABELS, maintenanceStatusLabel, priorityLabel } from '../../api/maintenance'
import { formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'

const FIELD_LABELS = {
  priority: 'Priority',
  service_provider: 'Service provider',
  repair_notes: 'Repair notes',
  cost: 'Cost',
}

function shown(field, value) {
  if (value === null || value === undefined || value === '') return '(empty)'
  if (field === 'priority') return priorityLabel(value)
  if (field === 'cost') return formatAmount(value)
  return value
}

/** "Work started" / "Completed" / "Cancelled" / "Request edited" / "Problem reported" / "Inspected", or null if not maintenance. */
export function maintenanceActionLabel(entry) {
  if (entry.action === 'maintenance.reported') return 'Problem reported'
  if (entry.action === 'maintenance.inspected') return 'Inspected' // Slice 6.3
  if (entry.action === 'maintenance.updated') return 'Request edited'
  if (entry.action !== 'maintenance.status_changed') return null
  const to = entry.after?.status
  if (to === 'in_progress') return 'Work started'
  if (to === 'completed') return 'Repair completed'
  if (to === 'cancelled') return 'Request cancelled'
  return 'Repair status changed'
}

/** A short note for a maintenance history row, or null if not maintenance. */
export function maintenanceHistoryNote(entry) {
  const after = entry.after ?? {}
  const before = entry.before ?? {}
  if (entry.action === 'maintenance.reported') {
    // e.g. "MNT-000001 · High · Screen flickers" (Slice 6.1)
    return [after.request_number, after.priority ? priorityLabel(after.priority) : null, after.issue_description]
      .filter(Boolean)
      .join(' · ')
  }
  if (entry.action === 'maintenance.updated') {
    // e.g. "MNT-000001 · Priority: Low → High; Cost: (empty) → ₹300.00"
    const changes = Object.keys(after)
      .filter((field) => FIELD_LABELS[field])
      .map((field) => `${FIELD_LABELS[field]}: ${shown(field, before[field])} → ${shown(field, after[field])}`)
      .join('; ')
    return `${after.request_number} · ${changes}`
  }
  if (entry.action === 'maintenance.inspected') {
    // e.g. "MNT-000001 · Under Maintenance → Available · inspected 26 Nov 2026 · Works fine" (Slice 6.3)
    return [
      after.request_number,
      `${assetStatusLabel(before.asset_status)} → ${INSPECTION_OUTCOME_LABELS[after.inspection_outcome] ?? assetStatusLabel(after.asset_status)}`,
      after.inspection_date ? `inspected ${formatPlainDate(after.inspection_date)}` : null,
      after.condition_notes,
    ]
      .filter(Boolean)
      .join(' · ')
  }
  if (entry.action !== 'maintenance.status_changed') return null
  // e.g. "MNT-000001 · Reported → In Progress · asset Under Maintenance · started 23 Nov 2026"
  const parts = [
    after.request_number,
    `${maintenanceStatusLabel(before.status)} → ${maintenanceStatusLabel(after.status)}`,
    after.asset_status ? `asset ${assetStatusLabel(after.asset_status)}` : null,
  ]
  if (after.status === 'in_progress') {
    parts.push(after.started_date ? `started ${formatPlainDate(after.started_date)}` : null, after.service_provider)
  } else if (after.status === 'completed') {
    parts.push(
      after.completion_date ? `completed ${formatPlainDate(after.completion_date)}` : null,
      after.repair_notes,
      after.service_provider,
      after.cost !== null && after.cost !== undefined ? `cost ${formatAmount(after.cost)}` : null,
    )
  } else if (after.status === 'cancelled') {
    parts.push(after.reason ? `Reason: ${after.reason}` : null)
  }
  return parts.filter(Boolean).join(' · ')
}
