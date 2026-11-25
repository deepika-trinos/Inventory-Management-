// Tests for Slice 6.2 screens (MNT-04 to MNT-07; owner's answers S1-S14): the request page (details,
// buttons by status, "Return it first." while Assigned, final states read-only), the Start / Complete /
// Cancel forms with their checks and confirm boxes, Edit details, the history wording, and the asset
// page's Retire… block while a request is open. The server is replaced by stand-ins (no network).
// Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getAsset, getAssetHistory } from '../../api/assets'
import { cancelRequest, completeWork, getAssetRequests, getRequest, startWork, updateRequest } from '../../api/maintenance'
import { NotificationProvider } from '../../context/NotificationContext'
import { todayInCompanyTimezone } from '../../utils/dates'
import AssetDetailPage from '../assets/AssetDetailPage'
import { maintenanceActionLabel, maintenanceHistoryNote } from './maintenanceHistory'
import MaintenanceRequestPage from './MaintenanceRequestPage'
import { validateProgress } from './RequestProgressDialogs'

vi.mock('../../api/assets', async (importOriginal) => ({
  ...(await importOriginal()),
  getAsset: vi.fn(),
  getAssetHistory: vi.fn(),
}))
vi.mock('../../api/maintenance', async (importOriginal) => ({
  ...(await importOriginal()),
  getRequest: vi.fn(),
  startWork: vi.fn(),
  completeWork: vi.fn(),
  cancelRequest: vi.fn(),
  updateRequest: vi.fn(),
  getAssetRequests: vi.fn(),
}))

const TODAY = todayInCompanyTimezone()
const MANAGER = { id: 2, email: 'manager@example.com', role: 'IT Manager' }
const ASSET = { id: 1, asset_code: 'AST-000004', name: 'Dell Latitude 5440', serial_number: 'DL-504', status: 'available' }
const REPORTED = {
  id: 5, request_number: 'MNT-000001', asset: ASSET, issue_description: 'Screen flickers', priority: 'high',
  status: 'reported', reported_date: '2026-11-20', reported_by: MANAGER, created_at: '2026-11-20T05:00:00Z',
  started_date: null, started_at: null, started_by: null, service_provider: null, repair_notes: null, cost: null,
  completion_date: null, completed_at: null, completed_by: null, cancelled_at: null, cancelled_by: null, cancel_reason: null,
  history: [
    { id: 41, action: 'maintenance.reported', created_at: '2026-11-20T05:00:00Z', actor: MANAGER, before: null,
      after: { request_id: 5, request_number: 'MNT-000001', priority: 'high', issue_description: 'Screen flickers' } },
  ],
}
const IN_PROGRESS = {
  ...REPORTED, status: 'in_progress', asset: { ...ASSET, status: 'under_maintenance' }, started_date: '2026-11-21',
  started_at: '2026-11-21T05:00:00Z', started_by: MANAGER, service_provider: 'Dell Service Centre',
}
const serverError = (code, message, status = 409) => ({ isAxiosError: true, response: { status, data: { error: { code, message } } } })

beforeEach(() => {
  vi.clearAllMocks()
  getRequest.mockResolvedValue(REPORTED)
})

