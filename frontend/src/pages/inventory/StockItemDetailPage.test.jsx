// Tests for the stock item page /inventory/:itemId (Slice 4.3, INV-02, INV-05, INV-06):
// details with quantity on hand, threshold and the low-stock badge; the movement history
// (type, signed change, balance after, date, reference link, reason, who / when); the
// empty history; Edit / Deactivate buttons; not-found and error states.
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getStockItem, getStockMovements } from '../../api/stockItems'
import { NotificationProvider } from '../../context/NotificationContext'
import StockItemDetailPage, { signedQuantity } from './StockItemDetailPage'

vi.mock('../../api/stockItems', async (importOriginal) => ({
  ...(await importOriginal()),
  getStockItem: vi.fn(),
  getStockMovements: vi.fn(),
  setStockItemActive: vi.fn(),
}))

const USER = { id: 2, email: 'manager@example.com' }
const ITEM = {
  id: 7, name: 'USB mouse', category: { id: 2, name: 'Peripherals', tracking_type: 'bulk', status: 'active' },
  unit_of_measure: 'pieces', reorder_threshold: 5, quantity_on_hand: 3, low_stock: true, status: 'active',
  created_at: '2026-11-12T05:00:00Z', updated_at: '2026-11-22T06:30:00Z',
}
const RECEIPT = {
  id: 11, movement_type: 'receipt', direction: 'in', quantity: 10, change: 10, balance_after: 13,
  movement_date: '2026-11-20', created_at: '2026-11-21T06:30:00Z', created_by: USER, reason: null,
  reference: { purchase_id: 9, purchase_number: 'PUR-000009', purchase_line_id: 21 },
}
const ADJUST = {
  id: 12, movement_type: 'adjustment_out', direction: 'out', quantity: 10, change: -10, balance_after: 3,
  movement_date: '2026-11-22', created_at: '2026-11-22T06:30:00Z', created_by: USER, reason: 'Damaged in storage', reference: null,
}
const history = (items) => ({ items, total: items.length, page: 1, page_size: 20 })

beforeEach(() => {
  vi.clearAllMocks()
  getStockItem.mockResolvedValue(ITEM)
  getStockMovements.mockResolvedValue(history([ADJUST, RECEIPT]))
})

function renderPage(path = '/inventory/7') {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/inventory/:itemId" element={<StockItemDetailPage />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

const section = (name) => within(screen.getByRole('region', { name }))

describe('StockItemDetailPage', () => {
  it('loads the item from the address and shows its balance, threshold and low-stock badge', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: 'USB mouse' })).toBeTruthy()
    expect(getStockItem).toHaveBeenCalledWith('7')
    expect(screen.getAllByText('Low stock').length).toBeGreaterThan(0)
    expect(screen.getByTestId('stock-on-hand').textContent).toContain('3 pieces')
    expect(screen.getByTestId('stock-threshold').textContent).toContain('5 pieces')
    expect(screen.getByTestId('stock-level').textContent).toContain('at or below the reorder threshold')
    expect(screen.getByRole('button', { name: 'Edit' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Deactivate' })).toBeTruthy()
  })

  it('an item above its threshold has no low-stock badge', async () => {
    getStockItem.mockResolvedValue({ ...ITEM, quantity_on_hand: 30, low_stock: false })
    renderPage()
    await screen.findByRole('heading', { name: 'USB mouse' })
    expect(screen.queryByText('Low stock')).toBeNull()
    expect(screen.getByTestId('stock-level').textContent).toContain('Above the reorder threshold')
  })

  it('shows the movement history newest first with all details', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'USB mouse' })
    const hist = section('Movement history')
    const rows = (await hist.findAllByRole('row')).slice(1)

    expect(getStockMovements).toHaveBeenCalledWith(7, expect.objectContaining({ page: 1 }))
    const first = within(rows[0])
    expect(first.getByText('Adjustment out')).toBeTruthy()
    expect(first.getByText('−10 pieces')).toBeTruthy()
    expect(first.getByText('3 pieces')).toBeTruthy()
    expect(first.getByText('Damaged in storage')).toBeTruthy()
    const second = within(rows[1])
    expect(second.getByText('Receipt')).toBeTruthy()
    expect(second.getByText('+10 pieces')).toBeTruthy()
    expect(second.getByText('20 Nov 2026')).toBeTruthy()
    expect(second.getByRole('link', { name: 'PUR-000009' }).getAttribute('href')).toBe('/purchases/9')
    expect(second.getByText(/manager@example\.com/)).toBeTruthy()
  })

  it('an item without movements says so', async () => {
    getStockMovements.mockResolvedValue(history([]))
    renderPage()
    await screen.findByRole('heading', { name: 'USB mouse' })
    expect(await section('Movement history').findByText('No stock movements yet')).toBeTruthy()
  })

  it('an inactive item shows Activate', async () => {
    getStockItem.mockResolvedValue({ ...ITEM, status: 'inactive', quantity_on_hand: 0, low_stock: false })
    renderPage()
    await screen.findByRole('heading', { name: 'USB mouse' })
    expect(screen.getByRole('button', { name: 'Activate' })).toBeTruthy()
    expect(screen.getByTestId('stock-level').textContent).toContain('Inactive')
  })

  it('an unknown item shows "Stock item not found" with a link back', async () => {
    getStockItem.mockRejectedValue({ response: { status: 404, data: { error: { code: 'stock_item_not_found', message: 'Stock item not found.' } } } })
    renderPage('/inventory/999')
    expect(await screen.findByText('Stock item not found')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'All stock items' }).getAttribute('href')).toBe('/inventory')
  })

  it('a server error offers Try again', async () => {
    getStockItem.mockRejectedValue({ response: { status: 500, data: { error: { code: 'internal_error', message: 'Something went wrong.' } } } })
    renderPage()
    expect(await screen.findByRole('button', { name: /try again/i })).toBeTruthy()
  })

  it('signed quantities', () => {
    expect(signedQuantity({ direction: 'in', quantity: 4 }, 'boxes')).toBe('+4 boxes')
    expect(signedQuantity({ direction: 'out', quantity: 1 }, 'pieces')).toBe('−1 pieces')
  })

  // ---- Slice 4.4 ------------------------------------------------------------------------
  it('an active item shows Issue… and Adjust…', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'USB mouse' })
    expect(screen.getByRole('button', { name: 'Issue…' }).disabled).toBe(false)
    expect(screen.getByRole('button', { name: 'Adjust…' }).disabled).toBe(false)
  })

  it('an inactive item cannot be issued or adjusted', async () => {
    getStockItem.mockResolvedValue({ ...ITEM, status: 'inactive', quantity_on_hand: 0, low_stock: false })
    renderPage()
    await screen.findByRole('heading', { name: 'USB mouse' })
    expect(screen.getByRole('button', { name: 'Issue…' }).disabled).toBe(true)
    expect(screen.getByRole('button', { name: 'Adjust…' }).disabled).toBe(true)
  })

  it('an issue to an employee shows who received it in the history', async () => {
    getStockMovements.mockResolvedValue(history([{
      ...ADJUST, id: 13, movement_type: 'issue', reason: 'Replacement mouse',
      issued_to: { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar' },
    }]))
    renderPage()
    await screen.findByRole('heading', { name: 'USB mouse' })
    expect(await section('Movement history').findByText('Issued to Asha Kumar (EMP-001)')).toBeTruthy()
    expect(section('Movement history').getByText('Issue')).toBeTruthy()
  })
})
