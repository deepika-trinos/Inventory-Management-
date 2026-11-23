// Tests for the Issue and Adjust forms and their confirm boxes (Slice 4.4; owner's answers
// A4, A5, A4-5a): screen checks (whole number, not more than on hand, reason required, no
// future date, Add / Remove chosen); the confirm box shows the balance now and after; what
// is sent; server problems shown under the right field. The server is replaced by stand-ins.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listEmployees } from '../../api/employees'
import { adjustStock, enterOpeningStock, issueStock } from '../../api/stockItems'
import StockChangeDialog, { stockChange, validateStockChange } from './StockChangeDialog'

vi.mock('../../api/stockItems', async (importOriginal) => ({
  ...(await importOriginal()),
  issueStock: vi.fn(),
  adjustStock: vi.fn(),
  enterOpeningStock: vi.fn(),
}))
vi.mock('../../api/employees', async (importOriginal) => ({ ...(await importOriginal()), listEmployees: vi.fn() }))

const ITEM = { id: 7, name: 'USB mouse', unit_of_measure: 'pieces', quantity_on_hand: 25, reorder_threshold: 5, status: 'active' }
const ASHA = { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar', status: 'active' }
const TODAY = '2026-11-23'

let onSaved
beforeEach(() => {
  vi.clearAllMocks()
  onSaved = vi.fn()
  listEmployees.mockResolvedValue({ items: [ASHA], total: 1, page: 1, page_size: 20 })
})

function renderDialog(mode, item = ITEM) {
  render(<StockChangeDialog open mode={mode} item={item} onClose={vi.fn()} onSaved={onSaved} />)
}

const form = () => within(screen.getByRole('dialog'))
const fill = (label, value) => fireEvent.change(form().getByLabelText(label), { target: { value } })

describe('StockChangeDialog: Issue', () => {
  it('shows the balance now and after while typing', () => {
    renderDialog('issue')
    expect(screen.getByTestId('stock-change-on-hand').textContent).toBe('On hand now: 25 pieces')
    fill(/^Quantity/, '5')
    expect(screen.getByTestId('stock-change-on-hand').textContent).toBe('On hand now: 25 pieces · after: 20 pieces')
  })

  it('refuses more than is in stock, an empty reason and a future date before asking the server', async () => {
    renderDialog('issue')
    fill(/^Quantity/, '26')
    fill(/^Date/, '2999-01-01')
    fireEvent.click(form().getByRole('button', { name: 'Issue…' }))

    expect(await screen.findByText('Only 25 in stock.')).toBeTruthy()
    expect(screen.getByText('Please enter the reason.')).toBeTruthy()
    expect(screen.getByText('The date cannot be in the future.')).toBeTruthy()
    expect(issueStock).not.toHaveBeenCalled()
  })

  it('asks to confirm with the new balance, then sends the issue without an employee', async () => {
    issueStock.mockResolvedValue({ item: { ...ITEM, quantity_on_hand: 22 }, movement: { quantity: 3, movement_type: 'issue', direction: 'out' } })
    renderDialog('issue')
    fill(/^Quantity/, '3')
    fill(/^Reason/, '  Training room 2  ')
    fireEvent.click(form().getByRole('button', { name: 'Issue…' }))

    const confirm = within(await screen.findByRole('dialog', { name: 'Issue 3 pieces of USB mouse?' }))
    expect(confirm.getByText('On hand now: 25 pieces · after: 22 pieces.')).toBeTruthy()
    expect(confirm.getByText(/Reason: Training room 2/)).toBeTruthy()
    fireEvent.click(confirm.getByRole('button', { name: 'Issue' }))

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(issueStock).toHaveBeenCalledWith(7, { quantity: 3, reason: 'Training room 2', movementDate: expect.any(String), employeeId: undefined })
  })

  it('can name an active employee, shown in the confirm box', async () => {
    issueStock.mockResolvedValue({ item: ITEM, movement: { quantity: 1, movement_type: 'issue', direction: 'out' } })
    renderDialog('issue')
    fill(/^Quantity/, '1')
    fill(/^Reason/, 'Replacement mouse')
    const picker = form().getByRole('combobox', { name: /Issued to/ })
    fireEvent.change(picker, { target: { value: 'asha' } })
    fireEvent.click(await screen.findByRole('option', { name: 'EMP-001 · Asha Kumar' }))
    expect(listEmployees.mock.calls.at(-1)[0]).toMatchObject({ status: 'active', hasLogin: undefined })

    fireEvent.click(form().getByRole('button', { name: 'Issue…' }))
    const confirm = within(await screen.findByRole('dialog', { name: /Issue 1 pieces/ }))
    expect(confirm.getByText('Issued to EMP-001 · Asha Kumar.')).toBeTruthy()
    fireEvent.click(confirm.getByRole('button', { name: 'Issue' }))

    await waitFor(() => expect(issueStock).toHaveBeenCalledWith(7, expect.objectContaining({ employeeId: 3 })))
  })

  it('a server refusal goes back to the form with the message under the field', async () => {
    issueStock.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'insufficient_stock', message: 'Only 2 pieces of "USB mouse" in stock (3 requested).' } } },
    })
    renderDialog('issue')
    fill(/^Quantity/, '3')
    fill(/^Reason/, 'Kits')
    fireEvent.click(form().getByRole('button', { name: 'Issue…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Issue 3/ })).getByRole('button', { name: 'Issue' }))

    expect(await screen.findByText('Only 2 pieces of "USB mouse" in stock (3 requested).')).toBeTruthy()
    expect(await screen.findByRole('button', { name: 'Issue…' })).toBeTruthy() // back on the form
    expect(onSaved).not.toHaveBeenCalled()
  })
})

