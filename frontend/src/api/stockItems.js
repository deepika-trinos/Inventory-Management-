// Calls to the stock item endpoints (/api/v1/stock-items, Slice 2.4).
// Admin and IT Manager only. No delete (BR-12). quantity_on_hand is read-only:
// only stock movements change it (Slices 3.3, 4.4, 4.5).
// Slice 4.3: each item's low_stock flag (active and at or below its reorder threshold,
// B37 / G1), the low-stock filter, one item, and its movement history (INV-05).
import apiClient from './client'

const BASE = '/api/v1/stock-items'

// The fixed list of units (decision B35); same as UNITS on the server.
export const UNITS = [
  { value: 'pieces', label: 'Pieces' },
  { value: 'boxes', label: 'Boxes' },
  { value: 'packs', label: 'Packs' },
  { value: 'pairs', label: 'Pairs' },
  { value: 'sets', label: 'Sets' },
  { value: 'rolls', label: 'Rolls' },
  { value: 'metres', label: 'Metres' },
]

export function unitLabel(value) {
  return UNITS.find((u) => u.value === value)?.label ?? value
}

// { page, pageSize, sort, search, categoryId, status, lowStock } -> { items, total, page, page_size }
// lowStock: true = only low-stock items; false = all others; '' / undefined = all.
export async function listStockItems({ page = 1, pageSize = 20, sort, search, categoryId, status, lowStock }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (categoryId) params.category_id = categoryId
  if (status) params.status = status
  if (lowStock === true || lowStock === false) params.low_stock = lowStock
  const { data } = await apiClient.get(BASE, { params })
  return data
}

export async function getStockItem(id) {
  const { data } = await apiClient.get(`${BASE}/${encodeURIComponent(id)}`)
  return data
}

// Issue stock (Slice 4.4, A4): { quantity, reason, employeeId?, movementDate? }
// -> { item, movement }. Never below 0 (insufficient_stock).
export async function issueStock(id, { quantity, reason, employeeId, movementDate }) {
  const body = { quantity, reason }
  if (employeeId) body.employee_id = employeeId
  if (movementDate) body.movement_date = movementDate
  const { data } = await apiClient.post(`${BASE}/${encodeURIComponent(id)}/issue`, body)
  return data
}

// Adjust stock (Slice 4.4, A5): { direction: 'add' | 'remove', quantity, reason, movementDate? }
// -> { item, movement }.
export async function adjustStock(id, { direction, quantity, reason, movementDate }) {
  const body = { direction, quantity, reason }
  if (movementDate) body.movement_date = movementDate
  const { data } = await apiClient.post(`${BASE}/${encodeURIComponent(id)}/adjust`, body)
  return data
}

// Opening stock (Slice 4.5, A6): { quantity, note?, movementDate? } -> { item, movement }.
// Once per item, only while it has no movements (opening_stock_not_allowed).
export async function enterOpeningStock(id, { quantity, note, movementDate }) {
  const body = { quantity }
  if (note) body.note = note
  if (movementDate) body.movement_date = movementDate
  const { data } = await apiClient.post(`${BASE}/${encodeURIComponent(id)}/opening-stock`, body)
  return data
}

// The item's movement history, newest saved first (G2): { items, total, page, page_size }.
export async function getStockMovements(id, { page = 1, pageSize = 20 } = {}) {
  const { data } = await apiClient.get(`${BASE}/${encodeURIComponent(id)}/movements`, {
    params: { page, page_size: pageSize },
  })
  return data
}

// fields: { name, category_id, unit_of_measure, reorder_threshold }
export async function createStockItem(fields) {
  const { data } = await apiClient.post(BASE, fields)
  return data
}

export async function updateStockItem(id, changes) {
  const { data } = await apiClient.patch(`${BASE}/${id}`, changes)
  return data
}

export async function setStockItemActive(id, active) {
  const { data } = await apiClient.post(`${BASE}/${id}/${active ? 'activate' : 'deactivate'}`)
  return data
}
