// Form logic for the purchase form (Slice 3.1), kept apart from the screen so it
// can be tested on its own: empty values, line-type switching, checks, totals, and
// the request body. The SERVER repeats every check and calculates the real totals.
import { toPaise } from '../../utils/money'

export const REFERENCE_MAX = 100
export const NOTES_MAX = 2000
export const DESCRIPTION_MAX = 200
export const QUANTITY_MAX = 100000

// How each line type is shown (same words as the categories' tracking types).
export const LINE_TYPES = [
  { value: 'bulk', label: 'By quantity', hint: 'A stock item counted by quantity (e.g. mice).' },
  { value: 'serialized', label: 'One-by-one', hint: 'Becomes one asset per unit when received (e.g. laptops).' },
]

let nextKey = 1
const newKey = () => `line-${nextKey++}`

export function emptyLine(lineType = 'serialized') {
  return { key: newKey(), line_type: lineType, stock_item_id: '', category_id: '', description: '', quantity: '1', unit_cost: '' }
}

export function emptyValues(today) {
  return { vendor_id: '', reference_number: '', purchase_date: today, notes: '', lines: [emptyLine()] }
}

/** Form values for an existing purchase (as the server sends it). */
export function valuesFromPurchase(purchase) {
  return {
    vendor_id: purchase.vendor.id,
    reference_number: purchase.reference_number,
    purchase_date: purchase.purchase_date,
    notes: purchase.notes ?? '',
    lines: purchase.lines.map((line) => ({
      key: newKey(),
      line_type: line.line_type,
      stock_item_id: line.stock_item?.id ?? '',
      category_id: line.category?.id ?? '',
      description: line.description ?? '',
      quantity: String(line.quantity),
      unit_cost: String(line.unit_cost),
    })),
  }
}

/** Switch a line between "By quantity" and "One-by-one": the item fields are
 *  cleared (they belong to the other type); quantity and unit cost are kept. */
export function switchLineType(line, lineType) {
  if (line.line_type === lineType) return line
  return { ...line, line_type: lineType, stock_item_id: '', category_id: '', description: '' }
}

const WHOLE_NUMBER = /^\d+$/

/** quantity x unit cost in paise, or null while either is not valid yet. */
export function lineTotalPaise(line) {
  const quantity = String(line.quantity ?? '').trim()
  const cost = toPaise(line.unit_cost)
  if (!WHOLE_NUMBER.test(quantity) || cost === null) return null
  return Number(quantity) * cost
}

/** Sum of the valid line totals, in paise. */
export function grandTotalPaise(lines) {
  return lines.reduce((sum, line) => sum + (lineTotalPaise(line) ?? 0), 0)
}

function validateLine(line) {
  const errors = {}
  if (line.line_type === 'bulk') {
    if (!line.stock_item_id) errors.stock_item_id = 'Choose a stock item.'
  } else {
    if (!line.category_id) errors.category_id = 'Choose a category.'
    const description = line.description.trim()
    if (!description) errors.description = 'Describe the item, e.g. "Laptops: Dell Latitude 5440".'
    else if (description.length > DESCRIPTION_MAX) errors.description = `Use at most ${DESCRIPTION_MAX} characters.`
  }
  const quantity = String(line.quantity).trim()
  if (!quantity) errors.quantity = 'Enter a quantity.'
  else if (!WHOLE_NUMBER.test(quantity) || Number(quantity) < 1) errors.quantity = 'Use a whole number, 1 or more.'
  else if (Number(quantity) > QUANTITY_MAX) errors.quantity = `At most ${QUANTITY_MAX.toLocaleString('en-IN')}.`
  const cost = String(line.unit_cost).trim()
  if (!cost) errors.unit_cost = 'Enter the unit cost (0 is allowed).'
  else if (toPaise(cost) === null) errors.unit_cost = 'Use an amount of 0 or more with up to 2 decimals.'
  return errors
}

/** All problems in the form: { field: message, lines: [{ field: message }, ...], linesError }.
 *  An empty object means the form can be sent. */
export function validatePurchase(values, today) {
  const errors = {}
  if (!values.vendor_id) errors.vendor_id = 'Choose a vendor.'
  const reference = values.reference_number.trim()
  if (!reference) errors.reference_number = 'Enter the invoice / reference number.'
  else if (reference.length > REFERENCE_MAX) errors.reference_number = `Use at most ${REFERENCE_MAX} characters.`
  if (!values.purchase_date) errors.purchase_date = 'Enter the purchase date.'
  else if (values.purchase_date > today) errors.purchase_date = 'The purchase date cannot be in the future.'
  if (values.notes.length > NOTES_MAX) errors.notes = `Use at most ${NOTES_MAX} characters.`

  if (values.lines.length === 0) {
    errors.linesError = 'Add at least one line.'
  } else {
    const lineErrors = values.lines.map(validateLine)
    if (lineErrors.some((e) => Object.keys(e).length)) errors.lines = lineErrors
  }
  return errors
}

/** The request body for create / edit. Totals are never sent: the server calculates them. */
export function toPayload(values) {
  return {
    vendor_id: Number(values.vendor_id),
    reference_number: values.reference_number.trim(),
    purchase_date: values.purchase_date,
    notes: values.notes.trim() || null,
    lines: values.lines.map((line) =>
      line.line_type === 'bulk'
        ? {
            line_type: 'bulk',
            stock_item_id: Number(line.stock_item_id),
            quantity: Number(String(line.quantity).trim()),
            unit_cost: String(line.unit_cost).trim(),
          }
        : {
            line_type: 'serialized',
            category_id: Number(line.category_id),
            description: line.description.trim(),
            quantity: Number(String(line.quantity).trim()),
            unit_cost: String(line.unit_cost).trim(),
          },
    ),
  }
}
