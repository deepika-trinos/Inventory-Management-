// Form logic for receiving a purchase of one-by-one items (Slice 3.2), kept apart
// from the screen so it can be tested on its own. The SERVER repeats every check.
//
// One step for the whole purchase (B55): the received date, and for every line the
// received quantity (0 to ordered, P4) with one row per unit received. Each row
// becomes an asset: serial number and model required; name (defaults to the line's
// description, B57), brand, warranty expiry and location (typed, Q1) optional (P5).

export const SERIAL_MAX = 100
export const MODEL_MAX = 100
export const NAME_MAX = 200
export const BRAND_MAX = 100
export const LOCATION_MAX = 200
export const MAX_UNITS_PER_RECEIPT = 1000 // B61

// Fields copied by "Copy unit 1 to all units" (never the serial number or the name).
export const COPYABLE_FIELDS = ['model', 'brand', 'warranty_expiry', 'location']

let nextKey = 1
const newKey = () => `unit-${nextKey++}`

export function emptyUnit() {
  return { key: newKey(), serial_number: '', model: '', name: '', brand: '', warranty_expiry: '', location: '' }
}

/** Does this purchase have by-quantity lines? Those are received in Slice 3.3 (B56). */
export function bulkLineNumbers(purchase) {
  return purchase.lines.flatMap((line, i) => (line.line_type === 'bulk' ? [i + 1] : []))
}

/** Starting values: received date today, every line received in full with empty unit rows. */
export function receiptValuesFromPurchase(purchase, today) {
  return {
    received_date: today,
    lines: purchase.lines.map((line, i) => ({
      line_id: line.id,
      number: i + 1,
      description: line.description ?? '',
      category: line.category?.name ?? '',
      ordered: line.quantity,
      received_quantity: String(line.quantity),
      units: Array.from({ length: line.quantity }, emptyUnit),
    })),
  }
}

const WHOLE_NUMBER = /^\d+$/

/** The received quantity as a number, or null while it is not a whole number from 0 to ordered. */
export function parseReceived(line) {
  const text = String(line.received_quantity ?? '').trim()
  if (!WHOLE_NUMBER.test(text)) return null
  const n = Number(text)
  return n <= line.ordered ? n : null
}

/** Change a line's received quantity. While it is valid, the unit rows follow it:
 *  rows already typed are kept, new empty rows are added, extra rows are removed. */
export function setReceivedQuantity(line, value) {
  const updated = { ...line, received_quantity: value }
  const n = parseReceived(updated)
  if (n === null) return updated
  const units = line.units.slice(0, n)
  while (units.length < n) units.push(emptyUnit())
  return { ...updated, units }
}

/** Copy unit 1's model, brand, warranty expiry and location to every other unit of the line. */
export function copyFirstUnitToAll(line) {
  if (line.units.length < 2) return line
  const [first, ...rest] = line.units
  const shared = Object.fromEntries(COPYABLE_FIELDS.map((f) => [f, first[f]]))
  return { ...line, units: [first, ...rest.map((u) => ({ ...u, ...shared }))] }
}

export function totalUnits(values) {
  return values.lines.reduce((sum, line) => sum + (parseReceived(line) ?? 0), 0)
}

function tooLong(value, max) {
  return value.trim().length > max ? `Use at most ${max} characters.` : ''
}

/** All problems in the form:
 *   { received_date, form, lines: [{ received_quantity, units: [{ field: message }] }] }
 *  An empty object means the receipt can be sent. */
export function validateReceipt(values, { purchaseDate, today }) {
  const errors = {}
  if (!values.received_date) errors.received_date = 'Enter the received date.'
  else if (values.received_date > today) errors.received_date = 'The received date cannot be in the future.'
  else if (values.received_date < purchaseDate) errors.received_date = 'The received date cannot be before the purchase date.'

  // Where each serial number was typed (lower case, trimmed), to spot duplicates in this receipt.
  const seen = new Map()
  values.lines.forEach((line, li) =>
    line.units.forEach((unit, ui) => {
      const key = unit.serial_number.trim().toLowerCase()
      if (key) seen.set(key, [...(seen.get(key) ?? []), [li, ui]])
    }),
  )
  const duplicated = new Set(
    [...seen.values()].filter((places) => places.length > 1).flat().map(([li, ui]) => `${li}:${ui}`),
  )

  let anyLineError = false
  const lineErrors = values.lines.map((line, li) => {
    const e = { units: [] }
    const text = String(line.received_quantity ?? '').trim()
    if (!text) e.received_quantity = 'Enter how many arrived (0 if none).'
    else if (!WHOLE_NUMBER.test(text)) e.received_quantity = 'Use a whole number, 0 or more.'
    else if (Number(text) > line.ordered) e.received_quantity = `Only ${line.ordered} ordered. More than ordered is not allowed.`

    e.units = line.units.map((unit, ui) => {
      const u = {}
      if (!unit.serial_number.trim()) u.serial_number = 'Enter the serial number.'
      else if (duplicated.has(`${li}:${ui}`)) u.serial_number = 'This serial number is entered twice in this receipt.'
      else if (tooLong(unit.serial_number, SERIAL_MAX)) u.serial_number = tooLong(unit.serial_number, SERIAL_MAX)
      if (!unit.model.trim()) u.model = 'Enter the model.'
      else if (tooLong(unit.model, MODEL_MAX)) u.model = tooLong(unit.model, MODEL_MAX)
      for (const [field, max] of [['name', NAME_MAX], ['brand', BRAND_MAX], ['location', LOCATION_MAX]]) {
        const problem = tooLong(unit[field], max)
        if (problem) u[field] = problem
      }
      return u
    })
    if (e.received_quantity || e.units.some((u) => Object.keys(u).length)) anyLineError = true
    return e
  })
  if (anyLineError) errors.lines = lineErrors

  const total = totalUnits(values)
  if (!errors.lines && total === 0) errors.form = 'Nothing was received. At least one unit must arrive.'
  if (total > MAX_UNITS_PER_RECEIPT) errors.form = `One receipt can create at most ${MAX_UNITS_PER_RECEIPT} assets.`
  return errors
}

const orNull = (value) => value.trim() || null

/** The request body for POST /purchases/{id}/receive. */
export function toReceivePayload(values) {
  return {
    received_date: values.received_date,
    lines: values.lines.map((line) => ({
      line_id: line.line_id,
      received_quantity: Number(String(line.received_quantity).trim()),
      units: line.units.map((unit) => ({
        serial_number: unit.serial_number.trim(),
        model: unit.model.trim(),
        name: orNull(unit.name),
        brand: orNull(unit.brand),
        warranty_expiry: unit.warranty_expiry || null,
        location: orNull(unit.location),
      })),
    })),
  }
}

/** The new asset IDs of a received purchase, in order. */
export function receivedAssetCodes(purchase) {
  return purchase.lines.flatMap((line) => (line.assets ?? []).map((a) => a.asset_code))
}

/** "PUR-000001 received: 3 assets created (AST-000001, AST-000002, AST-000003)." */
export function receivedMessage(purchase, shown = 10) {
  const codes = receivedAssetCodes(purchase)
  const listed = codes.slice(0, shown).join(', ')
  const more = codes.length > shown ? ` and ${codes.length - shown} more` : ''
  const noun = codes.length === 1 ? 'asset' : 'assets'
  return `${purchase.purchase_number} received: ${codes.length} ${noun} created (${listed}${more}).`
}
