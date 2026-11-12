// Calls to the vendor endpoints (/api/v1/vendors, Slice 2.3).
// Admin and IT Manager only. There is no delete: vendors are deactivated (BR-12, VEN-05).
import apiClient from './client'

const BASE = '/api/v1/vendors'

// { page, pageSize, sort, search, status } -> { items, total, page, page_size }
export async function listVendors({ page = 1, pageSize = 20, sort, search, status }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (status) params.status = status
  const { data } = await apiClient.get(BASE, { params })
  return data
}

export async function getVendor(id) {
  const { data } = await apiClient.get(`${BASE}/${id}`)
  return data
}

// fields: { name, contact_person, email, phone, address }
export async function createVendor(fields) {
  const { data } = await apiClient.post(BASE, fields)
  return data
}

export async function updateVendor(id, changes) {
  const { data } = await apiClient.patch(`${BASE}/${id}`, changes)
  return data
}

export async function setVendorActive(id, active) {
  const { data } = await apiClient.post(`${BASE}/${id}/${active ? 'activate' : 'deactivate'}`)
  return data
}
