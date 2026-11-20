// Tests for the purchase detail page /purchases/:id (Slice 3.4, PUR-09): vendor, lines,
// totals, assets created, stock movements, who created / received it; read-only for
// received and cancelled purchases; draft actions; loading, not-found and error states.
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getPurchase } from '../../api/purchases'
import { NotificationProvider } from '../../context/NotificationContext'
import PurchaseDetailPage from './PurchaseDetailPage'

vi.mock('../../api/purchases', async (importOriginal) => ({
  ...(await importOriginal()),
  getPurchase: vi.fn(),
  cancelPurchase: vi.fn(),
}))

const USER = { id: 2, email: 'manager@example.com' }
const MOUSE = { id: 7, name: 'USB mouse', unit_of_measure: 'pieces', status: 'active', quantity_on_hand: 35 }
const RECEIVED = {
  id: 9,
  purchase_number: 'PUR-000009',
  status: 'received',
  vendor: { id: 4, name: 'Acme IT Supplies', status: 'inactive', contact_person: 'Priya Nair', email: 'sales@acme.example.com', phone: null, address: null },
  reference_number: 'INV-2026-0042',
  purchase_date: '2026-11-10',
  received_date: '2026-11-12',
  notes: 'Q4 refresh',
  line_count: 2,
  total_amount: '174500.00',
  created_by: USER,
  created_at: '2026-11-10T05:00:00Z',
  received_by: { id: 3, email: 'admin@example.com' },
  received_at: '2026-11-12T06:30:00Z',
  updated_at: '2026-11-12T06:30:00Z',
  lines: [
    {
      id: 11, line_type: 'serialized', stock_item: null, category: { id: 3, name: 'Laptops' }, description: 'Laptops: Dell Latitude 5440',
      quantity: 3, unit_cost: '85000.00', line_total: '255000.00', received_quantity: 2,
      assets: [{ id: 1, asset_code: 'AST-000001', serial_number: 'SN-1' }, { id: 2, asset_code: 'AST-000002', serial_number: 'SN-2' }],
      stock_movements: [],
    },
    {
      id: 12, line_type: 'bulk', stock_item: MOUSE, category: null, description: null,
      quantity: 10, unit_cost: '450.00', line_total: '4500.00', received_quantity: 10, assets: [],
      stock_movements: [{ id: 5, movement_type: 'receipt', quantity: 10, balance_after: 35, movement_date: '2026-11-12', created_at: '2026-11-12T06:30:00Z', created_by: { id: 3, email: 'admin@example.com' } }],
    },
  ],
}
const NOT_RECEIVED = (status) => ({
  ...RECEIVED,
  status,
  received_date: null,
  received_by: null,
  received_at: null,
  lines: RECEIVED.lines.map((l) => ({ ...l, received_quantity: null, assets: [], stock_movements: [] })),
})

beforeEach(() => {
  vi.clearAllMocks()
  getPurchase.mockResolvedValue(RECEIVED)
})

