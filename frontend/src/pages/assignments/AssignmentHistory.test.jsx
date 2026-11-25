// Tests for Slice 5.3 screens (ASN-07, ASN-08, EMP-04; owner's answers N7, N8, N10-N13):
// the employee page (current assets with the overdue badge, past assignments with return details),
// the Assignments page (overdue list: rows, days overdue, search, "No overdue returns", row opens the
// asset), My Assets (own records only, read-only, no notes or staff e-mails) and the Employee's home
// page. The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useParams } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getEmployeeAssignments, getMyAssignments, listOverdue } from '../../api/assignments'
import { getEmployee } from '../../api/employees'
import { NotificationProvider } from '../../context/NotificationContext'
import { homePathFor } from '../../routes/navigation'
import EmployeeDetailPage from '../employees/EmployeeDetailPage'
import MyAssetsPage from '../my/MyAssetsPage'
import AssignmentsPage from './AssignmentsPage'

vi.mock('../../api/assignments', async (importOriginal) => ({
  ...(await importOriginal()),
  listOverdue: vi.fn(),
  getEmployeeAssignments: vi.fn(),
  getMyAssignments: vi.fn(),
}))
vi.mock('../../api/employees', async (importOriginal) => ({ ...(await importOriginal()), getEmployee: vi.fn() }))

