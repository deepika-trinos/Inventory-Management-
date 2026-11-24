// Calls to the asset endpoints (/api/v1/assets). Admin and IT Manager only.
// Slice 3.2: get one asset. Slice 4.1: the asset register (list, search, filters),
// the locations in use, and an asset's history. Slice 4.2: edit and retire.
// Slice 4.5: enter an existing asset by hand (no purchase). Slice 5.1: assign to an
// employee; the register's "Assigned to" filter. Slice 5.2: return with inspection.
import apiClient from './client'

const BASE = '/api/v1/assets'

// The server stores statuses in lower case (PRD 8.1); the screen shows these labels.
export const ASSET_STATUS_LABELS = {
  available: 'Available',
  assigned: 'Assigned',
  under_maintenance: 'Under Maintenance',
  damaged: 'Damaged',
  retired: 'Retired',
}

export function assetStatusLabel(value) {
  return ASSET_STATUS_LABELS[value] ?? value
}

// The asset page's address: /assets/AST-000007.
export function assetPath(asset) {
  return `/assets/${encodeURIComponent(asset.asset_code)}`
}

// { page, pageSize, sort, search, categoryId, status, location, assignedTo } -> { items, total, page, page_size }
// Each row carries assigned_to: the employee holding it now, or null (Slice 5.1, A1).
export async function listAssets({ page = 1, pageSize = 20, sort, search, categoryId, status, location, assignedTo }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (categoryId) params.category_id = categoryId
  if (status) params.status = status
  if (location) params.location = location
  if (assignedTo) params.assigned_to = assignedTo
  const { data } = await apiClient.get(BASE, { params })
  return data
}

// Locations already typed on assets, A-Z (for the location filter).
export async function listAssetLocations() {
  const { data } = await apiClient.get(`${BASE}/locations`)
  return data
}

// ref: the asset's id (7) or asset ID ("AST-000007").
export async function getAsset(ref) {
  const { data } = await apiClient.get(`${BASE}/${encodeURIComponent(ref)}`)
  return data
}

// Enter equipment the company already owns, without a purchase (Slice 4.5, A7).
// fields: { category_id, serial_number, model, name, brand?, location?, warranty_expiry?,
// purchase_date?, cost? } -> the new asset (status Available, no purchase).
export async function createAsset(fields) {
  const { data } = await apiClient.post(BASE, fields)
  return data
}

/** True for an asset entered by hand (no purchase). */
export function enteredByHand(asset) {
  return !asset.purchase
}

// Statuses an asset can be retired from (owner's answer A3).
export const RETIRABLE_STATUSES = ['available', 'damaged']

// Edit the allowed details (A2). changes: any of { name, brand, model, serial_number,
// location, warranty_expiry }; for assets entered by hand also category_id,
// purchase_date and cost (Slice 4.5). null clears an optional field.
export async function updateAsset(ref, changes) {
  const { data } = await apiClient.patch(`${BASE}/${encodeURIComponent(ref)}`, changes)
  return data
}

// Retire permanently (A3): reason is required, up to 500 characters. Cannot be undone.
export async function retireAsset(ref, reason) {
  const { data } = await apiClient.post(`${BASE}/${encodeURIComponent(ref)}/retire`, { reason })
  return data
}

// Only Available assets can be assigned (BR-02, BR-03). The reason shown on the greyed-out
// button for every other status.
const NOT_ASSIGNABLE_REASONS = {
  assigned: 'Already assigned. Return it first.',
  under_maintenance: 'Under Maintenance. Finish the repair first.',
  damaged: 'Damaged assets cannot be assigned.',
  retired: 'Retired assets cannot be assigned.',
}

/** '' when the asset can be assigned, otherwise why not. */
export function assignBlockedReason(status) {
  if (status === 'available') return ''
  return NOT_ASSIGNABLE_REASONS[status] ?? 'Only Available assets can be assigned.'
}

// Assign an Available asset to an active employee (Slice 5.1; owner's answers N1-N3).
// { employeeId, assignmentDate?, expectedReturnDate? } -> the asset (status Assigned,
// with current_assignment).
export async function assignAsset(ref, { employeeId, assignmentDate, expectedReturnDate }) {
  const body = { employee_id: employeeId }
  if (assignmentDate) body.assignment_date = assignmentDate
  if (expectedReturnDate) body.expected_return_date = expectedReturnDate
  const { data } = await apiClient.post(`${BASE}/${encodeURIComponent(ref)}/assign`, body)
  return data
}

// Inspection outcomes on return (Slice 5.2, N4): the asset's next status.
export const RETURN_OUTCOMES = ['available', 'under_maintenance', 'damaged']

// Return an assigned asset with its inspection (Slice 5.2; owner's answers Q5, N4, N5).
// { returnDate, outcome, notes? } -> the asset (new status, no current_assignment).
export async function returnAsset(ref, { returnDate, outcome, notes }) {
  const body = { inspection_outcome: outcome }
  if (returnDate) body.return_date = returnDate
  if (notes) body.condition_notes = notes
  const { data } = await apiClient.post(`${BASE}/${encodeURIComponent(ref)}/return`, body)
  return data
}

// The asset's history (its audit log entries), newest first: { items, total, page, page_size }.
export async function getAssetHistory(ref, { page = 1, pageSize = 20, sort } = {}) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  const { data } = await apiClient.get(`${BASE}/${encodeURIComponent(ref)}/history`, { params })
  return data
}

// How each history action is shown. Later slices add theirs (4.2 edit / retire,
// 5.x assign / return, 6.x maintenance); an unknown action shows as it is stored.
const HISTORY_ACTION_LABELS = {
  'asset.created': 'Created',
  'asset.updated': 'Edited',
  'asset.retired': 'Retired',
  'assignment.created': 'Assigned',
  'assignment.returned': 'Returned',
}

export function historyActionLabel(action) {
  return HISTORY_ACTION_LABELS[action] ?? action
}
