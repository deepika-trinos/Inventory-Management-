// Tests for the purchase form screen (Slice 3.1): required fields, at least one line,
// totals shown as you type, line-type switching, what is sent, server errors and
// read-only purchases. The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listCategories } from '../../api/categories'
import { createPurchase, getPurchase } from '../../api/purchases'
import { listStockItems } from '../../api/stockItems'
import { listVendors } from '../../api/vendors'
import { todayInCompanyTimezone } from '../../utils/dates'
import PurchaseFormDialog from './PurchaseFormDialog'

vi.mock('../../api/vendors', () => ({ listVendors: vi.fn() }))
vi.mock('../../api/categories', () => ({ listCategories: vi.fn() }))
vi.mock('../../api/stockItems', async (importOriginal) => ({ ...(await importOriginal()), listStockItems: vi.fn() }))
vi.mock('../../api/purchases', async (importOriginal) => ({
  ...(await importOriginal()),
  createPurchase: vi.fn(),
  updatePurchase: vi.fn(),
  getPurchase: vi.fn(),
}))

const page = (items) => ({ items, total: items.length, page: 1, page_size: 100 })
const ACME = { id: 1, name: 'Acme IT Supplies', status: 'active' }
const LAPTOPS = { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' }
const MOUSE = { id: 7, name: 'USB mouse', unit_of_measure: 'pieces', status: 'active' }

beforeEach(() => {
  vi.clearAllMocks()
  listVendors.mockResolvedValue(page([ACME]))
  listCategories.mockResolvedValue(page([LAPTOPS]))
  listStockItems.mockResolvedValue(page([MOUSE]))
})

function renderForm(props = {}) {
  const onSaved = vi.fn()
  render(<PurchaseFormDialog open onClose={vi.fn()} onSaved={onSaved} {...props} />)
  return { onSaved }
}

const line = (n) => screen.getByRole('group', { name: `Line ${n}` })

// MUI drop-down lists open on mouse-down, then an option is clicked.
function choose(container, label, option) {
  fireEvent.mouseDown(within(container).getByRole('combobox', { name: label }))
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: option }))
}

function type(element, value) {
  fireEvent.change(element, { target: { value } })
}

async function waitForLists() {
  await waitFor(() => expect(screen.getByRole('combobox', { name: /Vendor/ }).getAttribute('aria-disabled')).toBeNull())
}

async function fillHeader() {
  await waitForLists()
  choose(document.body, /Vendor/, 'Acme IT Supplies')
  type(screen.getByRole('textbox', { name: /Invoice/ }), 'INV-2026-0042')
}

