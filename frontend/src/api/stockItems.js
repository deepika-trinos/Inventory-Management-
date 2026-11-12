// Calls to the stock item endpoints (/api/v1/stock-items, Slice 2.4).
// Admin and IT Manager only. No delete (BR-12). quantity_on_hand is read-only:
// only stock movements change it (Slices 3.3, 4.4, 4.5).
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

// { page, pageSize, sort, search, categoryId, status } -> { items, total, page, page_size }
export async function listStockItems({ page = 1, pageSize = 20, sort, search, categoryId, status }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (categoryId) params.category_id = categoryId
  if (status) params.status = status
  const { data } = await apiClient.get(BASE, { params })
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