function renderRequest(path = '/maintenance/MNT-000001') {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/maintenance/:requestRef" element={<MaintenanceRequestPage />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

const button = (name) => screen.queryByRole('button', { name })
const confirmLines = () => screen.getAllByTestId('progress-confirm-line').map((l) => l.textContent)

describe('validateProgress (S5-S8, S11)', () => {
  const values = { date: '2026-11-22', provider: '', notes: 'Fixed', cost: '', reason: 'x' }
  const today = '2026-11-24'

  it('start date: not in the future, not before the reported date', () => {
    expect(validateProgress('start', values, REPORTED, today)).toEqual({})
    expect(validateProgress('start', { ...values, date: '2026-11-25' }, REPORTED, today).date).toMatch(/future/)
    expect(validateProgress('start', { ...values, date: '2026-11-19' }, REPORTED, today).date).toMatch(/reported/)
  })

  it('complete: notes required, date not before the start, cost 0 or more with 2 decimals', () => {
    expect(validateProgress('complete', values, IN_PROGRESS, today)).toEqual({})
    expect(validateProgress('complete', { ...values, notes: '  ' }, IN_PROGRESS, today).notes).toBe('Please describe what was done.')
    expect(validateProgress('complete', { ...values, date: '2026-11-20' }, IN_PROGRESS, today).date).toMatch(/before work started/)
    for (const bad of ['-1', '1.234', 'abc', '12345678901']) {
      expect(validateProgress('complete', { ...values, cost: bad }, IN_PROGRESS, today).cost).toBeTruthy()
    }
    for (const good of ['0', '1200', '1200.5', '99.99']) {
      expect(validateProgress('complete', { ...values, cost: good }, IN_PROGRESS, today)).toEqual({})
    }
  })

  it('cancel: reason required, up to 500', () => {
    expect(validateProgress('cancel', { ...values, reason: ' ' }, REPORTED, today).reason).toMatch(/reason/)
    expect(validateProgress('cancel', { ...values, reason: 'x'.repeat(501) }, REPORTED, today).reason).toMatch(/500/)
  })
})

describe('Request page', () => {
  it('shows the request with Start work, Edit and Cancel while Reported', async () => {
    renderRequest()
    expect(await screen.findByRole('heading', { name: 'Request MNT-000001' })).toBeTruthy()
    expect(screen.getByTestId('request-asset').textContent).toContain('AST-000004 · Dell Latitude 5440 · Available')
    expect(button('Start work…').disabled).toBe(false)
    expect(button('Mark completed…')).toBeNull()
    expect(button('Edit details')).toBeTruthy()
    expect(button('Cancel request…')).toBeTruthy()
    expect(screen.getAllByTestId('request-history-row')[0].textContent).toContain('Problem reported')
  })

  it('greys out Start work while the asset is Assigned (S1)', async () => {
    getRequest.mockResolvedValue({ ...REPORTED, asset: { ...ASSET, status: 'assigned' } })
    renderRequest()
    await screen.findByRole('heading', { name: 'Request MNT-000001' })
    expect(button('Start work…').disabled).toBe(true)
  })

  it('starts work after a confirm box that says the asset becomes Under Maintenance', async () => {
    startWork.mockResolvedValue(IN_PROGRESS)
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Start work…' }))

    expect(screen.getByLabelText(/Work started on/).value).toBe(TODAY)
    fireEvent.change(screen.getByLabelText(/Service provider/), { target: { value: 'Dell Service Centre' } })
    fireEvent.click(screen.getByRole('button', { name: 'Start work…' }))
    expect(confirmLines()[0]).toBe('AST-000004 becomes Under Maintenance and cannot be assigned until it is inspected.')
    expect(confirmLines()).toContain('Service provider: Dell Service Centre')
    fireEvent.click(screen.getByRole('button', { name: 'Start work' }))

    expect(await screen.findByText('Work started on MNT-000001. AST-000004 is Under Maintenance.')).toBeTruthy()
    expect(startWork).toHaveBeenCalledWith('MNT-000001', { startedDate: TODAY, serviceProvider: 'Dell Service Centre' })
    expect(button('Mark completed…')).toBeTruthy()
    expect(button('Start work…')).toBeNull()
  })

  it('shows a server refusal on top of the form (e.g. asset assigned meanwhile)', async () => {
    startWork.mockRejectedValue(serverError('asset_assigned', 'AST-000004 is assigned to an employee. Return it first, then start work.'))
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Start work…' }))
    fireEvent.click(screen.getByRole('button', { name: 'Start work…' }))
    fireEvent.click(screen.getByRole('button', { name: 'Start work' }))

    expect((await screen.findByTestId('progress-form-error')).textContent).toContain('Return it first')
  })

  it('completes with notes and cost; the asset stays Under Maintenance', async () => {
    getRequest.mockResolvedValue(IN_PROGRESS)
    completeWork.mockResolvedValue({ ...IN_PROGRESS, status: 'completed', completion_date: TODAY, repair_notes: 'Replaced cable', cost: '1200.50', completed_by: MANAGER, completed_at: '2026-11-24T05:00:00Z' })
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Mark completed…' }))

    fireEvent.click(screen.getByRole('button', { name: 'Mark completed…' }))
    expect(screen.getByText('Please describe what was done.')).toBeTruthy() // notes required (S5)
    fireEvent.change(screen.getByLabelText(/Repair notes/), { target: { value: 'Replaced cable' } })
    fireEvent.change(screen.getByLabelText(/Cost/), { target: { value: '1200.50' } })
    fireEvent.click(screen.getByRole('button', { name: 'Mark completed…' }))
    expect(confirmLines()[0]).toBe('AST-000004 stays Under Maintenance until it is inspected.')
    expect(confirmLines().some((l) => l.startsWith('Cost: ') && l.includes('1,200.50'))).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Mark completed' }))

    expect(await screen.findByText('MNT-000001 completed. AST-000004 stays Under Maintenance until inspected.')).toBeTruthy()
    expect(completeWork).toHaveBeenCalledWith('MNT-000001', {
      repairNotes: 'Replaced cable', completionDate: TODAY, serviceProvider: 'Dell Service Centre', cost: '1200.50',
    })
    expect(screen.getByText('Completed requests are final. Read-only.')).toBeTruthy()
    expect(button('Edit details')).toBeNull()
    expect(button('Cancel request…')).toBeNull()
  })

  it('cancels with a required reason; the confirm box says it cannot be undone', async () => {
    getRequest.mockResolvedValue(IN_PROGRESS)
    cancelRequest.mockResolvedValue({ ...IN_PROGRESS, status: 'cancelled', cancel_reason: 'Not needed', cancelled_by: MANAGER, cancelled_at: '2026-11-24T05:00:00Z' })
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel request…' }))
    fireEvent.change(screen.getByLabelText(/Reason for cancelling/), { target: { value: 'Not needed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel request…' }))
    expect(confirmLines()).toEqual(['Reason: Not needed', 'AST-000004 stays Under Maintenance until it is inspected.', 'This cannot be undone.'])
    fireEvent.click(screen.getByRole('button', { name: 'Cancel request' }))

    expect(await screen.findByText('MNT-000001 cancelled.')).toBeTruthy()
    expect(cancelRequest).toHaveBeenCalledWith('MNT-000001', 'Not needed')
    expect(screen.getByText('Cancelled requests are final. Read-only.')).toBeTruthy()
  })

  it('cancelling a Reported request says the asset keeps its status', async () => {
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Cancel request…' }))
    fireEvent.change(screen.getByLabelText(/Reason for cancelling/), { target: { value: 'Duplicate' } })
    fireEvent.click(screen.getByRole('button', { name: 'Cancel request…' }))
    expect(confirmLines()).toContain('AST-000004 keeps its status.')
  })

  it('edits priority and cost; empty fields are sent as null', async () => {
    updateRequest.mockResolvedValue({ ...REPORTED, priority: 'low' })
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Edit details' }))
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /Priority/ }))
    fireEvent.click(screen.getByRole('option', { name: 'Low' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('MNT-000001 saved.')).toBeTruthy()
    expect(updateRequest).toHaveBeenCalledWith('MNT-000001', { priority: 'low', service_provider: null, repair_notes: null, cost: null })
  })

  it('says when the request does not exist', async () => {
    getRequest.mockRejectedValue(serverError('maintenance_request_not_found', 'Maintenance request not found.', 404))
    renderRequest('/maintenance/MNT-999999')
    expect(await screen.findByText('Request not found')).toBeTruthy()
  })
})

