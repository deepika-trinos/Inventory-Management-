// Calls for assignment history and overdue returns (Slice 5.3: ASN-07, ASN-08, EMP-04; owner's
// answers N7, N8, N10-N13). All read-only. Assigning and returning are in api/assets.js.
import apiClient from './client'

// Admin and IT Manager: { page, pageSize, sort, search } -> { items, total, page, page_size }.
// Overdue = expected return date before today (company timezone), not returned (N7). Most late first.
export async function listOverdue({ page = 1, pageSize = 20, sort, search }) {
  const params = { page, page_size: pageSize }
  if (sort) params.sort = sort
  if (search) params.search = search
  const { data } = await apiClient.get('/api/v1/assignments/overdue', { params })
  return data
}

// Admin and IT Manager: { employee, current: [...], past: [...] } (EMP-04).
export async function getEmployeeAssignments(employeeId) {
  const { data } = await apiClient.get(`/api/v1/employees/${employeeId}/assignments`)
  return data
}

// Employee role only: the logged-in employee's own { employee, current, past } (N8). No condition
// notes or staff e-mails in it (N12).
export async function getMyAssignments() {
  const { data } = await apiClient.get('/api/v1/me/assignments')
  return data
}

/** "2 days overdue" / "1 day overdue" */
export function overdueLabel(days) {
  return `${days} ${days === 1 ? 'day' : 'days'} overdue`
}
