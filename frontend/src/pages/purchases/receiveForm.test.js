// Tests for the receiving form logic (Slice 3.2): starting values, unit rows that
// follow the received quantity, copy-down, checks (incl. duplicate serials), the
// request body and the success message. Run with: npm test
import { describe, expect, it } from 'vitest'

import {
  bulkLineNumbers,
  copyFirstUnitToAll,
  receiptValuesFromPurchase,
  receivedMessage,
  setReceivedQuantity,
  toReceivePayload,
  totalUnits,
  validateReceipt,
} from './receiveForm'

const TODAY = '2026-11-13'
const PURCHASE = {
  id: 5,
  purchase_number: 'PUR-000005',
  purchase_date: '2026-11-10',
  lines: [
    { id: 11, line_type: 'serialized', category: { name: 'Laptops' }, description: 'Dell Latitude 5440', quantity: 3 },
    { id: 12, line_type: 'serialized', category: { name: 'Monitors' }, description: 'Dell P2422H', quantity: 1 },
  ],
}

function filled() {
  const values = receiptValuesFromPurchase(PURCHASE, TODAY)
  values.lines[0].units = values.lines[0].units.map((u, i) => ({ ...u, serial_number: `SN-${i + 1}`, model: 'Latitude' }))
  values.lines[1].units = values.lines[1].units.map((u) => ({ ...u, serial_number: 'MON-1', model: 'P2422H' }))
  return values
}

const check = (values) => validateReceipt(values, { purchaseDate: PURCHASE.purchase_date, today: TODAY })

describe('receiptValuesFromPurchase', () => {
  it('starts with today, every line received in full and one empty row per unit', () => {
    const values = receiptValuesFromPurchase(PURCHASE, TODAY)
    expect(values.received_date).toBe(TODAY)
    expect(values.lines.map((l) => [l.line_id, l.number, l.ordered, l.received_quantity, l.units.length])).toEqual([
      [11, 1, 3, '3', 3],
      [12, 2, 1, '1', 1],
    ])
    expect(values.lines[0].units[0]).toMatchObject({ serial_number: '', model: '', name: '' })
    expect(totalUnits(values)).toBe(4)
  })

  it('finds by-quantity lines (received in Slice 3.3)', () => {
    expect(bulkLineNumbers(PURCHASE)).toEqual([])
    expect(bulkLineNumbers({ lines: [...PURCHASE.lines, { id: 13, line_type: 'bulk' }] })).toEqual([3])
  })
})

describe('setReceivedQuantity', () => {
  it('keeps typed rows, removes extra rows and adds empty ones', () => {
    const line = filled().lines[0]
    const fewer = setReceivedQuantity(line, '2')
    expect(fewer.units.map((u) => u.serial_number)).toEqual(['SN-1', 'SN-2'])
    const back = setReceivedQuantity(fewer, '3')
    expect(back.units.map((u) => u.serial_number)).toEqual(['SN-1', 'SN-2', ''])
    expect(setReceivedQuantity(line, '0').units).toEqual([])
  })

  it('leaves the rows alone while the quantity is not valid', () => {
    const line = filled().lines[0]
    for (const bad of ['', 'abc', '-1', '4', '1.5']) {
      const changed = setReceivedQuantity(line, bad)
      expect(changed.received_quantity).toBe(bad)
      expect(changed.units).toHaveLength(3)
    }
  })
})

describe('copyFirstUnitToAll', () => {
  it('copies model, brand, warranty and location but never the serial number or name', () => {
    const line = receiptValuesFromPurchase(PURCHASE, TODAY).lines[0]
    line.units[0] = { ...line.units[0], serial_number: 'A', name: 'Mine', model: 'Latitude', brand: 'Dell', warranty_expiry: '2029-01-01', location: 'Store' }
    line.units[1] = { ...line.units[1], serial_number: 'B' }
    const copied = copyFirstUnitToAll(line)
    expect(copied.units[1]).toMatchObject({ serial_number: 'B', name: '', model: 'Latitude', brand: 'Dell', warranty_expiry: '2029-01-01', location: 'Store' })
    expect(copied.units[2]).toMatchObject({ serial_number: '', model: 'Latitude' })
  })
})

