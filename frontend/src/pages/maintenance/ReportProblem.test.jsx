// Tests for Slice 6.1 screens (MNT-01 to MNT-03; owner's answers Q9, Q10, O1-O14): the report form
// (staff: issue, priority, date; Employee: issue only), the asset page ("Report a problem…", greyed
// out while a request is open, not on Retired assets; "Maintenance requests" section; history note),
// My Assets ("Report a problem" on held assets, "Problem reported (MNT-…)" while open) and the
// Maintenance page (list, status filter, row opens the asset). The server is replaced by stand-ins
// (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useParams } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getAsset, getAssetHistory } from '../../api/assets'
import { getMyAssignments } from '../../api/assignments'
import { getAssetRequests, listRequests, reportMyProblem, reportProblem } from '../../api/maintenance'
import { NotificationProvider } from '../../context/NotificationContext'
import { todayInCompanyTimezone } from '../../utils/dates'
import AssetDetailPage, { historyNote } from '../assets/AssetDetailPage'
import MyAssetsPage from '../my/MyAssetsPage'
import MaintenancePage from './MaintenancePage'
import ReportProblemDialog, { validateReport } from './ReportProblemDialog'

vi.mock('../../api/assets', async (importOriginal) => ({
  ...(await importOriginal()),
  getAsset: vi.fn(),
  getAssetHistory: vi.fn(),
}))
vi.mock('../../api/assignments', async (importOriginal) => ({ ...(await importOriginal()), getMyAssignments: vi.fn() }))
vi.mock('../../api/maintenance', async (importOriginal) => ({
  ...(await importOriginal()),
  reportProblem: vi.fn(),
  reportMyProblem: vi.fn(),
  getAssetRequests: vi.fn(),
  listRequests: vi.fn(),
}))

