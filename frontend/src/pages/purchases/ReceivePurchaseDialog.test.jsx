// Tests for the Receive purchase screen (Slices 3.2-3.3): one row per unit, validation
// per row (missing and duplicate serials), the confirm box, what is sent, server
// errors on the right row, by-quantity lines (stock now / after, deactivated item),
// and purchases that cannot be received.
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getPurchase, receivePurchase } from '../../api/purchases'
import { todayInCompanyTimezone } from '../../utils/dates'
import ReceivePurchaseDialog from './ReceivePurchaseDialog'

vi.mock('../../api/purchases', async (importOriginal) => ({
  ...(await importOriginal()),
  getPurchase: vi.fn(),
  receivePurchase: vi.fn(),
}))

const TODAY = todayInCompanyTimezone()
const DRAFT = {
  id: 5,
  purchase_number: 'PUR-000005',
  status: 'draft',
  purchase_date: TODAY,
  reference_number: 'INV-1',
  vendor: { id: 1, name: 'Acme IT Supplies', status: 'active' },
  lines: [
    { id: 11, line_type: 'serialized', category: { id: 3, name: 'Laptops' }, description: 'Dell Latitude 5440', quantity: 2, unit_cost: '85000.00', assets: [] },
  ],
}

const MOUSE = { id: 7, name: 'USB mouse', unit_of_measure: 'pieces', status: 'active', quantity_on_hand: 15 }
const MIXED = {
  ...DRAFT,
  lines: [...DRAFT.lines, { id: 12, line_type: 'bulk', stock_item: MOUSE, quantity: 10, unit_cost: '450.00', assets: [] }],
}

beforeEach(() => {
  vi.clearAllMocks()
  getPurchase.mockResolvedValue(DRAFT)
})

function renderDialog() {
  const onReceived = vi.fn()
  render(<ReceivePurchaseDialog open purchaseId={5} onClose={vi.fn()} onReceived={onReceived} />)
  return { onReceived }
}

const cell = (line, unit, label) => screen.getByLabelText(`Line ${line} unit ${unit} ${label}`)
const type = (element, value) => fireEvent.change(element, { target: { value } })

function fillUnit(unit, serial, model = 'Latitude 5440') {
  type(cell(1, unit, 'serial number'), serial)
  type(cell(1, unit, 'model'), model)
}

