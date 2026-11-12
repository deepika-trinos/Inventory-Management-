// Calls to the asset category endpoints (/api/v1/categories, Slice 2.1).
// Admin and IT Manager only. There is no delete: categories are deactivated (BR-12).
import apiClient from './client'

const BASE = '/api/v1/categories'

// How each tracking type is shown on screen.
export const TRACKING_TYPES = [
  { value: 'serialized', label: 'One-by-one', hint: 'Each unit is its own asset with an ID and serial number (e.g. laptops).' },
  { value: 'bulk', label: 'By quantity', hint: 'Counted as stock, not one by one (e.g. mice, cables).' },
]

export function trackingTypeLabel(value) {
  return TRACKING_TYPES.find((t) => t.value === value)?.label ?? value
}

// { page, pageSize, sort, search, trackingType, status } -> { items, total, page, page_size }
export async function listCategories({ page, pageSize, sort, search, trackingType, status }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (trackingType) params.tracking_type = trackingType
  if (status) params.status = status
  const { data } = await apiClient.get(BASE, { params })
  return data
}

export async function createCategory({ name, description, trackingType }) {
  const { data } = await apiClient.post(BASE, { name, description, tracking_type: trackingType })
  return data
}

// changes: { name?, description?, tracking_type? }
export async function updateCategory(id, changes) {
  const { data } = await apiClient.patch(`${BASE}/${id}`, changes)
  return data
}

export async function setCategoryActive(id, active) {
  const { data } = await apiClient.post(`${BASE}/${id}/${active ? 'activate' : 'deactivate'}`)
  return data
}
