// Tests for the asset page /assets/:assetId (Slice 4.1, AST-02, AST-05): details,
// purchase (with links) or "entered by hand", who created it and when, the history
// (audit log entries, newest first), and the loading, not-found and error states.
// Slice 4.2: Edit and Retire… buttons, a retired asset's read-only view with who / when /
// why, Retire… only for Available or Damaged, and the history note for each edit.
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getAsset, getAssetHistory, retireAsset, updateAsset } from '../../api/assets'
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
  updateAsset: vi.fn(),
  retireAsset: vi.fn(),
}))

const USER = { id: 2, email: 'manager@example.com' }
const ASSET = {
  id: 1,
  asset_code: 'AST-000001',
  name: 'Laptops: Dell Latitude 5440',
  category: { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' },
  brand: 'Dell',
  model: 'Latitude 5440',
  serial_number: 'DL-1001',
  status: 'available',
  location: 'Bangalore Floor 2',
  warranty_expiry: '2029-11-10',
  purchase_date: '2026-11-10',
  cost: '85000.00',
  purchase: { purchase_id: 9, purchase_number: 'PUR-000009', purchase_line_id: 11, vendor_id: 4, vendor: 'Acme IT Supplies', reference_number: 'INV-2026-0042' },
  created_by: USER,
  created_at: '2026-11-12T06:30:00Z',
  updated_at: '2026-11-12T06:30:00Z',
}
const CREATED = {
  id: 31, action: 'asset.created', created_at: '2026-11-12T06:30:00Z', actor: USER, before: null,
  after: { asset_code: 'AST-000001', purchase_number: 'PUR-000009' },
}
const history = (items) => ({ items, total: items.length, page: 1, page_size: 10 })

beforeEach(() => {
  vi.clearAllMocks()
  getAsset.mockResolvedValue(ASSET)
  getAssetHistory.mockResolvedValue(history([CREATED]))
})

function renderPage(path = '/assets/AST-000001') {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/assets/:assetId" element={<AssetDetailPage />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

const section = (name) => within(screen.getByRole('region', { name }))

describe('AssetDetailPage', () => {
  it('loads the asset from the address (asset ID or id)', async () => {
    renderPage('/assets/7')
    await screen.findByRole('heading', { name: 'Asset AST-000001' })
    expect(getAsset).toHaveBeenCalledWith('7')
    expect(getAssetHistory).toHaveBeenCalledWith('AST-000001', expect.objectContaining({ page: 1 }))
  })

  it('shows the details, status and who created it', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })

    const details = section('Details')
    for (const text of ['Laptops: Dell Latitude 5440', 'Laptops', 'DL-1001', 'Latitude 5440', 'Dell', 'Bangalore Floor 2', '10 Nov 2029']) {
      expect(details.getByText(text)).toBeTruthy()
    }
    expect(screen.getAllByText('Available').length).toBeGreaterThan(0)
    expect(screen.getByTestId('asset-created-by').textContent).toContain('manager@example.com')
    expect(screen.getByTestId('asset-created-by').textContent).toContain('12 Nov 2026')
  })

  it('shows the purchase with links to the purchase and the vendor', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })

    const purchase = section('Purchase')
    expect(purchase.getByRole('link', { name: 'PUR-000009' }).getAttribute('href')).toBe('/purchases/9')
    expect(purchase.getByRole('link', { name: 'Acme IT Supplies' }).getAttribute('href')).toBe('/vendors/4')
    expect(purchase.getByText('INV-2026-0042')).toBeTruthy()
    expect(purchase.getByText('10 Nov 2026')).toBeTruthy()
    expect(purchase.getByText(/85,000\.00/)).toBeTruthy()
  })

  it('an asset entered by hand has no purchase', async () => {
    getAsset.mockResolvedValue({ ...ASSET, purchase: null, purchase_date: null, cost: null })
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })

    expect(section('Purchase').getByText('Entered by hand (existing equipment, no purchase or vendor)')).toBeTruthy()
    expect(section('Purchase').queryByRole('link')).toBeNull()
    expect(screen.getByTestId('asset-origin').textContent).toBe('Entered by hand')
  })

  it('shows the history: when, what, by whom and details', async () => {
    renderPage()
    const hist = within(await screen.findByRole('region', { name: 'History' }))

    expect(await hist.findByText('Created')).toBeTruthy()
    expect(hist.getByText('manager@example.com')).toBeTruthy()
    expect(hist.getByText('Received on purchase PUR-000009')).toBeTruthy()
    expect(hist.getByText(/12 Nov 2026/)).toBeTruthy()
  })

  it('an empty history says so', async () => {
    getAssetHistory.mockResolvedValue(history([]))
    renderPage()
    const hist = within(await screen.findByRole('region', { name: 'History' }))
    expect(await hist.findByText('No history recorded')).toBeTruthy()
  })

  it('history notes: entered by hand, a reason, a system action', () => {
    expect(historyNote({ action: 'asset.created', after: { purchase_number: null } })).toBe('Entered by hand')
    expect(historyNote({ action: 'asset.retired', after: { reason: 'Broken screen' } })).toBe('Reason: Broken screen')
    expect(historyNote({ action: 'asset.something', after: null })).toBe('')
  })

  it('an unknown asset shows "Asset not found" with a link back', async () => {
    getAsset.mockRejectedValue({ response: { status: 404, data: { error: { code: 'asset_not_found', message: 'Asset not found.' } } } })
    renderPage('/assets/AST-999999')

    expect(await screen.findByText('Asset not found')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'All assets' }).getAttribute('href')).toBe('/assets')
  })

  it('a server error offers Try again', async () => {
    getAsset.mockRejectedValue({ response: { status: 500, data: { error: { code: 'internal_error', message: 'Something went wrong.' } } } })
    renderPage()
    expect(await screen.findByRole('button', { name: /try again|retry/i })).toBeTruthy()
  })

  // ---- Slice 4.2 ------------------------------------------------------------------------
  it('an available asset shows Edit and Retire… buttons', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })
    expect(screen.getByRole('button', { name: 'Edit' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Retire…' }).disabled).toBe(false)
  })

  it.each(['assigned', 'under_maintenance'])('a %s asset can be edited but not retired', async (status) => {
    getAsset.mockResolvedValue({ ...ASSET, status })
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })
    expect(screen.getByRole('button', { name: 'Edit' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Retire…' }).disabled).toBe(true)
  })

  it('a retired asset is read-only and shows who retired it, when and why', async () => {
    getAsset.mockResolvedValue({
      ...ASSET, status: 'retired', retired_by: USER, retired_at: '2026-11-22T06:30:00Z', retire_reason: 'Stolen from the Chennai office',
    })
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })

    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Retire…' })).toBeNull()
    expect(screen.getByText('Retired assets are final. Read-only.')).toBeTruthy()
    expect(screen.getByTestId('asset-retired-by').textContent).toContain('manager@example.com')
    expect(screen.getByTestId('asset-retired-by').textContent).toContain('22 Nov 2026')
    expect(screen.getByTestId('asset-retire-reason').textContent).toContain('Stolen from the Chennai office')
  })

  it('editing saves, shows the new values and reloads the history', async () => {
    updateAsset.mockResolvedValue({ ...ASSET, location: 'Chennai' })
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })
    const historyCalls = getAssetHistory.mock.calls.length

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    const dialog = within(await screen.findByRole('dialog'))
    fireEvent.change(dialog.getByLabelText('Location'), { target: { value: 'Chennai' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
    expect(updateAsset).toHaveBeenCalledWith('AST-000001', expect.objectContaining({ location: 'Chennai' }))
    expect(section('Details').getByText('Chennai')).toBeTruthy()
    expect(await screen.findByText('AST-000001 saved.')).toBeTruthy()
    await waitFor(() => expect(getAssetHistory.mock.calls.length).toBeGreaterThan(historyCalls))
  })

  it('retiring shows the retired view afterwards', async () => {
    retireAsset.mockResolvedValue({ ...ASSET, status: 'retired', retired_by: USER, retired_at: '2026-11-22T06:30:00Z', retire_reason: 'End of life' })
    renderPage()
    await screen.findByRole('heading', { name: 'Asset AST-000001' })

    fireEvent.click(screen.getByRole('button', { name: 'Retire…' }))
    const dialog = within(await screen.findByRole('dialog'))
    fireEvent.change(dialog.getByLabelText(/Reason for retiring/), { target: { value: 'End of life' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Retire asset' }))

    expect(await screen.findByText('Retired assets are final. Read-only.')).toBeTruthy()
    expect(retireAsset).toHaveBeenCalledWith('AST-000001', 'End of life')
    expect(screen.getByTestId('asset-retire-reason').textContent).toContain('End of life')
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
  })

  it('history notes: each edited field with old and new value', () => {
    expect(historyNote({
      action: 'asset.updated',
      before: { location: 'Bangalore Floor 2', serial_number: 'DL-1O01', warranty_expiry: null },
      after: { location: 'Chennai', serial_number: 'DL-1001', warranty_expiry: '2030-01-31' },
    })).toBe('Location: Bangalore Floor 2 → Chennai; Serial number: DL-1O01 → DL-1001; Warranty expiry: (empty) → 31 Jan 2030')
    expect(historyNote({ action: 'asset.retired', before: { status: 'available' }, after: { status: 'retired', reason: 'End of life' } }))
      .toBe('Reason: End of life')
  })
})