const USER = { id: 2, email: 'manager@example.com' }
const ASHA = { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar', status: 'active' }
const RAVI = { id: 4, employee_code: 'EMP-002', full_name: 'Ravi Shah', status: 'active' }
const laptop = (n, status = 'assigned') => ({ id: n, asset_code: `AST-00000${n}`, name: 'Dell Latitude 5440', serial_number: `DL-50${n}`, status })

const CURRENT = {
  id: 11, asset: laptop(2), employee: ASHA, assignment_date: '2026-11-10', expected_return_date: '2026-11-20',
  return_date: null, return_outcome: null, is_open: true, is_overdue: true, days_overdue: 4,
  assigned_by: USER, created_at: '2026-11-10T05:00:00Z', condition_notes: null, returned_by: null, returned_at: null,
}
const PAST = {
  id: 10, asset: laptop(1, 'available'), employee: ASHA, assignment_date: '2026-11-01', expected_return_date: null,
  return_date: '2026-11-05', return_outcome: 'damaged', is_open: false, is_overdue: false, days_overdue: 0,
  assigned_by: USER, created_at: '2026-11-01T05:00:00Z', condition_notes: 'Screen cracked', returned_by: USER,
  returned_at: '2026-11-05T06:00:00Z',
}
// What My Assets receives: no notes, no staff e-mails (N12).
const strip = ({ employee, assigned_by, created_at, condition_notes, returned_by, returned_at, ...rest }) => rest // eslint-disable-line no-unused-vars
const page = (items) => ({ items, total: items.length, page: 1, page_size: 20 })

beforeEach(() => {
  vi.clearAllMocks()
  getEmployee.mockResolvedValue({ ...ASHA, department: 'Finance', designation: null, work_email: null, phone: null, user: null })
  getEmployeeAssignments.mockResolvedValue({ employee: ASHA, current: [CURRENT], past: [PAST] })
  getMyAssignments.mockResolvedValue({ employee: ASHA, current: [strip(CURRENT)], past: [strip(PAST)] })
  listOverdue.mockResolvedValue(page([CURRENT, { ...CURRENT, id: 12, asset: laptop(7), employee: RAVI, days_overdue: 1 }]))
})

function AssetStandIn() {
  const { assetId } = useParams()
  return <p>Asset page {assetId}</p>
}

function renderAt(path, element, routePath = path) {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={routePath} element={element} />
          <Route path="/assets/:assetId" element={<AssetStandIn />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

const region = (name) => within(screen.getByRole('region', { name }))

describe('Employee page (EMP-04, ASN-07)', () => {
  it('shows current assets with the overdue badge and past assignments with return details', async () => {
    renderAt('/employees/3', <EmployeeDetailPage />, '/employees/:employeeId')

    expect(await screen.findByRole('heading', { name: 'Asha Kumar (EMP-001)' })).toBeTruthy()
    expect(getEmployeeAssignments).toHaveBeenCalledWith('3')
    const current = region('Current assets')
    expect(current.getByRole('link', { name: 'AST-000002' }).getAttribute('href')).toBe('/assets/AST-000002')
    expect(current.getByTestId('overdue-badge').textContent).toBe('4 days overdue')
    expect(current.getByText('manager@example.com')).toBeTruthy()

    const past = region('Past assignments')
    expect(past.getByRole('link', { name: 'AST-000001' })).toBeTruthy()
    expect(past.getByText('05 Nov 2026')).toBeTruthy()
    expect(past.getByText('Damaged')).toBeTruthy()
    expect(past.getByText('Screen cracked')).toBeTruthy()
  })

  it('an employee with nothing shows empty messages', async () => {
    getEmployeeAssignments.mockResolvedValue({ employee: ASHA, current: [], past: [] })
    renderAt('/employees/3', <EmployeeDetailPage />, '/employees/:employeeId')
    expect(await screen.findByText('No assets held now.')).toBeTruthy()
    expect(screen.getByText('No past assignments.')).toBeTruthy()
  })

  it('an unknown employee says "Employee not found"', async () => {
    getEmployee.mockRejectedValue({ response: { status: 404, data: { error: { code: 'employee_not_found', message: 'Employee not found.' } } } })
    renderAt('/employees/999', <EmployeeDetailPage />, '/employees/:employeeId')
    expect(await screen.findByText('Employee not found')).toBeTruthy()
  })
})

describe('Assignments page: overdue returns (ASN-08, N7, N10)', () => {
  it('lists overdue items most late first with days overdue', async () => {
    renderAt('/assignments', <AssignmentsPage />)

    expect(await screen.findByText('AST-000002')).toBeTruthy()
    expect(listOverdue.mock.calls[0][0]).toMatchObject({ page: 1, sort: 'expected_return_date' })
    for (const header of ['Asset ID', 'Asset', 'Employee', 'Assigned on', 'Expected return', 'Overdue']) {
      expect(screen.getByRole('columnheader', { name: header })).toBeTruthy()
    }
    expect(screen.getByText('4 days overdue')).toBeTruthy()
    expect(screen.getByText('1 day overdue')).toBeTruthy()
    expect(screen.getByText('Ravi Shah (EMP-002)')).toBeTruthy()
  })

  it('searches on the server', async () => {
    renderAt('/assignments', <AssignmentsPage />)
    await screen.findByText('AST-000002')
    fireEvent.change(screen.getByRole('textbox', { name: 'Search' }), { target: { value: 'ravi' } })
    await waitFor(() => expect(listOverdue.mock.calls.at(-1)[0]).toMatchObject({ search: 'ravi' }))
  })

  it('says "No overdue returns" when there are none', async () => {
    listOverdue.mockResolvedValue(page([]))
    renderAt('/assignments', <AssignmentsPage />)
    expect(await screen.findByText('No overdue returns')).toBeTruthy()
  })

  it('a row opens the asset page', async () => {
    renderAt('/assignments', <AssignmentsPage />)
    await screen.findByText('AST-000002')
    fireEvent.click(screen.getByRole('row', { name: 'Open AST-000007' }))
    expect(await screen.findByText('Asset page AST-000007')).toBeTruthy()
  })
})

describe('My Assets (N8, N11-N13)', () => {
  it('shows the employee own current and past assets, read-only, without notes or staff e-mails', async () => {
    renderAt('/my/assets', <MyAssetsPage />)

    expect(await screen.findByRole('heading', { name: 'My Assets' })).toBeTruthy()
    const current = region('Current assets')
    expect(current.getByText('AST-000002 · Dell Latitude 5440')).toBeTruthy()
    expect(current.getByTestId('overdue-badge').textContent).toBe('4 days overdue')
    const past = region('Past assignments')
    expect(past.getByText('Damaged')).toBeTruthy()
    expect(screen.queryByText('Screen cracked')).toBeNull()
    expect(screen.queryByText(/@example\.com/)).toBeNull()
    expect(screen.queryByRole('columnheader', { name: 'Condition notes' })).toBeNull()
    expect(screen.queryByRole('link', { name: /AST-/ })).toBeNull() // employees cannot open asset pages
    // Nothing to change, except "Report a problem" on the asset held now (Slice 6.1, MNT-01).
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual(['Report a problem'])
    expect(past.queryAllByRole('button')).toHaveLength(0) // not for a returned asset (O6)
  })

  it('says when nothing is held', async () => {
    getMyAssignments.mockResolvedValue({ employee: ASHA, current: [], past: [] })
    renderAt('/my/assets', <MyAssetsPage />)
    expect(await screen.findByText('You hold no assets right now.')).toBeTruthy()
  })

  it('Employees land on My Assets after login; staff still land on the dashboard (N11)', () => {
    expect(homePathFor('Employee')).toBe('/my/assets')
    expect(homePathFor('IT Manager')).toBe('/dashboard')
    expect(homePathFor('Admin')).toBe('/dashboard')
  })
})
