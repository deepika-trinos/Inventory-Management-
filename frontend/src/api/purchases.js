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

// { page, pageSize, sort, search, status, vendorId } -> { items, total, page, page_size }
export async function listPurchases({ page = 1, pageSize = 20, sort, search, status, vendorId }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (status) params.status = status
  if (vendorId) params.vendor_id = vendorId
  const { data } = await apiClient.get(BASE, { params })
  return data
}

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