function renderPage(path = '/purchases/9') {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/purchases/:purchaseId" element={<PurchaseDetailPage />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

const section = (name) => within(screen.getByRole('region', { name }))

describe('PurchaseDetailPage', () => {
  it('loads the purchase from the address', async () => {
    renderPage()
    expect(screen.getByText('Loading purchase…')).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'Purchase PUR-000009' })).toBeTruthy()
    expect(getPurchase).toHaveBeenCalledWith('9')
  })

  it('shows the vendor, the details and who created and received it', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'Purchase PUR-000009' })
    expect(screen.getByRole('link', { name: 'Acme IT Supplies' }).getAttribute('href')).toBe('/vendors/4')
    expect(screen.getByTestId('purchase-vendor').textContent).toContain('(inactive)')
    expect(screen.getByText('Priya Nair')).toBeTruthy()
    expect(screen.getByText('INV-2026-0042')).toBeTruthy()
    expect(screen.getByText('10 Nov 2026')).toBeTruthy()
    expect(screen.getByTestId('purchase-created-by').textContent).toContain('manager@example.com')
    expect(screen.getByTestId('purchase-received-by').textContent).toContain('admin@example.com')
    // The status badge sits next to the title.
    expect(screen.getByRole('heading', { name: 'Purchase PUR-000009' }).parentElement.textContent).toContain('Received')
  })

  it('lists every line with ordered and received quantities, unit cost, line total and the total', async () => {
    renderPage()
    const lines = await screen.findByRole('table', { name: 'Purchase lines' })
    const [laptops, mice] = within(lines).getAllByRole('row').slice(1, 3)
    expect(within(laptops).getByText('Laptops: Dell Latitude 5440')).toBeTruthy()
    expect(within(laptops).getByText('One-by-one · Laptops')).toBeTruthy()
    expect(within(laptops).getByText('3')).toBeTruthy()
    expect(within(laptops).getByText('2')).toBeTruthy()
    expect(within(laptops).getByText('₹85,000.00')).toBeTruthy()
    expect(within(mice).getByText('USB mouse')).toBeTruthy()
    expect(within(mice).getAllByText('10 pieces')).toHaveLength(2) // ordered and received
    expect(within(mice).getByText('₹4,500.00')).toBeTruthy()
    expect(screen.getByTestId('purchase-total').textContent).toBe('₹1,74,500.00')
  })

  it('shows the assets created and the stock movements written', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'Purchase PUR-000009' })
    const assets = section('Assets created')
    expect(assets.getByText('Assets created (2)')).toBeTruthy()
    expect(assets.getByRole('button', { name: 'AST-000001' })).toBeTruthy()
    expect(assets.getByText('SN-2')).toBeTruthy()
    const movements = section('Stock movements')
    expect(movements.getByText('Receipt')).toBeTruthy()
    expect(movements.getByText('+10 pieces')).toBeTruthy()
    expect(movements.getByText('35 pieces')).toBeTruthy()
    expect(movements.getByText(/admin@example.com/)).toBeTruthy()
  })

  it('is read-only for a received purchase', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'Purchase PUR-000009' })
    expect(screen.getByText(/Received purchases are final/)).toBeTruthy()
    for (const name of ['Edit', 'Receive…', 'Cancel purchase']) expect(screen.queryByRole('button', { name })).toBeNull()
  })

  it('is read-only for a cancelled purchase and shows no assets or movements', async () => {
    getPurchase.mockResolvedValue(NOT_RECEIVED('cancelled'))
    renderPage()
    await screen.findByRole('heading', { name: 'Purchase PUR-000009' })
    expect(screen.getByText(/Cancelled purchases are final/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
    expect(section('Assets created').getByText('A cancelled purchase never changes stock or creates assets.')).toBeTruthy()
    expect(section('Stock movements').getByText('No stock movements')).toBeTruthy()
    expect(screen.getByTestId('purchase-received-by').textContent).toContain('—')
  })

  it('offers edit, receive and cancel on a draft, and cancelling asks first', async () => {
    getPurchase.mockResolvedValue(NOT_RECEIVED('draft'))
    renderPage()
    await screen.findByRole('heading', { name: 'Purchase PUR-000009' })
    expect(screen.getByRole('button', { name: 'Edit' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Receive…' })).toBeTruthy()
    expect(section('Assets created').getByText('Assets are created when the purchase is received.')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Cancel purchase' }))

    expect(await screen.findByText('Cancel purchase PUR-000009?')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Keep draft' })).toBeTruthy()
  })

  it('says "Purchase not found" for an unknown id', async () => {
    getPurchase.mockRejectedValue({ response: { status: 404, data: { error: { code: 'purchase_not_found', message: 'Purchase not found.' } } } })
    renderPage('/purchases/999')
    expect(await screen.findByText('Purchase not found')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'All purchases' }).getAttribute('href')).toBe('/purchases')
  })

  it('shows other errors with "Try again", which loads again', async () => {
    getPurchase.mockRejectedValueOnce({ request: {}, code: 'ERR_NETWORK' })
    renderPage()
    expect(await screen.findByText(/Cannot reach the server/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(await screen.findByRole('heading', { name: 'Purchase PUR-000009' })).toBeTruthy()
  })
})
