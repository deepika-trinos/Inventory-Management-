// Tests for the purchase form logic (Slice 3.1): required fields, at least one line,
// totals and line-type switching. Run with: npm test
import { describe, expect, it } from 'vitest'

import { formatPaise, toPaise } from '../../utils/money'
import {
  emptyLine,
  emptyValues,
  grandTotalPaise,
  lineTotalPaise,
  switchLineType,
  toPayload,
  validatePurchase,
  valuesFromPurchase,
} from './purchaseForm'

const TODAY = '2026-11-12'

function filledValues() {
  return {
    vendor_id: 1,
    reference_number: ' INV-1 ',
    purchase_date: TODAY,
    notes: '',
    lines: [
      { ...emptyLine('serialized'), category_id: 3, description: 'Laptops: Dell Latitude 5440', quantity: '3', unit_cost: '85000' },
      { ...emptyLine('bulk'), stock_item_id: 7, quantity: '10', unit_cost: '450.00' },
    ],
  }
}

describe('required fields', () => {
  it('a new form starts with today, one one-by-one line and nothing else filled', () => {
    const values = emptyValues(TODAY)
    expect(values.purchase_date).toBe(TODAY)
    expect(values.lines).toHaveLength(1)
    expect(values.lines[0].line_type).toBe('serialized')
  })

  it('reports every missing field of an empty form', () => {
    const errors = validatePurchase({ ...emptyValues(TODAY), purchase_date: '' }, TODAY)
    expect(errors.vendor_id).toBeTruthy()
    expect(errors.reference_number).toBeTruthy()
    expect(errors.purchase_date).toBeTruthy()
    expect(errors.lines[0]).toEqual({
      category_id: 'Choose a category.',
      description: expect.any(String),
      unit_cost: 'Enter the unit cost (0 is allowed).',
    })
  })

  it('a complete form has no errors', () => {
    expect(validatePurchase(filledValues(), TODAY)).toEqual({})
  })

  it('a blank reference (only spaces) is missing', () => {
    expect(validatePurchase({ ...filledValues(), reference_number: '   ' }, TODAY).reference_number).toBeTruthy()
  })

  it('a future date is refused; today and earlier are fine', () => {
    expect(validatePurchase({ ...filledValues(), purchase_date: '2026-11-13' }, TODAY).purchase_date).toMatch(/future/)
    expect(validatePurchase({ ...filledValues(), purchase_date: '2025-01-31' }, TODAY)).toEqual({})
  })

  it('a by-quantity line needs a stock item; a one-by-one line a category and a description', () => {
    const bulk = validatePurchase({ ...filledValues(), lines: [{ ...emptyLine('bulk'), quantity: '1', unit_cost: '1' }] }, TODAY)
    expect(bulk.lines[0]).toEqual({ stock_item_id: 'Choose a stock item.' })
    const serialized = validatePurchase(
      { ...filledValues(), lines: [{ ...emptyLine('serialized'), category_id: 3, description: '  ', quantity: '1', unit_cost: '1' }] },
      TODAY,
    )
    expect(Object.keys(serialized.lines[0])).toEqual(['description'])
  })

  it.each([
    ['0', 'quantity'],
    ['-2', 'quantity'],
    ['1.5', 'quantity'],
    ['', 'quantity'],
    ['100001', 'quantity'],
  ])('quantity %j is refused', (quantity, field) => {
    const values = filledValues()
    values.lines[1].quantity = quantity
    expect(validatePurchase(values, TODAY).lines[1]).toHaveProperty(field)
  })

  it.each(['-1', '12.345', 'abc', '1,000'])('unit cost %j is refused', (cost) => {
    const values = filledValues()
    values.lines[1].unit_cost = cost
    expect(validatePurchase(values, TODAY).lines[1]).toHaveProperty('unit_cost')
  })

  it('a unit cost of 0 is allowed', () => {
    const values = filledValues()
    values.lines[1].unit_cost = '0'
    expect(validatePurchase(values, TODAY)).toEqual({})
  })
})

describe('at least one line', () => {
  it('a purchase with no lines cannot be sent', () => {
    expect(validatePurchase({ ...filledValues(), lines: [] }, TODAY).linesError).toBe('Add at least one line.')
  })
})

describe('totals', () => {
  it('line total = quantity x unit cost, in paise', () => {
    expect(lineTotalPaise({ quantity: '3', unit_cost: '85000' })).toBe(25500000)
    expect(lineTotalPaise({ quantity: '10', unit_cost: '450.5' })).toBe(450500)
  })

  it('has no floating point errors', () => {
    expect(lineTotalPaise({ quantity: '3', unit_cost: '0.10' })).toBe(30)
    expect(grandTotalPaise([{ quantity: '1', unit_cost: '0.1' }, { quantity: '1', unit_cost: '0.2' }])).toBe(30)
  })

  it('an incomplete line counts as nothing in the grand total', () => {
    const lines = [{ quantity: '3', unit_cost: '85000' }, { quantity: '10', unit_cost: '' }, { quantity: 'x', unit_cost: '5' }]
    expect(lineTotalPaise(lines[1])).toBeNull()
    expect(grandTotalPaise(lines)).toBe(25500000)
  })

  it('grand total for 3 laptops and 10 mice', () => {
    expect(formatPaise(grandTotalPaise(filledValues().lines))).toBe('₹2,59,500.00')
  })

  it('amounts are read exactly', () => {
    expect(toPaise('1250.5')).toBe(125050)
    expect(toPaise('0')).toBe(0)
    expect(toPaise('-1')).toBeNull()
  })
})

describe('line-type switching', () => {
  it('switching clears the item fields but keeps quantity and unit cost', () => {
    const line = { ...emptyLine('serialized'), category_id: 3, description: 'Laptops: Dell', quantity: '4', unit_cost: '100' }
    const switched = switchLineType(line, 'bulk')
    expect(switched).toMatchObject({ line_type: 'bulk', stock_item_id: '', category_id: '', description: '', quantity: '4', unit_cost: '100' })
    expect(switched.key).toBe(line.key)
  })

  it('choosing the same type changes nothing', () => {
    const line = { ...emptyLine('bulk'), stock_item_id: 7 }
    expect(switchLineType(line, 'bulk')).toBe(line)
  })
})

describe('request body', () => {
  it('sends only the fields of each line type, trimmed, and never any totals', () => {
    expect(toPayload(filledValues())).toEqual({
      vendor_id: 1,
      reference_number: 'INV-1',
      purchase_date: TODAY,
      notes: null,
      lines: [
        { line_type: 'serialized', category_id: 3, description: 'Laptops: Dell Latitude 5440', quantity: 3, unit_cost: '85000' },
        { line_type: 'bulk', stock_item_id: 7, quantity: 10, unit_cost: '450.00' },
      ],
    })
  })

  it('reads an existing purchase back into the form', () => {
    const values = valuesFromPurchase({
      vendor: { id: 2 },
      reference_number: 'R',
      purchase_date: '2026-01-02',
      notes: null,
      lines: [{ line_type: 'bulk', stock_item: { id: 7 }, category: null, description: null, quantity: 5, unit_cost: '1.50' }],
    })
    expect(values).toMatchObject({ vendor_id: 2, notes: '', lines: [{ stock_item_id: 7, category_id: '', quantity: '5', unit_cost: '1.50' }] })
  })
})
