// Tests for assigning on the asset page (Slice 5.1, ASN-01 to ASN-04, BR-02, BR-03):
// "Assign…" only for Available assets (greyed out with the reason otherwise; none on a
// retired asset, which is read-only), the "Assigned to" section with the current holder,
// the history note "Assigned to …", and the page updating after assigning.
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { assignAsset, assignBlockedReason, getAsset, getAssetHistory } from '../../api/assets'
import { listEmployees } from '../../api/employees'
import { NotificationProvider } from '../../context/NotificationContext'
import AssetDetailPage, { historyNote } from './AssetDetailPage'

// Slice 6.1: the asset page also loads its maintenance requests; none here.
vi.mock('../../api/maintenance', async (importOriginal) => ({
  ...(await importOriginal()),
  getAssetRequests: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../../api/assets', async (importOriginal) => ({
  ...(await importOriginal()),
  getAsset: vi.fn(),
  getAssetHistory: vi.fn(),
  assignAsset: vi.fn(),
}))
vi.mock('../../api/employees', async (importOriginal) => ({ ...(await importOriginal()), listEmployees: vi.fn() }))

const USER = { id: 2, email: 'manager@example.com' }
const ASHA = { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar', status: 'active' }
const ASSET = {
  id: 3, asset_code: 'AST-000003', name: 'Laptops: Dell Latitude 5440', brand: 'Dell', model: 'Latitude 5440',
  serial_number: 'DL-1003', status: 'available', location: null, warranty_expiry: null, purchase_date: null, cost: null,
  category: { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' }, purchase: null,
  created_by: USER, created_at: '2026-11-01T06:30:00Z', updated_at: '2026-11-01T06:30:00Z', current_assignment: null,
}
const HOLDING = {
  id: 5, employee: ASHA, assignment_date: '2026-11-20', expected_return_date: '2026-12-20',
  assigned_by: USER, created_at: '2026-11-20T05:00:00Z',
}
const ASSIGNED_ENTRY = {
  id: 40, action: 'assignment.created', created_at: '2026-11-20T05:00:00Z', actor: USER,
  before: { status: 'available' },
  after: { status: 'assigned', employee_name: 'Asha Kumar', employee_code: 'EMP-001', assignment_date: '2026-11-20', expected_return_date: null },
}
const history = (items) => ({ items, total: items.length, page: 1, page_size: 10 })

beforeEach(() => {
  vi.clearAllMocks()
  getAsset.mockResolvedValue(ASSET)
  getAssetHistory.mockResolvedValue(history([]))
  listEmployees.mockResolvedValue({ items: [ASHA], total: 1, page: 1, page_size: 20 })
})

function renderPage() {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={['/assets/AST-000003']}>
        <Routes>
          <Route path="/assets/:assetId" element={<AssetDetailPage />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

describe('Assign button', () => {
  it('is available for an Available asset', async () => {
    renderPage()
    expect((await screen.findByRole('button', { name: 'Assign…' })).disabled).toBe(false)
  })

  it.each([
    ['assigned', 'Already assigned. Return it first.'],
    ['under_maintenance', 'Under Maintenance. Finish the repair first.'],
    ['damaged', 'Damaged assets cannot be assigned.'],
  ])('is greyed out with the reason for a %s asset', async (status, reason) => {
    getAsset.mockResolvedValue({ ...ASSET, status })
    renderPage()
    const button = await screen.findByRole('button', { name: 'Assign…' })
    expect(button.disabled).toBe(true)
    expect(assignBlockedReason(status)).toBe(reason)
    fireEvent.mouseOver(button.parentElement)
    expect(await screen.findByRole('tooltip')).toHaveProperty('textContent', reason)
  })

  it('is not shown on a retired asset (read-only)', async () => {
    getAsset.mockResolvedValue({ ...ASSET, status: 'retired', retired_by: USER, retired_at: '2026-11-21T05:00:00Z', retire_reason: 'Broken' })
    renderPage()
    await screen.findByText('Retired assets are final. Read-only.')
    expect(screen.queryByRole('button', { name: 'Assign…' })).toBeNull()
  })
})

describe('Assigned asset', () => {
  it('shows who holds it, since when and the expected return', async () => {
    getAsset.mockResolvedValue({ ...ASSET, status: 'assigned', current_assignment: HOLDING })
    renderPage()
    const region = within(await screen.findByRole('region', { name: 'Assigned to' }))
    expect(region.getByTestId('asset-assigned-to').textContent).toContain('Asha Kumar (EMP-001)')
    expect(region.getByTestId('asset-assignment-date').textContent).toContain('20 Nov 2026')
    expect(region.getByTestId('asset-expected-return').textContent).toContain('20 Dec 2026')
    expect(region.getByText(/manager@example.com/)).toBeTruthy()
  })

  it('an Available asset has no "Assigned to" section', async () => {
    renderPage()
    await screen.findByRole('button', { name: 'Assign…' })
    expect(screen.queryByRole('region', { name: 'Assigned to' })).toBeNull()
  })

  it('history says "Assigned to …"', async () => {
    getAssetHistory.mockResolvedValue(history([ASSIGNED_ENTRY]))
    renderPage()
    expect(await screen.findByText('Assigned')).toBeTruthy()
    expect(screen.getByText('Assigned to Asha Kumar (EMP-001) · from 20 Nov 2026')).toBeTruthy()
    expect(historyNote({ ...ASSIGNED_ENTRY, after: { ...ASSIGNED_ENTRY.after, expected_return_date: '2026-12-20' } })).toBe(
      'Assigned to Asha Kumar (EMP-001) · from 20 Nov 2026 · expected back 20 Dec 2026',
    )
  })
})

describe('Assigning from the page', () => {
  it('opens the form, confirms, then shows the new holder and refreshes the history', async () => {
    assignAsset.mockResolvedValue({ ...ASSET, status: 'assigned', current_assignment: HOLDING })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Assign…' }))
    const d = within(await screen.findByRole('dialog', { name: 'Assign AST-000003' }))
    fireEvent.change(d.getByRole('combobox', { name: /^Employee/ }), { target: { value: 'asha' } })
    fireEvent.click(await screen.findByRole('option', { name: /Asha Kumar/ }))
    fireEvent.click(d.getByRole('button', { name: 'Assign…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: 'Assign AST-000003 to Asha Kumar (EMP-001)?' })).getByRole('button', { name: 'Assign' }))

    expect(await screen.findByText('AST-000003 assigned to Asha Kumar (EMP-001).')).toBeTruthy()
    expect(await screen.findByRole('region', { name: 'Assigned to' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Assign…' }).disabled).toBe(true)
    await waitFor(() => expect(getAssetHistory.mock.calls.length).toBeGreaterThan(1))
  })
})
