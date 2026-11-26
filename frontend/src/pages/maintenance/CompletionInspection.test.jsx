// Tests for Slice 6.3 screens (MNT-07, workflow 7.4; decisions.md sections 35-36): "Awaiting inspection" and
// Inspect… on the request page and the asset page, the inspection form's checks (date, outcome, notes 1,000 /
// 500 for Retired), the confirm box for each outcome, the Inspection section afterwards, the list's
// "Awaiting inspection" filter, and the history wording. The server is replaced by stand-ins (no network).
// Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getAsset, getAssetHistory } from '../../api/assets'
import { earliestInspectionDate, getAssetRequests, getRequest, inspectionLabel, inspectRequest, listRequests } from '../../api/maintenance'
import { NotificationProvider } from '../../context/NotificationContext'
import { todayInCompanyTimezone } from '../../utils/dates'
import AssetDetailPage from '../assets/AssetDetailPage'
import { inspectionConfirmLines, validateInspection } from './InspectDialog'
import { maintenanceActionLabel, maintenanceHistoryNote } from './maintenanceHistory'
import MaintenancePage from './MaintenancePage'
import MaintenanceRequestPage from './MaintenanceRequestPage'

vi.mock('../../api/assets', async (importOriginal) => ({
  ...(await importOriginal()),
  getAsset: vi.fn(),
  getAssetHistory: vi.fn(),
}))
vi.mock('../../api/maintenance', async (importOriginal) => ({
  ...(await importOriginal()),
  getRequest: vi.fn(),
  inspectRequest: vi.fn(),
  getAssetRequests: vi.fn(),
  listRequests: vi.fn(),
}))

const TODAY = todayInCompanyTimezone()
const MANAGER = { id: 2, email: 'manager@example.com', role: 'IT Manager' }
const ASSET = { id: 1, asset_code: 'AST-000004', name: 'Dell Latitude 5440', serial_number: 'DL-504', status: 'under_maintenance' }
const COMPLETED = {
  id: 5, request_number: 'MNT-000001', asset: ASSET, issue_description: 'Screen flickers', priority: 'high',
  status: 'completed', reported_date: '2026-11-20', reported_by: MANAGER, created_at: '2026-11-20T05:00:00Z',
  started_date: '2026-11-21', started_at: '2026-11-21T05:00:00Z', started_by: MANAGER, service_provider: null,
  repair_notes: 'Replaced cable', cost: null, completion_date: '2026-11-22', completed_at: '2026-11-22T05:00:00Z',
  completed_by: MANAGER, cancelled_at: null, cancelled_by: null, cancel_reason: null,
  awaiting_inspection: true, inspection_outcome: null, inspection_date: null, inspection_notes: null,
  inspected_at: null, inspected_by: null,
  history: [],
}
const inspected = (outcome, notes = null) => ({
  ...COMPLETED, asset: { ...ASSET, status: outcome }, awaiting_inspection: false, inspection_outcome: outcome,
  inspection_date: TODAY, inspection_notes: notes, inspected_at: '2026-11-26T05:00:00Z', inspected_by: MANAGER,
})
const serverError = (code, message, status = 409) => ({ isAxiosError: true, response: { status, data: { error: { code, message } } } })

beforeEach(() => {
  vi.clearAllMocks()
  getRequest.mockResolvedValue(COMPLETED)
})

function renderAt(path, routePath, element) {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path={routePath} element={element} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}
const renderRequest = () => renderAt('/maintenance/MNT-000001', '/maintenance/:requestRef', <MaintenanceRequestPage />)
const button = (name) => screen.queryByRole('button', { name })
const confirmLines = () => screen.getAllByTestId('inspect-confirm-line').map((l) => l.textContent)

describe('validateInspection', () => {
  const values = { date: '2026-11-23', outcome: 'available', notes: '' }
  const today = '2026-11-26'

  it('date: not in the future, not before the completion date', () => {
    expect(validateInspection(values, '2026-11-22', today)).toEqual({})
    expect(validateInspection({ ...values, date: '2026-11-27' }, '2026-11-22', today).date).toMatch(/future/)
    expect(validateInspection({ ...values, date: '2026-11-21' }, '2026-11-22', today).date).toMatch(/before 22 Nov 2026/)
    expect(validateInspection({ ...values, date: '2026-11-22' }, '2026-11-22', today)).toEqual({})
  })

  it('outcome required; notes optional for Available, required for Damaged and Retired', () => {
    expect(validateInspection({ ...values, outcome: '' }, null, today).outcome).toBe('Choose the inspection outcome.')
    expect(validateInspection({ ...values, outcome: 'damaged', notes: '  ' }, null, today).notes).toMatch(/required when the outcome is Damaged/)
    expect(validateInspection({ ...values, outcome: 'retired' }, null, today).notes).toMatch(/Retired/)
  })

  it('notes up to 1,000; up to 500 for Retired (the retirement reason)', () => {
    expect(validateInspection({ ...values, outcome: 'damaged', notes: 'x'.repeat(1000) }, null, today)).toEqual({})
    expect(validateInspection({ ...values, outcome: 'damaged', notes: 'x'.repeat(1001) }, null, today).notes).toMatch(/1,000/)
    expect(validateInspection({ ...values, outcome: 'retired', notes: 'x'.repeat(500) }, null, today)).toEqual({})
    expect(validateInspection({ ...values, outcome: 'retired', notes: 'x'.repeat(501) }, null, today).notes).toMatch(/500/)
  })
})