describe('PurchaseFormDialog', () => {
  it('shows the required fields and sends nothing while they are empty', async () => {
    renderForm()
    await waitForLists()

    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))

    expect(await screen.findByText('Please fix the highlighted fields.')).toBeTruthy()
    expect(screen.getByText('Choose a vendor.')).toBeTruthy()
    expect(screen.getByText('Enter the invoice / reference number.')).toBeTruthy()
    expect(within(line(1)).getByText('Choose a category.')).toBeTruthy()
    expect(within(line(1)).getByText('Enter the unit cost (0 is allowed).')).toBeTruthy()
    expect(createPurchase).not.toHaveBeenCalled()
  })

  it('starts with today as the purchase date and does not allow a later one', async () => {
    renderForm()
    const date = screen.getByLabelText(/Purchase date/)
    expect(date.value).toBe(todayInCompanyTimezone())
    expect(date.getAttribute('max')).toBe(todayInCompanyTimezone())
  })

  it('always keeps at least one line: the only line cannot be removed', async () => {
    renderForm()
    await waitForLists()
    expect(screen.queryByRole('button', { name: 'Remove line 1' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Add line' }))
    expect(screen.getAllByRole('group', { name: /^Line \d$/ })).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Remove line 2' }))

    expect(screen.getAllByRole('group', { name: /^Line \d$/ })).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Remove line 1' })).toBeNull()
  })

  it('shows line totals and the grand total as you type', async () => {
    renderForm()
    await waitForLists()
    expect(screen.getByTestId('purchase-grand-total').textContent).toBe('Total: ₹0.00')

    type(within(line(1)).getByRole('spinbutton', { name: /Quantity/ }), '3')
    type(within(line(1)).getByRole('textbox', { name: /Unit cost/ }), '85000')
    fireEvent.click(screen.getByRole('button', { name: 'Add line' }))
    choose(line(2), /Type/, 'By quantity')
    type(within(line(2)).getByRole('spinbutton', { name: /Quantity/ }), '10')
    type(within(line(2)).getByRole('textbox', { name: /Unit cost/ }), '450.50')

    expect(screen.getByTestId('line-total-1').textContent).toBe('₹2,55,000.00')
    expect(screen.getByTestId('line-total-2').textContent).toBe('₹4,505.00')
    expect(screen.getByTestId('purchase-grand-total').textContent).toBe('Total: ₹2,59,505.00')

    type(within(line(2)).getByRole('textbox', { name: /Unit cost/ }), '')
    expect(screen.getByTestId('line-total-2').textContent).toBe('—')
    expect(screen.getByTestId('purchase-grand-total').textContent).toBe('Total: ₹2,55,000.00')
  })

  it('switches a line between one-by-one and by quantity', async () => {
    renderForm()
    await waitForLists()
    const first = line(1)
    expect(within(first).getByRole('combobox', { name: /Category/ })).toBeTruthy()
    expect(within(first).getByRole('textbox', { name: /Description/ })).toBeTruthy()
    type(within(first).getByRole('spinbutton', { name: /Quantity/ }), '4')

    choose(first, /Type/, 'By quantity')

    expect(within(first).getByRole('combobox', { name: /Stock item/ })).toBeTruthy()
    expect(within(first).queryByRole('combobox', { name: /Category/ })).toBeNull()
    expect(within(first).queryByRole('textbox', { name: /Description/ })).toBeNull()
    expect(within(first).getByRole('spinbutton', { name: /Quantity/ }).value).toBe('4') // kept

    choose(first, /Type/, 'One-by-one')
    expect(within(first).getByRole('textbox', { name: /Description/ }).value).toBe('') // cleared
  })

  it('saves a draft with laptops and mice, sending no totals', async () => {
    createPurchase.mockResolvedValue({ id: 1, purchase_number: 'PUR-000001' })
    const { onSaved } = renderForm()
    await fillHeader()
    choose(line(1), /Category/, 'Laptops')
    type(within(line(1)).getByRole('textbox', { name: /Description/ }), 'Laptops: Dell Latitude 5440')
    type(within(line(1)).getByRole('spinbutton', { name: /Quantity/ }), '3')
    type(within(line(1)).getByRole('textbox', { name: /Unit cost/ }), '85000')
    fireEvent.click(screen.getByRole('button', { name: 'Add line' }))
    choose(line(2), /Type/, 'By quantity')
    choose(line(2), /Stock item/, 'USB mouse')
    type(within(line(2)).getByRole('spinbutton', { name: /Quantity/ }), '10')
    type(within(line(2)).getByRole('textbox', { name: /Unit cost/ }), '0')

    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith({ id: 1, purchase_number: 'PUR-000001' }, true))
    expect(createPurchase).toHaveBeenCalledWith({
      vendor_id: 1,
      reference_number: 'INV-2026-0042',
      purchase_date: todayInCompanyTimezone(),
      notes: null,
      lines: [
        { line_type: 'serialized', category_id: 3, description: 'Laptops: Dell Latitude 5440', quantity: 3, unit_cost: '85000' },
        { line_type: 'bulk', stock_item_id: 7, quantity: 10, unit_cost: '0' },
      ],
    })
  })

  it('shows a server error on the line it belongs to', async () => {
    createPurchase.mockRejectedValue({
      response: {
        status: 409,
        data: { error: { code: 'stock_item_inactive', message: 'Line 1: Stock item "USB mouse" is deactivated.', details: { line: 1 } } },
      },
    })
    renderForm()
    await fillHeader()
    choose(line(1), /Type/, 'By quantity')
    choose(line(1), /Stock item/, 'USB mouse')
    type(within(line(1)).getByRole('textbox', { name: /Unit cost/ }), '10')

    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))

    expect(await within(line(1)).findByText('Line 1: Stock item "USB mouse" is deactivated.')).toBeTruthy()
  })

  it('opens a cancelled purchase read-only', async () => {
    getPurchase.mockResolvedValue({
      id: 9,
      purchase_number: 'PUR-000009',
      status: 'cancelled',
      vendor: ACME,
      reference_number: 'OLD-1',
      purchase_date: '2026-01-05',
      notes: null,
      lines: [{ id: 1, line_type: 'bulk', stock_item: MOUSE, category: null, description: null, quantity: 2, unit_cost: '100.00' }],
    })
    renderForm({ purchaseId: 9 })

    expect(await screen.findByText(/is cancelled and can no longer be changed/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Save/ })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Add line' })).toBeNull()
    expect(screen.getByRole('textbox', { name: /Invoice/ })).toHaveProperty('disabled', true)
    expect(screen.getByTestId('purchase-grand-total').textContent).toBe('Total: ₹200.00')
  })
})