describe('StockChangeDialog: Adjust', () => {
  it('needs Add or Remove to be chosen', async () => {
    renderDialog('adjust')
    fill(/^Quantity/, '2')
    fill(/^Reason/, 'Count')
    fireEvent.click(form().getByRole('button', { name: 'Adjust…' }))
    expect(await screen.findByText('Choose Add or Remove.')).toBeTruthy()
    expect(adjustStock).not.toHaveBeenCalled()
  })

  it('Add shows the higher balance and sends direction add', async () => {
    adjustStock.mockResolvedValue({ item: { ...ITEM, quantity_on_hand: 27 }, movement: { quantity: 2, movement_type: 'adjustment_in', direction: 'in' } })
    renderDialog('adjust')
    fireEvent.click(form().getByRole('radio', { name: /^Add/ }))
    fill(/^Quantity/, '2')
    fill(/^Reason/, 'Found two in the store room')
    fireEvent.click(form().getByRole('button', { name: 'Adjust…' }))

    const confirm = within(await screen.findByRole('dialog', { name: 'Add 2 pieces to USB mouse?' }))
    expect(confirm.getByText('On hand now: 25 pieces · after: 27 pieces.')).toBeTruthy()
    fireEvent.click(confirm.getByRole('button', { name: 'Add' }))

    await waitFor(() => expect(adjustStock).toHaveBeenCalledWith(7, expect.objectContaining({ direction: 'add', quantity: 2, reason: 'Found two in the store room' })))
  })

  it('Remove cannot take more than is in stock', async () => {
    renderDialog('adjust')
    fireEvent.click(form().getByRole('radio', { name: /^Remove/ }))
    fill(/^Quantity/, '30')
    fill(/^Reason/, 'Broken')
    fireEvent.click(form().getByRole('button', { name: 'Adjust…' }))
    expect(await screen.findByText('Only 25 in stock.')).toBeTruthy()
  })

  it('Remove of everything is allowed (exactly 0)', async () => {
    renderDialog('adjust')
    fireEvent.click(form().getByRole('radio', { name: /^Remove/ }))
    fill(/^Quantity/, '25')
    fill(/^Reason/, 'Store flooded')
    fireEvent.click(form().getByRole('button', { name: 'Adjust…' }))
    const confirm = within(await screen.findByRole('dialog', { name: 'Remove 25 pieces from USB mouse?' }))
    expect(confirm.getByText('On hand now: 25 pieces · after: 0 pieces.')).toBeTruthy()
  })
})