describe('ReceivePurchaseDialog', () => {
  it('shows one row per ordered unit and the received date (today)', async () => {
    renderDialog()
    expect(await screen.findByText('Line 1: Dell Latitude 5440')).toBeTruthy()
    expect(screen.getByLabelText(/Received date/).value).toBe(TODAY)
    expect(screen.getByLabelText(/Received quantity/).value).toBe('2')
    expect(within(screen.getByRole('table', { name: 'Units for line 1' })).getAllByRole('row')).toHaveLength(3) // header + 2
    expect(screen.getByTestId('receive-count').textContent).toBe('2 assets will be created')
  })

  it('adds and removes unit rows when the received quantity changes', async () => {
    renderDialog()
    await screen.findByText('Line 1: Dell Latitude 5440')
    fillUnit(1, 'SN-1')

    type(screen.getByLabelText(/Received quantity/), '1')

    expect(screen.queryByLabelText('Line 1 unit 2 serial number')).toBeNull()
    expect(cell(1, 1, 'serial number').value).toBe('SN-1')
    expect(screen.getByTestId('receive-count').textContent).toBe('1 asset will be created')
  })

  it('marks missing serial numbers and models per row and sends nothing', async () => {
    renderDialog()
    await screen.findByText('Line 1: Dell Latitude 5440')
    fillUnit(1, 'SN-1')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))

    expect(await screen.findByText('Please fix the highlighted fields.')).toBeTruthy()
    expect(screen.getByText('Enter the serial number.')).toBeTruthy()
    expect(screen.getByText('Enter the model.')).toBeTruthy()
    expect(screen.queryByRole('dialog', { name: /Receive PUR-000005\?/ })).toBeNull()
    expect(receivePurchase).not.toHaveBeenCalled()
  })

  it('marks a serial number typed twice in the form', async () => {
    renderDialog()
    await screen.findByText('Line 1: Dell Latitude 5440')
    fillUnit(1, 'SN-1')
    fillUnit(2, 'sn-1')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))

    expect(await screen.findAllByText('This serial number is entered twice in this receipt.')).toHaveLength(2)
    expect(receivePurchase).not.toHaveBeenCalled()
  })

  it('asks for confirmation, then sends the receipt and reports the new assets', async () => {
    const received = {
      ...DRAFT,
      status: 'received',
      lines: [{ ...DRAFT.lines[0], received_quantity: 2, assets: [{ id: 1, asset_code: 'AST-000001' }, { id: 2, asset_code: 'AST-000002' }] }],
    }
    receivePurchase.mockResolvedValue(received)
    const { onReceived } = renderDialog()
    await screen.findByText('Line 1: Dell Latitude 5440')
    fillUnit(1, ' SN-1 ')
    type(cell(1, 1, 'brand'), 'Dell')
    fillUnit(2, 'SN-2')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))
    const confirm = await screen.findByRole('dialog', { name: 'Receive PUR-000005?' })
    expect(within(confirm).getByText(/This creates 2 assets/)).toBeTruthy()
    expect(receivePurchase).not.toHaveBeenCalled() // nothing is sent before confirming
    fireEvent.click(within(confirm).getByRole('button', { name: 'Receive' }))

    await waitFor(() => expect(onReceived).toHaveBeenCalledWith(received))
    expect(receivePurchase).toHaveBeenCalledWith(5, {
      received_date: TODAY,
      lines: [
        {
          line_id: 11,
          received_quantity: 2,
          units: [
            { serial_number: 'SN-1', model: 'Latitude 5440', name: null, brand: 'Dell', warranty_expiry: null, location: null },
            { serial_number: 'SN-2', model: 'Latitude 5440', name: null, brand: null, warranty_expiry: null, location: null },
          ],
        },
      ],
    })
  })

  it('warns in the confirm box when a line is received short', async () => {
    renderDialog()
    await screen.findByText('Line 1: Dell Latitude 5440')
    type(screen.getByLabelText(/Received quantity/), '1')
    fillUnit(1, 'SN-1')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))

    const confirm = await screen.findByRole('dialog', { name: 'Receive PUR-000005?' })
    expect(within(confirm).getByText(/fewer units than ordered are closed/)).toBeTruthy()
  })

  it('shows a serial number already used by another asset on its row', async () => {
    receivePurchase.mockRejectedValue({
      response: {
        status: 409,
        data: { error: { code: 'serial_number_taken', message: 'Line 1, unit 2: Serial number "SN-2" is already used by another asset.', details: { line: 1, unit: 2 } } },
      },
    })
    const { onReceived } = renderDialog()
    await screen.findByText('Line 1: Dell Latitude 5440')
    fillUnit(1, 'SN-1')
    fillUnit(2, 'SN-2')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: 'Receive PUR-000005?' })).getByRole('button', { name: 'Receive' }))

    expect(await screen.findByText(/Serial number "SN-2" is already used by another asset/)).toBeTruthy()
    expect(screen.getByText('Please fix the highlighted fields. Nothing was saved.')).toBeTruthy()
    expect(cell(1, 2, 'serial number').getAttribute('aria-invalid')).toBe('true')
    expect(cell(1, 1, 'serial number').getAttribute('aria-invalid')).toBe('false')
    expect(onReceived).not.toHaveBeenCalled()
  })

  it('receives a mixed purchase: laptops as assets, mice as stock', async () => {
    getPurchase.mockResolvedValue(MIXED)
    const received = { ...MIXED, status: 'received' }
    receivePurchase.mockResolvedValue(received)
    const { onReceived } = renderDialog()
    expect(await screen.findByText('Line 2: USB mouse')).toBeTruthy()
    expect(screen.getByText('By quantity · Ordered: 10 pieces')).toBeTruthy()
    expect(screen.getByTestId('stock-preview-2').textContent).toBe('In stock now: 15 pieces · after receiving: 25 pieces')
    expect(screen.queryByRole('table', { name: 'Units for line 2' })).toBeNull() // no unit rows
    expect(screen.getByTestId('receive-count').textContent).toBe('2 assets will be created · stock added on 1 line')

    const mouseQuantity = within(screen.getByRole('group', { name: 'Line 2' })).getByLabelText(/Received quantity/)
    type(mouseQuantity, '7')
    expect(screen.getByTestId('stock-preview-2').textContent).toBe('In stock now: 15 pieces · after receiving: 22 pieces')
    fillUnit(1, 'SN-1')
    fillUnit(2, 'SN-2')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))
    const confirm = await screen.findByRole('dialog', { name: 'Receive PUR-000005?' })
    expect(within(confirm).getByText(/creates 2 assets.*adds the received quantities to stock on 1 by-quantity line/)).toBeTruthy()
    fireEvent.click(within(confirm).getByRole('button', { name: 'Receive' }))

    await waitFor(() => expect(onReceived).toHaveBeenCalledWith(received))
    expect(receivePurchase.mock.calls[0][1].lines[1]).toEqual({ line_id: 12, received_quantity: 7, units: [] })
  })

  it('receives a purchase of by-quantity lines only', async () => {
    getPurchase.mockResolvedValue({ ...MIXED, lines: [MIXED.lines[1]] })
    receivePurchase.mockResolvedValue({ ...MIXED, status: 'received' })
    renderDialog()
    await screen.findByText('Line 1: USB mouse')
    expect(screen.getByTestId('receive-count').textContent).toBe('stock added on 1 line')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))
    const confirm = await screen.findByRole('dialog', { name: 'Receive PUR-000005?' })
    expect(within(confirm).getByText(/^This adds the received quantities to stock on 1 by-quantity line, and marks/)).toBeTruthy()
  })

  it('blocks stock for a deactivated stock item until 0 is entered', async () => {
    getPurchase.mockResolvedValue({
      ...MIXED,
      lines: [MIXED.lines[0], { ...MIXED.lines[1], stock_item: { ...MOUSE, status: 'inactive' } }],
    })
    renderDialog()
    await screen.findByText('Line 2: USB mouse')
    expect(screen.getByText(/This stock item is deactivated, so stock cannot be added to it/)).toBeTruthy()
    fillUnit(1, 'SN-1')
    fillUnit(2, 'SN-2')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))
    expect(await screen.findByText('Please fix the highlighted fields.')).toBeTruthy()
    expect(receivePurchase).not.toHaveBeenCalled()

    type(within(screen.getByRole('group', { name: 'Line 2' })).getByLabelText(/Received quantity/), '0')
    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))
    expect(await screen.findByRole('dialog', { name: 'Receive PUR-000005?' })).toBeTruthy()
  })

  it('shows a server "stock item deactivated" error on its line', async () => {
    getPurchase.mockResolvedValue(MIXED)
    receivePurchase.mockRejectedValue({
      response: { data: { error: { code: 'stock_item_inactive', message: 'Line 2: stock item "USB mouse" is deactivated.', details: { line: 2 } } } },
    })
    renderDialog()
    await screen.findByText('Line 2: USB mouse')
    fillUnit(1, 'SN-1')
    fillUnit(2, 'SN-2')
    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))
    const confirm = await screen.findByRole('dialog', { name: 'Receive PUR-000005?' })
    fireEvent.click(within(confirm).getByRole('button', { name: 'Receive' }))

    expect(await screen.findByText(/is deactivated\. Nothing was saved\./)).toBeTruthy()
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Receive PUR-000005?' })).toBeNull())
    const quantity = within(screen.getByRole('group', { name: 'Line 2' })).getByLabelText(/Received quantity/)
    expect(quantity.getAttribute('aria-invalid')).toBe('true')
  })

  it('marks a warranty expiry before the purchase date (B61)', async () => {
    getPurchase.mockResolvedValue({ ...DRAFT, purchase_date: '2026-01-10' })
    renderDialog()
    await screen.findByText('Line 1: Dell Latitude 5440')
    fillUnit(1, 'SN-1')
    fillUnit(2, 'SN-2')
    type(cell(1, 2, 'warranty expiry'), '2026-01-09')

    fireEvent.click(screen.getByRole('button', { name: 'Receive…' }))

    expect(await screen.findByText('Cannot be before the purchase date.')).toBeTruthy()
    expect(cell(1, 2, 'warranty expiry').getAttribute('aria-invalid')).toBe('true')
    expect(receivePurchase).not.toHaveBeenCalled()
  })

  it('does not offer receiving for a purchase that is not a draft', async () => {
    getPurchase.mockResolvedValue({ ...DRAFT, status: 'cancelled' })
    renderDialog()

    expect(await screen.findByText(/Only a draft purchase can be received/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Receive…' })).toBeNull()
  })
})