describe('helpers', () => {
  it('the earliest date is the completion date, or the day it was cancelled', () => {
    expect(earliestInspectionDate(COMPLETED)).toBe('2026-11-22')
    expect(earliestInspectionDate({ ...COMPLETED, completion_date: null, cancelled_at: '2026-11-23T05:00:00Z' })).toBe('2026-11-23')
  })

  it('labels a request awaiting or after inspection', () => {
    expect(inspectionLabel(COMPLETED)).toBe('Awaiting inspection')
    expect(inspectionLabel(inspected('damaged', 'x'))).toBe('Inspected: Damaged')
    expect(inspectionLabel({ ...COMPLETED, awaiting_inspection: false })).toBeNull()
  })

  it('the confirm box says what happens to the asset', () => {
    const lines = (outcome, notes = '') => inspectionConfirmLines({ date: '2026-11-26', outcome, notes }, COMPLETED)
    expect(lines('available')).toEqual([
      'AST-000004 becomes Available.', 'It can be assigned again.', 'Inspected on 26 Nov 2026.', 'No condition notes.',
      'An inspection is final and cannot be changed.',
    ])
    expect(lines('damaged', 'Hinge loose')).toContain('Condition: Hinge loose')
    expect(lines('retired', 'Dead board')).toContain(
      'This retires the asset permanently. It cannot be undone, and the asset becomes read-only.',
    )
    expect(lines('retired', 'Dead board')).toContain('Reason for retiring: Dead board')
  })
})

