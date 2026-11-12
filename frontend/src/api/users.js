// Calls to the Admin-only user management endpoints (/api/v1/users, Slice 1.6).
import apiClient from './client'

const BASE = '/api/v1/users'

// { page, pageSize, sort, search, role, isActive } -> { items, total, page, page_size }
export async function listUsers({ page, pageSize, sort, search, role, isActive }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (role) params.role = role
  if (isActive !== '' && isActive !== undefined && isActive !== null) params.is_active = isActive
  const { data } = await apiClient.get(BASE, { params })
  return data
}

// employeeId: required for the Employee role (Slice 2.2), optional otherwise.
export async function createUser({ email, password, role, employeeId = null }) {
  const { data } = await apiClient.post(BASE, { email, password, role, employee_id: employeeId })
  return data
}

export async function updateUser(id, changes) {
  const { data } = await apiClient.patch(`${BASE}/${id}`, changes)
  return data
}

// employeeId: links an employee in the same step (needed when changing to Employee without a link).
export async function changeUserRole(id, role, employeeId = null) {
  const body = { role }
  if (employeeId) body.employee_id = employeeId
  const { data } = await apiClient.patch(`${BASE}/${id}/role`, body)
  return data
}

export async function setUserActive(id, active) {
  const { data } = await apiClient.post(`${BASE}/${id}/${active ? 'activate' : 'deactivate'}`)
  return data
}
