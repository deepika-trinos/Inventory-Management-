// Calls to the purchase endpoints (/api/v1/purchases, Slice 3.1).
// Admin and IT Manager only (P6). There is no delete: a draft is cancelled (BR-12).
// Money comes back as strings with 2 decimals ("1250.00"); totals are calculated by the server.
import apiClient from './client'

const BASE = '/api/v1/purchases'

export const PURCHASE_STATUSES = [
  { value: 'draft', label: 'Draft' },
  { value: 'received', label: 'Received' },
  { value: 'cancelled', label: 'Cancelled' },
]

export function purchaseStatusLabel(value) {
  return PURCHASE_STATUSES.find((s) => s.value === value)?.label ?? value
}

// { page, pageSize, sort, search, status, vendorId, dateFrom, dateTo } -> { items, total, page, page_size }
// Also a vendor's purchase history (Slice 3.4, VEN-04): { vendorId, sort: '-purchase_date' }.
// dateFrom / dateTo ("YYYY-MM-DD") limit the purchase date, both days included.
export async function listPurchases({ page = 1, pageSize = 20, sort, search, status, vendorId, dateFrom, dateTo }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (status) params.status = status
  if (vendorId) params.vendor_id = vendorId
  if (dateFrom) params.date_from = dateFrom
  if (dateTo) params.date_to = dateTo
  const { data } = await apiClient.get(BASE, { params })
  return data
}

// How stock movement types are shown (P7).
const MOVEMENT_TYPE_LABELS = {
  receipt: 'Receipt',
  issue: 'Issue',
  adjustment_in: 'Adjustment in',
  adjustment_out: 'Adjustment out',
  opening: 'Opening stock',
}

export function movementTypeLabel(value) {
  return MOVEMENT_TYPE_LABELS[value] ?? value
}

// One purchase with its lines, assets created and stock movements written (PUR-09).
export async function getPurchase(id) {
  const { data } = await apiClient.get(`${BASE}/${id}`)
  return data
}

// fields: { vendor_id, reference_number, purchase_date, notes, lines: [...] }
export async function createPurchase(fields) {
  const { data } = await apiClient.post(BASE, fields)
  return data
}

// Only a draft can be edited. `lines`, when sent, replaces all lines.
export async function updatePurchase(id, changes) {
  const { data } = await apiClient.patch(`${BASE}/${id}`, changes)
  return data
}

// Only a draft can be cancelled. Final.
export async function cancelPurchase(id) {
  const { data } = await apiClient.post(`${BASE}/${id}/cancel`)
  return data
}

// Receive a draft in one step (Slice 3.2): { received_date, lines: [{ line_id, received_quantity, units }] }.
// Each unit becomes an asset; the new asset IDs come back in lines[].assets. Final.
export async function receivePurchase(id, body) {
  const { data } = await apiClient.post(`${BASE}/${id}/receive`, body)
  return data
}