describe('validateReceipt', () => {
  it('accepts a complete receipt', () => {
    expect(check(filled())).toEqual({})
  })

  it('needs a serial number and model on every unit', () => {
    const values = filled()
    values.lines[0].units[1] = { ...values.lines[0].units[1], serial_number: '  ', model: '' }
    const errors = check(values)
    expect(errors.lines[0].units[1]).toEqual({ serial_number: 'Enter the serial number.', model: 'Enter the model.' })
    expect(errors.lines[0].units[0]).toEqual({})
  })

  it('marks every copy of a serial number entered twice, ignoring case and spaces', () => {
    const values = filled()
    values.lines[1].units[0].serial_number = '  sn-1 '
    const errors = check(values)
    const message = 'This serial number is entered twice in this receipt.'
    expect(errors.lines[0].units[0].serial_number).toBe(message)
    expect(errors.lines[1].units[0].serial_number).toBe(message)
    expect(errors.lines[0].units[1]).toEqual({})
  })

  it('checks the received quantity: whole number from 0 to ordered', () => {
    const values = filled()
    values.lines[0].received_quantity = '4'
    values.lines[1].received_quantity = ''
    const errors = check(values)
    expect(errors.lines[0].received_quantity).toBe('Only 3 ordered. More than ordered is not allowed.')
    expect(errors.lines[1].received_quantity).toBe('Enter how many arrived (0 if none).')
  })

  it('needs at least one unit in the whole receipt', () => {
    const values = filled()
    values.lines = values.lines.map((l) => setReceivedQuantity(l, '0'))
    expect(check(values)).toEqual({ form: 'Nothing was received. At least one unit must arrive.' })
  })

  it('allows 0 on one line when another line arrives', () => {
    const values = filled()
    values.lines[0] = setReceivedQuantity(values.lines[0], '0')
    expect(check(values)).toEqual({})
  })

  it('checks the received date against the purchase date and today', () => {
    const values = filled()
    expect(check({ ...values, received_date: '' }).received_date).toBe('Enter the received date.')
    expect(check({ ...values, received_date: '2026-11-14' }).received_date).toBe('The received date cannot be in the future.')
    expect(check({ ...values, received_date: '2026-11-09' }).received_date).toBe('The received date cannot be before the purchase date.')
    expect(check({ ...values, received_date: '2026-11-10' })).toEqual({})
  })

  it('checks the length of the optional text fields', () => {
    const values = filled()
    values.lines[0].units[0].brand = 'x'.repeat(101)
    values.lines[0].units[0].location = 'y'.repeat(201)
    const errors = check(values)
    expect(errors.lines[0].units[0]).toEqual({
      brand: 'Use at most 100 characters.',
      location: 'Use at most 200 characters.',
    })
  })
})

describe('toReceivePayload', () => {
  it('trims text, sends empty optional fields as null and numbers as numbers', () => {
    const values = filled()
    values.lines[0] = setReceivedQuantity(values.lines[0], '2')
    values.lines[0].units[0] = { ...values.lines[0].units[0], serial_number: ' SN-1 ', model: ' Latitude ', brand: ' Dell ', name: '  ', warranty_expiry: '2029-11-30' }
    expect(toReceivePayload(values)).toEqual({
      received_date: TODAY,
      lines: [
        {
          line_id: 11,
          received_quantity: 2,
          units: [
            { serial_number: 'SN-1', model: 'Latitude', name: null, brand: 'Dell', warranty_expiry: '2029-11-30', location: null },
            { serial_number: 'SN-2', model: 'Latitude', name: null, brand: null, warranty_expiry: null, location: null },
          ],
        },
        {
          line_id: 12,
          received_quantity: 1,
          units: [{ serial_number: 'MON-1', model: 'P2422H', name: null, brand: null, warranty_expiry: null, location: null }],
        },
      ],
    })
  })
})

describe('receivedMessage', () => {
  const received = (count) => ({
    purchase_number: 'PUR-000005',
    lines: [{ assets: Array.from({ length: count }, (_, i) => ({ asset_code: `AST-${String(i + 1).padStart(6, '0')}` })) }],
  })

  it('lists the new asset IDs', () => {
    expect(receivedMessage(received(3))).toBe('PUR-000005 received: 3 assets created (AST-000001, AST-000002, AST-000003).')
    expect(receivedMessage(received(1))).toBe('PUR-000005 received: 1 asset created (AST-000001).')
  })

  it('shortens a long list', () => {
    expect(receivedMessage(received(12), 2)).toBe('PUR-000005 received: 12 assets created (AST-000001, AST-000002 and 10 more).')
  })
})
