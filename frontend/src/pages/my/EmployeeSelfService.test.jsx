// Tests for Slice 6.4 screens (MNT-08, PRD 4.2; decisions.md sections 37-38): My Requests (rows, progress
// wording, empty state, no staff-only fields shown, Report a problem… with the asset picker), My Dashboard
// (counts, overdue returns, open requests, a login not linked to an employee), and the Employee home page.
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getMyAssignments } from '../../api/assignments'
import { getMyRequests, myRequestProgress, reportMyProblem } from '../../api/maintenance'
import { NotificationProvider } from '../../context/NotificationContext'
import { canOpen, homePathFor } from '../../routes/navigation'
import MyDashboardPage from './MyDashboardPage'
import MyRequestsPage from './MyRequestsPage'

vi.mock('../../api/assignments', async (importOriginal) => ({
  ...(await importOriginal()),
  getMyAssignments: vi.fn(),
}))
vi.mock('../../api/maintenance', async (importOriginal) => ({
  ...(await importOriginal()),
  getMyRequests: vi.fn(),
  reportMyProblem: vi.fn(),
}))

const ASHA = { id: 1, employee_code: 'EMP-001', full_name: 'Asha Kumar' }
const LAPTOP = { id: 11, asset_code: 'AST-000001', name: 'Dell Latitude 5440', serial_number: 'DL-1001', status: 'assigned' }
const PHONE = { id: 12, asset_code: 'AST-000002', name: 'Pixel 8', serial_number: 'PX-8', status: 'assigned' }
const held = (asset, extra = {}) => ({
  asset, assignment_date: '2026-11-01', expected_return_date: null, return_date: null, return_outcome: null,
  is_open: true, is_overdue: false, days_overdue: null, open_request: null, ...extra,
})
const REQ = (n, status, extra = {}) => ({
  request_number: `MNT-00000${n}`, asset: { asset_code: 'AST-000001', name: 'Dell Latitude 5440', serial_number: 'DL-1001' },
  issue_description: 'Battery drains fast', status, reported_date: '2026-11-20', started_date: null,
  completion_date: null, cancelled_date: null, cancel_reason: null, ...extra,
})
const serverError = (code, message, status = 404) => ({ isAxiosError: true, response: { status, data: { error: { code, message } } } })

beforeEach(() => {
  vi.clearAllMocks()
  getMyAssignments.mockResolvedValue({ employee: ASHA, current: [held(LAPTOP)], past: [] })
  getMyRequests.mockResolvedValue([])
})