const TODAY = todayInCompanyTimezone()
const USER = { id: 2, email: 'manager@example.com' }
const ASHA = { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar', status: 'active' }
const ASSET = {
  id: 1, asset_code: 'AST-000001', name: 'Dell Latitude 5440', serial_number: 'DL-1001', model: 'Latitude 5440',
  brand: 'Dell', status: 'available', location: null, warranty_expiry: null, purchase: null, purchase_date: null,
  cost: null, category: { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' },
  created_by: USER, created_at: '2026-11-01T06:30:00Z', updated_at: '2026-11-01T06:30:00Z', current_assignment: null,
}
const REQUEST = {
  id: 5, request_number: 'MNT-000001', asset: { id: 1, asset_code: 'AST-000001', name: 'Dell Latitude 5440', serial_number: 'DL-1001', status: 'assigned' },
  issue_description: 'Screen flickers', priority: 'high', status: 'reported', reported_date: '2026-11-20',
  reported_by: { id: 9, email: 'asha@example.com', role: 'Employee' }, created_at: '2026-11-20T05:00:00Z',
}
const page = (items) => ({ items, total: items.length, page: 1, page_size: 20 })
const serverError = (code, message, status = 422) => ({ isAxiosError: true, response: { status, data: { error: { code, message } } } })
const HELD = {
  id: 11, asset: { id: 1, asset_code: 'AST-000001', name: 'Dell Latitude 5440', serial_number: 'DL-1001', status: 'assigned' },
  assignment_date: '2026-11-10', expected_return_date: null, return_date: null, return_outcome: null,
  is_open: true, is_overdue: false, days_overdue: 0, open_request: null,
}
const RETURNED = { ...HELD, id: 10, asset: { ...HELD.asset, id: 2, asset_code: 'AST-000002' }, is_open: false, return_date: '2026-11-12', return_outcome: 'available' }

beforeEach(() => {
  vi.clearAllMocks()
  getAsset.mockResolvedValue(ASSET)
  getAssetHistory.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
  getAssetRequests.mockResolvedValue([])
  getMyAssignments.mockResolvedValue({ employee: ASHA, current: [HELD], past: [RETURNED] })
  listRequests.mockResolvedValue(page([REQUEST]))
})

function AssetStandIn() {
  const { assetId } = useParams()
  return <p>Asset page {assetId}</p>
}

function RequestStandIn() {
  const { requestRef } = useParams()
  return <p>Request page {requestRef}</p>
}

function renderAt(path, element, routePath = path) {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={routePath} element={element} />
          <Route path="/assets/:assetId" element={<AssetStandIn />} />
          <Route path="/maintenance/:requestRef" element={<RequestStandIn />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

const renderAssetPage = () => renderAt('/assets/AST-000001', <AssetDetailPage />, '/assets/:assetId')
const region = (name) => within(screen.getByRole('region', { name }))
const issueBox = () => screen.getByRole('textbox', { name: /What is wrong/ })

describe('validateReport (O4, O5)', () => {
  const ok = { issue: 'Screen flickers', reportedDate: '2026-11-20' }
  const opts = { staff: true, addedDate: '2026-11-01', today: '2026-11-24' }

  it('accepts a normal report', () => {
    expect(validateReport(ok, opts)).toEqual({})
  })

  it('needs the issue, up to 1,000 characters', () => {
    expect(validateReport({ ...ok, issue: '   ' }, opts).issue).toBe('Please describe the problem.')
    expect(validateReport({ ...ok, issue: 'x'.repeat(1001) }, opts).issue).toMatch(/at most 1,000/)
    expect(validateReport({ ...ok, issue: 'x'.repeat(1000) }, opts)).toEqual({})
  })

  it('staff date: not in the future, not before the asset was added', () => {
    expect(validateReport({ ...ok, reportedDate: '2026-11-25' }, opts).reportedDate).toMatch(/future/)
    expect(validateReport({ ...ok, reportedDate: '2026-10-31' }, opts).reportedDate).toMatch(/before the asset was added/)
    expect(validateReport({ ...ok, reportedDate: '2026-11-01' }, opts)).toEqual({})
  })

  it('an Employee has no date to check', () => {
    expect(validateReport({ issue: 'x', reportedDate: '' }, { staff: false, today: '2026-11-24' })).toEqual({})
  })
})

describe('ReportProblemDialog', () => {
  const renderDialog = (props) => {
    const onReported = vi.fn()
    render(<ReportProblemDialog open asset={ASSET} onClose={vi.fn()} onReported={onReported} {...props} />)
    return onReported
  }

  it('staff send the issue, priority and date', async () => {
    reportProblem.mockResolvedValue(REQUEST)
    const onReported = renderDialog({ staff: true })

    fireEvent.change(issueBox(), { target: { value: '  Screen flickers  ' } })
    expect(screen.getByText('15 / 1,000')).toBeTruthy()
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /Priority/ }))
    expect(screen.getAllByRole('option').map((o) => o.textContent)).toEqual(['None', 'Low', 'Medium', 'High'])
    fireEvent.click(screen.getByRole('option', { name: 'High' }))
    expect(screen.getByLabelText(/Reported date/).value).toBe(TODAY)
    fireEvent.click(screen.getByRole('button', { name: 'Report problem' }))

    await waitFor(() => expect(onReported).toHaveBeenCalledWith(REQUEST))
    expect(reportProblem).toHaveBeenCalledWith('AST-000001', { issue: 'Screen flickers', priority: 'high', reportedDate: TODAY })
  })

  it('an Employee sends the issue only: no priority, no date (Q10, O5)', async () => {
    reportMyProblem.mockResolvedValue(REQUEST)
    const onReported = renderDialog()

    expect(screen.queryByRole('combobox', { name: /Priority/ })).toBeNull()
    expect(screen.queryByLabelText(/Reported date/)).toBeNull()
    fireEvent.change(issueBox(), { target: { value: 'Battery drains fast' } })
    fireEvent.click(screen.getByRole('button', { name: 'Report problem' }))

    await waitFor(() => expect(onReported).toHaveBeenCalled())
    expect(reportMyProblem).toHaveBeenCalledWith(1, 'Battery drains fast')
  })

  it('checks the issue before asking the server', () => {
    renderDialog({ staff: true })
    fireEvent.click(screen.getByRole('button', { name: 'Report problem' }))

    expect(screen.getByText('Please describe the problem.')).toBeTruthy()
    expect(reportProblem).not.toHaveBeenCalled()
  })

  it('shows a server problem under its field, or on top', async () => {
    reportProblem.mockRejectedValueOnce(serverError('reported_date_before_asset_created', 'Too early.'))
    renderDialog({ staff: true })
    fireEvent.change(issueBox(), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Report problem' }))
    expect(await screen.findByText('Too early.')).toBeTruthy()

    reportProblem.mockRejectedValueOnce(serverError('maintenance_request_open', 'MNT-000001 is already open for AST-000001.', 409))
    fireEvent.click(screen.getByRole('button', { name: 'Report problem' }))
    expect((await screen.findByTestId('report-form-error')).textContent).toContain('MNT-000001 is already open')
  })
})

describe('Asset page (MNT-02, O1, O2, O12)', () => {
  it('reports a problem: the request appears, the status stays (Q9)', async () => {
    reportProblem.mockResolvedValue({ ...REQUEST, asset: { ...REQUEST.asset, status: 'available' } })
    renderAssetPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })
    expect(region('Maintenance requests').getByText('No maintenance requests.')).toBeTruthy()

    fireEvent.click(await screen.findByRole('button', { name: 'Report a problem…' }))
    getAssetRequests.mockResolvedValue([REQUEST])
    fireEvent.change(issueBox(), { target: { value: 'Screen flickers' } })
    fireEvent.click(screen.getByRole('button', { name: 'Report problem' }))

    expect(await screen.findByText('MNT-000001 reported.')).toBeTruthy()
    const rows = await region('Maintenance requests').findAllByTestId('maintenance-request-row')
    expect(rows[0].textContent).toContain('MNT-000001')
    expect(rows[0].textContent).toContain('asha@example.com (Employee)')
    expect(rows[0].textContent).toContain('High')
    expect(rows[0].textContent).toContain('Reported')
    expect(region('Details').getByText('Available')).toBeTruthy()
    expect(getAssetHistory).toHaveBeenCalledTimes(2) // history refreshed
  })

  it('greys out the button while a request is open', async () => {
    getAssetRequests.mockResolvedValue([REQUEST])
    renderAssetPage()
    const button = await screen.findByRole('button', { name: 'Report a problem…' })
    await waitFor(() => expect(button.disabled).toBe(true))
  })

  it('allows a new report when the earlier request is closed', async () => {
    getAssetRequests.mockResolvedValue([{ ...REQUEST, status: 'completed' }])
    renderAssetPage()
    const button = await screen.findByRole('button', { name: 'Report a problem…' })
    await waitFor(() => expect(button.disabled).toBe(false))
  })

  it('has no button on a retired asset (O1)', async () => {
    getAsset.mockResolvedValue({ ...ASSET, status: 'retired', retired_by: USER, retired_at: '2026-11-22T06:30:00Z', retire_reason: 'Old' })
    renderAssetPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })
    expect(screen.queryByRole('button', { name: 'Report a problem…' })).toBeNull()
  })

  it('history shows the report', () => {
    const entry = { action: 'maintenance.reported', after: { request_number: 'MNT-000001', priority: 'high', issue_description: 'Screen flickers' } }
    expect(historyNote(entry)).toBe('MNT-000001 · High · Screen flickers')
    expect(historyNote({ ...entry, after: { ...entry.after, priority: null } })).toBe('MNT-000001 · Screen flickers')
  })
})

