// Tests for the Receive purchase screen (Slice 3.2): one row per unit, validation
// per row (missing and duplicate serials), the confirm box, what is sent, server
// errors on the right row, and purchases that cannot be received.
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

  it('refuses a purchase with by-quantity lines until Slice 3.3', async () => {
    getPurchase.mockResolvedValue({
      ...DRAFT,
      lines: [...DRAFT.lines, { id: 12, line_type: 'bulk', stock_item: { id: 7, name: 'USB mouse' }, quantity: 10, assets: [] }],
    })
    renderDialog()

    expect(await screen.findByText(/Receiving by-quantity items arrives in Slice 3.3/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Receive…' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Close' })).toBeTruthy()
  })

  it('does not offer receiving for a purchase that is not a draft', async () => {
    getPurchase.mockResolvedValue({ ...DRAFT, status: 'cancelled' })
    renderDialog()

    expect(await screen.findByText(/Only a draft purchase can be received/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Receive…' })).toBeNull()
  })
})
