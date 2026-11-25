// Calls for maintenance requests (Slice 6.1: MNT-01 to MNT-03; owner's answers Q9, Q10, O1-O14).
// Reporting a problem never changes the asset's status (Q9).
import apiClient from './client'

export const ISSUE_MAX = 1000 // O4

// MNT-04. Slice 6.1 only creates Reported requests; 6.2 moves them on.
export const MAINTENANCE_STATUS_LABELS = {
  reported: 'Reported',
  in_progress: 'In Progress',
  completed: 'Completed',
  cancelled: 'Cancelled',
}

// Q10: optional, set by the IT Manager.
export const PRIORITY_LABELS = { low: 'Low', medium: 'Medium', high: 'High' }

export function maintenanceStatusLabel(value) {
  return MAINTENANCE_STATUS_LABELS[value] ?? value
}

export function priorityLabel(value) {
  return value ? PRIORITY_LABELS[value] ?? value : 'Not set'
}

/** "asha@example.com (Employee)" */
export function reporterLabel(reporter) {
  return reporter ? `${reporter.email} (${reporter.role})` : '—'
}

// Admin and IT Manager (MNT-02): any asset except Retired. Returns the new request.
export async function reportProblem(ref, { issue, priority, reportedDate }) {
  const body = { issue_description: issue }
  if (priority) body.priority = priority
  if (reportedDate) body.reported_date = reportedDate
  const { data } = await apiClient.post(`/api/v1/assets/${encodeURIComponent(ref)}/maintenance-requests`, body)
  return data
}

// Employee role (MNT-01): only an asset they hold now. No priority and no date (Q10, O5).
export async function reportMyProblem(assetId, issue) {
  const { data } = await apiClient.post('/api/v1/me/maintenance-requests', { asset_id: assetId, issue_description: issue })
  return data
}

// Admin and IT Manager: the asset's requests, newest first.
export async function getAssetRequests(ref) {
  const { data } = await apiClient.get(`/api/v1/assets/${encodeURIComponent(ref)}/maintenance-requests`)
  return data
}

// Admin and IT Manager: { page, pageSize, sort, search, status } -> { items, total, page, page_size }.
export async function listRequests({ page = 1, pageSize = 20, sort, search, status }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (status) params.status = status
  const { data } = await apiClient.get('/api/v1/maintenance-requests', { params })
  return data
}

// ---- Slice 6.2: repair progress (MNT-04 to MNT-07; owner's answers S1-S14) ----------------------
export const SERVICE_PROVIDER_MAX = 200 // S9
export const REPAIR_NOTES_MAX = 1000 // S12
export const CANCEL_REASON_MAX = 500 // S11

/** Open = Reported or In Progress (O2). */
export function isOpenStatus(status) {
  return status === 'reported' || status === 'in_progress'
}

/** The request page's address. */
export function requestPath(request) {
  return `/maintenance/${encodeURIComponent(request.request_number)}`
}

// Admin and IT Manager: one request with its history (newest first).
export async function getRequest(ref) {
  const { data } = await apiClient.get(`/api/v1/maintenance-requests/${encodeURIComponent(ref)}`)
  return data
}

const progressUrl = (ref, action) => `/api/v1/maintenance-requests/${encodeURIComponent(ref)}/${action}`

// Reported -> In Progress: the asset becomes Under Maintenance (Q9).
export async function startWork(ref, { startedDate, serviceProvider }) {
  const body = {}
  if (startedDate) body.started_date = startedDate
  if (serviceProvider) body.service_provider = serviceProvider
  const { data } = await apiClient.post(progressUrl(ref, 'start'), body)
  return data
}

// In Progress -> Completed: the asset stays Under Maintenance until inspected (Slice 6.3).
export async function completeWork(ref, { repairNotes, completionDate, serviceProvider, cost }) {
  const body = { repair_notes: repairNotes }
  if (completionDate) body.completion_date = completionDate
  if (serviceProvider) body.service_provider = serviceProvider
  if (cost !== '' && cost !== null && cost !== undefined) body.cost = cost
  const { data } = await apiClient.post(progressUrl(ref, 'complete'), body)
  return data
}

// Reported or In Progress -> Cancelled (required reason, S11).
export async function cancelRequest(ref, reason) {
  const { data } = await apiClient.post(progressUrl(ref, 'cancel'), { reason })
  return data
}

// Priority and details while open: send only what changes; null clears.
export async function updateRequest(ref, changes) {
  const { data } = await apiClient.patch(`/api/v1/maintenance-requests/${encodeURIComponent(ref)}`, changes)
  return data
}