describe('History wording (S13)', () => {
  const ids = { request_id: 5, request_number: 'MNT-000001' }

  it('names each status change', () => {
    const started = { action: 'maintenance.status_changed', before: { ...ids, status: 'reported', asset_status: 'available' }, after: { ...ids, status: 'in_progress', asset_status: 'under_maintenance', started_date: '2026-11-21', service_provider: 'Dell' } }
    expect(maintenanceActionLabel(started)).toBe('Work started')
    expect(maintenanceHistoryNote(started)).toBe('MNT-000001 · Reported → In Progress · asset Under Maintenance · started 21 Nov 2026 · Dell')

    const cancelled = { action: 'maintenance.status_changed', before: { ...ids, status: 'reported' }, after: { ...ids, status: 'cancelled', asset_status: 'available', reason: 'Duplicate' } }
    expect(maintenanceActionLabel(cancelled)).toBe('Request cancelled')
    expect(maintenanceHistoryNote(cancelled)).toBe('MNT-000001 · Reported → Cancelled · asset Available · Reason: Duplicate')

    const completed = { action: 'maintenance.status_changed', before: { ...ids, status: 'in_progress' }, after: { ...ids, status: 'completed', asset_status: 'under_maintenance', completion_date: '2026-11-23', repair_notes: 'Fixed', cost: '0.00' } }
    expect(maintenanceActionLabel(completed)).toBe('Repair completed')
    expect(maintenanceHistoryNote(completed)).toContain('In Progress → Completed · asset Under Maintenance · completed 23 Nov 2026 · Fixed · cost')
  })

  it('lists edited fields with old and new values', () => {
    const edited = { action: 'maintenance.updated', before: { ...ids, priority: 'low', cost: null }, after: { ...ids, priority: 'high', cost: '300.00' } }
    expect(maintenanceActionLabel(edited)).toBe('Request edited')
    expect(maintenanceHistoryNote(edited)).toMatch(/^MNT-000001 · Priority: Low → High; Cost: \(empty\) → .*300\.00$/)
  })
})

describe('Asset page (S14)', () => {
  const PAGE_ASSET = {
    ...ASSET, model: 'Latitude 5440', brand: 'Dell', location: null, warranty_expiry: null, purchase: null,
    purchase_date: null, cost: null, category: { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' },
    created_by: MANAGER, created_at: '2026-11-01T06:30:00Z', updated_at: '2026-11-01T06:30:00Z', current_assignment: null,
  }

  it('greys out Retire… while a request is open and links the request number', async () => {
    getAsset.mockResolvedValue(PAGE_ASSET)
    getAssetHistory.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
    getAssetRequests.mockResolvedValue([REPORTED])
    render(
      <NotificationProvider>
        <MemoryRouter initialEntries={['/assets/AST-000004']}>
          <Routes>
            <Route path="/assets/:assetId" element={<AssetDetailPage />} />
          </Routes>
        </MemoryRouter>
      </NotificationProvider>,
    )
    const region = within(await screen.findByRole('region', { name: 'Maintenance requests' }))
    await waitFor(() => expect(region.getByRole('link', { name: 'MNT-000001' }).getAttribute('href')).toBe('/maintenance/MNT-000001'))
    expect(screen.getByRole('button', { name: 'Retire…' }).disabled).toBe(true)
  })
})