describe('validation helpers', () => {
  it('quantity must be a whole number from 1', () => {
    const base = { mode: 'issue', direction: 'remove', reason: 'x', movementDate: TODAY }
    for (const bad of ['', '0', '-1', '1.5', 'two']) {
      expect(validateStockChange({ ...base, quantity: bad }, 25, TODAY).quantity).toBe('Enter a whole number, 1 or more.')
    }
    expect(validateStockChange({ ...base, quantity: '1' }, 0, TODAY).quantity).toBe('Nothing is in stock.')
    expect(validateStockChange({ ...base, quantity: '25' }, 25, TODAY)).toEqual({})
  })

  it('reason up to 500 characters; earlier dates allowed', () => {
    const base = { mode: 'adjust', direction: 'add', quantity: '1', movementDate: '2026-11-01' }
    expect(validateStockChange({ ...base, reason: 'r'.repeat(501) }, 0, TODAY).reason).toBe('Use at most 500 characters.')
    expect(validateStockChange({ ...base, reason: 'r'.repeat(500) }, 0, TODAY)).toEqual({})
  })

  it('stockChange signs', () => {
    expect(stockChange('issue', 'remove', 3)).toBe(-3)
    expect(stockChange('adjust', 'add', 3)).toBe(3)
    expect(stockChange('adjust', 'remove', 3)).toBe(-3)
  })
})

// Slice 4.5 (INV-01; owner's answer A6): opening stock, once, with a confirm box 0 -> N.
describe('StockChangeDialog: Opening stock', () => {
  const CABLE = { ...ITEM, id: 8, name: 'HDMI cable', quantity_on_hand: 0 }

  it('the note is optional; the confirm box shows 0 → N', async () => {
    enterOpeningStock.mockResolvedValue({ item: { ...CABLE, quantity_on_hand: 40 }, movement: { quantity: 40, movement_type: 'opening', direction: 'in' } })
    renderDialog('opening', CABLE)
    expect(form().getByLabelText(/^Note/)).toBeTruthy()
    expect(form().queryByRole('radio')).toBeNull()
    fill(/^Quantity/, '40')
    fireEvent.click(form().getByRole('button', { name: 'Continue…' }))

    const confirm = within(await screen.findByRole('dialog', { name: 'Enter opening stock of 40 pieces for HDMI cable?' }))
    expect(confirm.getByText('On hand: 0 → 40 pieces.')).toBeTruthy()
    fireEvent.click(confirm.getByRole('button', { name: 'Enter opening stock' }))

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(enterOpeningStock).toHaveBeenCalledWith(8, { quantity: 40, note: '', movementDate: expect.any(String) })
  })

  it('sends a typed note and refuses a future date or a bad quantity first', async () => {
    renderDialog('opening', CABLE)
    fill(/^Quantity/, '0')
    fill(/^Date/, '2999-01-01')
    fireEvent.click(form().getByRole('button', { name: 'Continue…' }))
    expect(await screen.findByText('Enter a whole number, 1 or more.')).toBeTruthy()
    expect(screen.getByText('The date cannot be in the future.')).toBeTruthy()
    expect(enterOpeningStock).not.toHaveBeenCalled()
  })

  it('a refusal (already has movements) is shown on the form', async () => {
    enterOpeningStock.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'opening_stock_not_allowed', message: 'Stock item "HDMI cable" already has stock movements.' } } },
    })
    renderDialog('opening', CABLE)
    fill(/^Quantity/, '5')
    fill(/^Note/, ' First count ')
    fireEvent.click(form().getByRole('button', { name: 'Continue…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Enter opening stock of 5/ })).getByRole('button', { name: 'Enter opening stock' }))

    expect(await screen.findByText('Stock item "HDMI cable" already has stock movements.')).toBeTruthy()
    expect(enterOpeningStock).toHaveBeenCalledWith(8, expect.objectContaining({ note: 'First count' }))
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('validation: the note is not required for opening stock', () => {
    expect(validateStockChange({ mode: 'opening', direction: 'add', quantity: '3', reason: '', movementDate: TODAY }, 0, TODAY)).toEqual({})
  })
})
