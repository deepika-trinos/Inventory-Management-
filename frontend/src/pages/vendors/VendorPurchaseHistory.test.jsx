// Tests for a vendor's purchase history (Slice 3.4, VEN-04): what is asked from the
// server, the row fields, empty and error states, and that a row opens the purchase.
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listPurchases } from '../../api/purchases'
import VendorPurchaseHistory from './VendorPurchaseHistory'

vi.mock('../../api/purchases', async (importOriginal) => ({ ...(await importOriginal()), listPurchases: vi.fn() }))

const VENDOR = { id: 4, name: 'Acme IT Supplies', status: 'inactive' }
const RECEIVED = {
  id: 9,
  purchase_number: 'PUR-000009',
  vendor: VENDOR,
  reference_number: 'INV-2026-0042',
  purchase_date: '2026-11-10',
  received_date: '2026-11-12',
  status: 'received',
  line_count: 2,
  total_amount: '259500.00',
}
const DRAFT = { ...RECEIVED, id: 8, purchase_number: 'PUR-000008', reference_number: 'INV-7', received_date: null, status: 'draft', line_count: 1, total_amount: '450.00' }
const page = (items) => ({ items, total: items.length, page: 1, page_size: 10 })

beforeEach(() => {
  vi.clearAllMocks()
  listPurchases.mockResolvedValue(page([RECEIVED, DRAFT]))
})

function renderHistory() {
  render(
    <MemoryRouter initialEntries={['/vendors/4']}>
      <Routes>
        <Route path="/vendors/:vendorId" element={<VendorPurchaseHistory vendorId={4} />} />
        <Route path="/purchases/:purchaseId" element={<p>Purchase detail page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

const rowFor = (number) => screen.getByText(number).closest('tr')

describe('VendorPurchaseHistory', () => {
  it("asks for this vendor's purchases, newest purchase date first", async () => {
    renderHistory()
    await screen.findByText('PUR-000009')
    expect(listPurchases).toHaveBeenCalledWith(expect.objectContaining({ vendorId: 4, sort: '-purchase_date', page: 1 }))
    expect(screen.getByRole('heading', { name: 'Purchase history' })).toBeTruthy()
  })

  it('shows reference, dates, lines, total and status for each purchase', async () => {
    renderHistory()
    const row = within(rowFor(await screen.findByText('PUR-000009').then(() => 'PUR-000009')))
    expect(row.getByText('INV-2026-0042')).toBeTruthy()
    expect(row.getByText('10 Nov 2026')).toBeTruthy()
    expect(row.getByText('12 Nov 2026')).toBeTruthy()
    expect(row.getByText('₹2,59,500.00')).toBeTruthy()
    expect(row.getByText('Received')).toBeTruthy()
    const draft = within(rowFor('PUR-000008'))
    expect(draft.getByText('Draft')).toBeTruthy()
    expect(draft.getByText('—')).toBeTruthy() // not received yet
    // The vendor column is left out on the vendor's own page.
    expect(screen.queryByRole('button', { name: 'Vendor' })).toBeNull()
  })

  it('opens the purchase detail page when a row is clicked', async () => {
    renderHistory()
    fireEvent.click(rowFor(await screen.findByText('PUR-000009').then(() => 'PUR-000009')))
    expect(await screen.findByText('Purchase detail page')).toBeTruthy()
  })

  it('opens the purchase with the keyboard too', async () => {
    renderHistory()
    await screen.findByText('PUR-000009')
    fireEvent.keyDown(screen.getByLabelText('Open PUR-000008'), { key: 'Enter' })
    expect(await screen.findByText('Purchase detail page')).toBeTruthy()
  })

  it('says so when the vendor has no purchases', async () => {
    listPurchases.mockResolvedValue(page([]))
    renderHistory()
    expect(await screen.findByText('No purchases from this vendor yet')).toBeTruthy()
  })

  it('shows an error with "Try again", which asks again', async () => {
    listPurchases.mockRejectedValueOnce({ request: {}, code: 'ERR_NETWORK' })
    renderHistory()
    expect(await screen.findByText(/Cannot reach the server/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(await screen.findByText('PUR-000009')).toBeTruthy()
    await waitFor(() => expect(listPurchases).toHaveBeenCalledTimes(2))
  })
})
