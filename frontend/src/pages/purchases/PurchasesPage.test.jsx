// Tests for the Purchases list's empty and error messages (D9 extended to Purchases at
// Phase 3 sign-off, decision D10): an empty result caused by filters says "No matches"
// (not "No purchases yet") and can clear the filters; a truly empty list keeps "No
// purchases yet"; a "from" date after the "to" date is explained without "Try again";
// other errors keep "Try again". The server is replaced by stand-ins. Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listPurchases } from '../../api/purchases'
import { listVendors } from '../../api/vendors'
import { NotificationProvider } from '../../context/NotificationContext'
import PurchasesPage from './PurchasesPage'

vi.mock('../../api/purchases', async (importOriginal) => ({ ...(await importOriginal()), listPurchases: vi.fn() }))
vi.mock('../../api/vendors', async (importOriginal) => ({ ...(await importOriginal()), listVendors: vi.fn() }))

const page = (items) => ({ items, total: items.length, page: 1, page_size: 20 })
const T = '2026-11-20T05:00:00Z'
const ACME = { id: 1, name: 'Acme IT Supplies', status: 'active' }
const DRAFT = {
  id: 1, purchase_number: 'PUR-000001', status: 'draft', vendor: ACME, reference_number: 'INV-2026-0042',
  purchase_date: '2026-11-20', received_date: null, line_count: 2, total_amount: '259500.00', created_at: T, updated_at: T,
}
const serverError = (code, message, status = 422) => ({ response: { status, data: { error: { code, message } } } })

beforeEach(() => {
  vi.clearAllMocks()
  listVendors.mockResolvedValue(page([ACME]))
  // Stand-in server: one draft; the Received filter matches nothing.
  listPurchases.mockImplementation(({ status }) => Promise.resolve(page(!status || status === 'draft' ? [DRAFT] : [])))
})

function renderPage() {
  render(
    <NotificationProvider>
      <MemoryRouter>
        <PurchasesPage />
      </MemoryRouter>
    </NotificationProvider>,
  )
}

function choose(label, option) {
  fireEvent.mouseDown(screen.getByRole('combobox', { name: label }))
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: option }))
}

describe('PurchasesPage empty and error messages', () => {
  it('an empty result caused by a filter says "No matches" and can clear the filters', async () => {
    renderPage()
    await screen.findByText('PUR-000001')

    choose(/Status/, 'Received')

    expect(await screen.findByText('No matches')).toBeTruthy()
    expect(screen.getByText('Nothing matches the selected filters.')).toBeTruthy()
    expect(screen.queryByText('No purchases yet')).toBeNull()

    fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' }).at(-1)) // the one in the message
    expect(await screen.findByText('PUR-000001')).toBeTruthy()
    expect(listPurchases.mock.calls.at(-1)[0]).toMatchObject({ status: '', vendorId: '', dateFrom: '', dateTo: '' })
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('a truly empty list keeps "No purchases yet"', async () => {
    listPurchases.mockResolvedValue(page([]))
    renderPage()
    expect(await screen.findByText('No purchases yet')).toBeTruthy()
    expect(screen.queryByText('No matches')).toBeNull()
  })

  it('"from" after "to": the field is red and the message has no "Try again"', async () => {
    listPurchases.mockImplementation(({ dateFrom, dateTo }) =>
      dateFrom && dateTo && dateFrom > dateTo
        ? Promise.reject(serverError('invalid_date_range', "The 'from' date must be on or before the 'to' date."))
        : Promise.resolve(page([DRAFT])),
    )
    renderPage()
    await screen.findByText('PUR-000001')

    fireEvent.change(screen.getByLabelText('Purchase date from'), { target: { value: '2026-11-21' } })
    fireEvent.change(screen.getByLabelText('to'), { target: { value: '2026-11-20' } })

    expect(await screen.findByText("The 'from' date must be on or before the 'to' date.")).toBeTruthy()
    expect(screen.getByText('Must be on or after the “from” date.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /try again/i })).toBeNull()
  })

  it('other errors still offer "Try again"', async () => {
    listPurchases.mockRejectedValueOnce(serverError('internal_error', 'Something went wrong.', 500))
    renderPage()

    const retry = await screen.findByRole('button', { name: /try again/i })
    fireEvent.click(retry)

    await waitFor(() => expect(screen.getByText('PUR-000001')).toBeTruthy())
  })
})