function renderAt(path, element) {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={path} element={element} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

describe('myRequestProgress', () => {
  it('reads each stage in plain words', () => {
    expect(myRequestProgress(REQ(1, 'reported'))).toBe('Waiting for the IT team')
    expect(myRequestProgress(REQ(1, 'in_progress', { started_date: '2026-11-21' }))).toBe('Work started 21 Nov 2026')
    expect(myRequestProgress(REQ(1, 'completed', { started_date: '2026-11-21', completion_date: '2026-11-22' }))).toBe(
      'Work started 21 Nov 2026 · Completed 22 Nov 2026',
    )
    expect(myRequestProgress(REQ(1, 'cancelled', { cancelled_date: '2026-11-21', cancel_reason: 'Fixed by restart' }))).toBe(
      'Cancelled 21 Nov 2026 — Reason: Fixed by restart',
    )
  })
})

describe('My Requests', () => {
  it('lists my requests with status and progress, newest first as sent', async () => {
    getMyRequests.mockResolvedValue([
      REQ(2, 'in_progress', { started_date: '2026-11-21' }),
      REQ(1, 'cancelled', { cancelled_date: '2026-11-20', cancel_reason: 'Duplicate' }),
    ])
    renderAt('/my/requests', <MyRequestsPage />)

    const rows = await screen.findAllByTestId('my-request-row')
    expect(rows.map((r) => within(r).getAllByRole('cell')[0].textContent)).toEqual(['MNT-000002', 'MNT-000001'])
    expect(within(rows[0]).getByText('In Progress')).toBeTruthy()
    expect(within(rows[0]).getByTestId('my-request-progress').textContent).toBe('Work started 21 Nov 2026')
    expect(within(rows[1]).getByTestId('my-request-progress').textContent).toContain('Reason: Duplicate')
    // No staff-only columns (N12, O8)
    for (const hidden of ['Priority', 'Service provider', 'Repair notes', 'Cost', 'Inspection']) {
      expect(screen.queryByRole('columnheader', { name: hidden })).toBeNull()
    }
  })

  it('says when there are no requests yet', async () => {
    renderAt('/my/requests', <MyRequestsPage />)
    expect(await screen.findByText('No requests yet')).toBeTruthy()
  })

  it('reports a problem: pick an asset held now (one with an open request is greyed out), then the form', async () => {
    getMyAssignments.mockResolvedValue({
      employee: ASHA,
      current: [held(LAPTOP), held(PHONE, { open_request: { request_number: 'MNT-000003', status: 'reported', reported_date: '2026-11-20' } })],
      past: [],
    })
    reportMyProblem.mockResolvedValue({ request_number: 'MNT-000004' })
    renderAt('/my/requests', <MyRequestsPage />)

    fireEvent.click(await screen.findByRole('button', { name: 'Report a problem…' }))
    const choices = screen.getAllByTestId('pick-asset')
    expect(choices[1].getAttribute('aria-disabled')).toBe('true')
    expect(within(choices[1]).getByText('Problem already reported (MNT-000003)')).toBeTruthy()
    fireEvent.click(choices[0])

    expect(screen.getByText('Report a problem with AST-000001')).toBeTruthy()
    fireEvent.change(screen.getByLabelText(/What is wrong/i), { target: { value: 'Fan noisy' } })
    fireEvent.click(screen.getByRole('button', { name: /^Report/ }))

    expect(await screen.findByText('Problem reported: MNT-000004. The IT team will review it.')).toBeTruthy()
    expect(reportMyProblem).toHaveBeenCalledWith(11, 'Fan noisy')
    expect(getMyRequests).toHaveBeenCalledTimes(2) // reloaded
  })

  it('greys out Report a problem when nothing is held', async () => {
    getMyAssignments.mockResolvedValue({ employee: ASHA, current: [], past: [] })
    renderAt('/my/requests', <MyRequestsPage />)
    await screen.findByText('No requests yet')
    expect(screen.getByRole('button', { name: 'Report a problem…' }).disabled).toBe(true)
  })
})

describe('My Dashboard', () => {
  it('shows my counts, overdue returns and open requests', async () => {
    getMyAssignments.mockResolvedValue({
      employee: ASHA,
      current: [held(LAPTOP, { expected_return_date: '2026-11-10', is_overdue: true, days_overdue: 3 }), held(PHONE)],
      past: [],
    })
    getMyRequests.mockResolvedValue([REQ(2, 'reported'), REQ(1, 'completed', { completion_date: '2026-11-22' })])
    renderAt('/my/dashboard', <MyDashboardPage />)

    expect((await screen.findByTestId('count-held')).textContent).toBe('2')
    expect(screen.getByTestId('count-overdue').textContent).toBe('1')
    expect(screen.getByTestId('count-open').textContent).toBe('1')
    expect(screen.getByTestId('overdue-row').textContent).toContain('AST-000001')
    expect(screen.getByTestId('overdue-row').textContent).toContain('3 days overdue')
    const open = screen.getAllByTestId('open-request-row')
    expect(open).toHaveLength(1)
    expect(open[0].textContent).toContain('MNT-000002')
    expect(screen.getByText(/Welcome, Asha Kumar/)).toBeTruthy()
    expect(screen.getByRole('link', { name: 'My Requests' }).getAttribute('href')).toBe('/my/requests')
  })

  it('says when nothing is overdue and nothing is open', async () => {
    renderAt('/my/dashboard', <MyDashboardPage />)
    expect(await screen.findByText('Nothing overdue.')).toBeTruthy()
    expect(screen.getByText('No open requests.')).toBeTruthy()
  })

  it('a login not linked to an employee still sees its requests', async () => {
    getMyAssignments.mockRejectedValue(
      serverError('employee_not_linked', 'Your login is not linked to an employee record. Ask an Admin.'),
    )
    getMyRequests.mockResolvedValue([REQ(1, 'reported')])
    renderAt('/my/dashboard', <MyDashboardPage />)

    expect((await screen.findByTestId('not-linked')).textContent).toContain('not linked to an employee record')
    expect(screen.getByTestId('count-held').textContent).toBe('—')
    expect(screen.getByTestId('count-open').textContent).toBe('1')
  })
})

describe('Navigation (N11)', () => {
  it('Employees land on My Dashboard; the My pages are for the Employee role only', () => {
    expect(homePathFor('Employee')).toBe('/my/dashboard')
    for (const path of ['/my/dashboard', '/my/assets', '/my/requests']) {
      expect(canOpen('Employee', path)).toBe(true)
      expect(canOpen('IT Manager', path)).toBe(false)
      expect(canOpen('Admin', path)).toBe(false)
    }
  })
})
