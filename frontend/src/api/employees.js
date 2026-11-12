// Calls to the employee endpoints (/api/v1/employees, Slice 2.2).
// Admin and IT Manager only. There is no delete: employees are deactivated (BR-12).
import apiClient from './client'

const BASE = '/api/v1/employees'

// { page, pageSize, sort, search, status, department, hasLogin } -> { items, total, page, page_size }
export async function listEmployees({ page = 1, pageSize = 20, sort, search, status, department, hasLogin }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  if (status) params.status = status
  if (department) params.department = department
  if (hasLogin !== undefined && hasLogin !== null && hasLogin !== '') params.has_login = hasLogin
  const { data } = await apiClient.get(BASE, { params })
  return data
}

// Departments already in use, A-Z (for the filter and the form's suggestions).
export async function listDepartments() {
  const { data } = await apiClient.get(`${BASE}/departments`)
  return data
}

// fields: { employee_code, full_name, department, designation, work_email, phone }
export async function createEmployee(fields) {
  const { data } = await apiClient.post(BASE, fields)
  return data
}

export async function updateEmployee(id, changes) {
  const { data } = await apiClient.patch(`${BASE}/${id}`, changes)
  return data
}

export async function setEmployeeActive(id, active) {
  const { data } = await apiClient.post(`${BASE}/${id}/${active ? 'activate' : 'deactivate'}`)
  return data
}

// "EMP-001 · Asha Kumar"
export function employeeLabel(employee) {
  return employee ? `${employee.employee_code} · ${employee.full_name}` : ''
}