describe('Request page', () => {
  it('shows "Awaiting inspection" and Inspect… for a completed request', async () => {
    renderRequest()
    expect(await screen.findByTestId('awaiting-inspection')).toBeTruthy()
    expect(screen.getByTestId('inspection-pending').textContent).toContain('AST-000004 stays Under Maintenance until it is inspected')
    expect(button('Inspect…')).toBeTruthy()
    expect(screen.queryByText('Completed requests are final. Read-only.')).toBeNull()
  })

  it('inspects as Available after a confirm box, then shows the Inspection section', async () => {
    inspectRequest.mockResolvedValue(inspected('available', 'Works fine'))
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Inspect…' }))

    expect(screen.getByLabelText(/Inspection date/).value).toBe(TODAY)
    fireEvent.click(screen.getByRole('button', { name: 'Inspect…' }))
    expect(screen.getByText('Choose the inspection outcome.')).toBeTruthy()
    fireEvent.click(screen.getByLabelText('Available'))
    fireEvent.change(screen.getByLabelText(/Condition notes/), { target: { value: ' Works fine ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect…' }))
    expect(screen.getByText('Inspect AST-000004 after MNT-000001 — result: Available?')).toBeTruthy()
    expect(confirmLines()[0]).toBe('AST-000004 becomes Available.')
    fireEvent.click(screen.getByRole('button', { name: 'Save inspection' }))

    expect(await screen.findByText('AST-000004 inspected. Status: Available.')).toBeTruthy()
    expect(inspectRequest).toHaveBeenCalledWith('MNT-000001', { outcome: 'available', inspectionDate: TODAY, notes: 'Works fine' })
    expect(screen.getByTestId('inspection-outcome').textContent).toContain('Available')
    expect(screen.getByTestId('inspection-notes').textContent).toContain('Works fine')
    expect(screen.getByTestId('inspection-by').textContent).toContain('manager@example.com')
    expect(button('Inspect…')).toBeNull()
    expect(screen.getByText('Completed requests are final. Read-only.')).toBeTruthy()
  })

  it('Retired needs notes (the reason) and warns that it is permanent', async () => {
    inspectRequest.mockResolvedValue(inspected('retired', 'Motherboard dead'))
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Inspect…' }))
    fireEvent.click(screen.getByLabelText('Retired'))
    expect(screen.getByLabelText(/reason for retiring/)).toBeTruthy()
    expect(screen.getByText('0 / 500 · required for this outcome')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Inspect…' }))
    expect(screen.getByText(/required when the outcome is Retired/)).toBeTruthy()

    fireEvent.change(screen.getByLabelText(/reason for retiring/), { target: { value: 'Motherboard dead' } })
    fireEvent.click(screen.getByRole('button', { name: 'Inspect…' }))
    expect(confirmLines()).toContain('This retires the asset permanently. It cannot be undone, and the asset becomes read-only.')
    fireEvent.click(screen.getByRole('button', { name: 'Retire the asset' }))

    expect(await screen.findByText('AST-000004 inspected. Status: Retired.')).toBeTruthy()
  })

  it('shows a server refusal under the right field or on top', async () => {
    inspectRequest.mockRejectedValueOnce(serverError('inspection_date_before_completion', 'The inspection date cannot be before the repair was completed (2026-11-22).', 422))
    inspectRequest.mockRejectedValueOnce(serverError('request_not_awaiting_inspection', 'MNT-000001 has already been inspected. An inspection is final.'))
    renderRequest()
    fireEvent.click(await screen.findByRole('button', { name: 'Inspect…' }))
    fireEvent.click(screen.getByLabelText('Available'))
    fireEvent.click(screen.getByRole('button', { name: 'Inspect…' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save inspection' }))
    expect(await screen.findByText(/cannot be before the repair was completed/)).toBeTruthy()

    fireEvent.click(await screen.findByRole('button', { name: 'Inspect…' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Save inspection' }))
    expect((await screen.findByTestId('inspect-form-error')).textContent).toContain('already been inspected')
  })

  it('a request cancelled before work started shows no inspection', async () => {
    getRequest.mockResolvedValue({
      ...COMPLETED, status: 'cancelled', started_date: null, started_at: null, started_by: null, completion_date: null,
      completed_at: null, completed_by: null, cancelled_at: '2026-11-21T05:00:00Z', cancelled_by: MANAGER,
      cancel_reason: 'Mistake', awaiting_inspection: false,
    })
    renderRequest()
    expect(await screen.findByText('Cancelled requests are final. Read-only.')).toBeTruthy()
    expect(button('Inspect…')).toBeNull()
    expect(screen.queryByRole('region', { name: 'Inspection' })).toBeNull()
  })
})

describe('Asset page', () => {
  const PAGE_ASSET = {
    ...ASSET, model: 'Latitude 5440', brand: 'Dell', location: null, warranty_expiry: null, purchase: null,
    purchase_date: null, cost: null, category: { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' },
    created_by: MANAGER, created_at: '2026-11-01T06:30:00Z', updated_at: '2026-11-01T06:30:00Z', current_assignment: null,
  }

  it('shows the note and Inspect…, greys out Assign and Report a problem, and inspects', async () => {
    getAsset.mockResolvedValueOnce(PAGE_ASSET).mockResolvedValueOnce({ ...PAGE_ASSET, status: 'available' })
    getAssetHistory.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
    getAssetRequests.mockResolvedValueOnce([COMPLETED]).mockResolvedValueOnce([inspected('available')])
    inspectRequest.mockResolvedValue(inspected('available'))
    renderAt('/assets/AST-000004', '/assets/:assetId', <AssetDetailPage />)

    const note = await screen.findByTestId('awaiting-inspection')
    expect(note.textContent).toContain('Awaiting inspection after MNT-000001')
    expect(within(note).getByRole('link', { name: 'MNT-000001' }).getAttribute('href')).toBe('/maintenance/MNT-000001')
    expect(screen.getByRole('button', { name: 'Assign…' }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: 'Report a problem…' }).disabled).toBe(true)
    const region = within(screen.getByRole('region', { name: 'Maintenance requests' }))
    expect(region.getByTestId('request-inspection').textContent).toBe('Awaiting inspection')

    fireEvent.click(screen.getByRole('button', { name: 'Inspect…' }))
    fireEvent.click(screen.getByLabelText('Available'))
    fireEvent.click(screen.getByRole('button', { name: 'Inspect…' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save inspection' }))

    await waitFor(() => expect(inspectRequest).toHaveBeenCalled())
    expect(await screen.findByText('AST-000004 inspected. Status: Available.')).toBeTruthy()
    await waitFor(() => expect(screen.queryByTestId('awaiting-inspection')).toBeNull())
    expect(getAsset).toHaveBeenCalledTimes(2)
  })
})

describe('Maintenance list', () => {
  it('offers an "Awaiting inspection" filter and shows it under the status', async () => {
    listRequests.mockResolvedValue({ items: [COMPLETED], total: 1, page: 1, page_size: 20 })
    renderAt('/maintenance', '/maintenance', <MaintenancePage />)
    expect(await screen.findByText('Awaiting inspection')).toBeTruthy()

    fireEvent.mouseDown(screen.getByLabelText('Status'))
    fireEvent.click(await screen.findByRole('option', { name: 'Awaiting inspection' }))
    await waitFor(() => expect(listRequests).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'awaiting_inspection' })))
  })
})

describe('History wording', () => {
  it('names the inspection with the outcome, date and notes', () => {
    const entry = {
      action: 'maintenance.inspected',
      before: { request_number: 'MNT-000001', status: 'completed', asset_status: 'under_maintenance' },
      after: { request_number: 'MNT-000001', inspection_outcome: 'damaged', asset_status: 'damaged', inspection_date: '2026-11-26', condition_notes: 'Hinge loose' },
    }
    expect(maintenanceActionLabel(entry)).toBe('Inspected')
    expect(maintenanceHistoryNote(entry)).toBe('MNT-000001 · Under Maintenance → Damaged · inspected 26 Nov 2026 · Hinge loose')
  })
})