describe('My Assets (MNT-01, O3, O6, O12)', () => {
  it('reports a problem with a held asset, then shows it as reported', async () => {
    reportMyProblem.mockResolvedValue(REQUEST)
    renderAt('/my/assets', <MyAssetsPage />)
    await screen.findByRole('heading', { name: 'My Assets' })
    expect(region('Past assignments').queryAllByRole('button')).toHaveLength(0) // returned: no report (O6)

    fireEvent.click(region('Current assets').getByRole('button', { name: 'Report a problem' }))
    getMyAssignments.mockResolvedValue({
      employee: ASHA, current: [{ ...HELD, open_request: { request_number: 'MNT-000001', status: 'reported', reported_date: '2026-11-20' } }], past: [RETURNED],
    })
    fireEvent.change(issueBox(), { target: { value: 'Battery drains fast' } })
    fireEvent.click(screen.getByRole('button', { name: 'Report problem' }))

    expect(await screen.findByText('Problem reported: MNT-000001. The IT team will review it.')).toBeTruthy()
    expect(reportMyProblem).toHaveBeenCalledWith(1, 'Battery drains fast')
    expect((await screen.findByTestId('open-request')).textContent).toBe('Problem reported (MNT-000001)')
    expect(screen.queryByRole('button', { name: 'Report a problem' })).toBeNull()
  })
})

describe('Maintenance page (O12)', () => {
  it('lists the requests and a row opens the request page (Slice 6.2)', async () => {
    renderAt('/maintenance', <MaintenancePage />)

    expect(await screen.findByText('MNT-000001')).toBeTruthy()
    expect(screen.getByText('AST-000001 · Dell Latitude 5440')).toBeTruthy()
    expect(screen.getByText('Screen flickers')).toBeTruthy()
    expect(screen.getByText('asha@example.com (Employee)')).toBeTruthy()
    expect(listRequests).toHaveBeenCalledWith(expect.objectContaining({ sort: '-request_number', status: '' }))

    fireEvent.click(screen.getByRole('row', { name: 'Open MNT-000001 (AST-000001)' }))
    expect(await screen.findByText('Request page MNT-000001')).toBeTruthy()
  })

  it('filters by status and says when the list is empty', async () => {
    renderAt('/maintenance', <MaintenancePage />)
    await screen.findByText('MNT-000001')

    listRequests.mockResolvedValue(page([]))
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Status' }))
    fireEvent.click(screen.getByRole('option', { name: 'Completed' }))

    await waitFor(() => expect(listRequests).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'completed' })))
    expect(await screen.findByText('No matches')).toBeTruthy()
  })
})
