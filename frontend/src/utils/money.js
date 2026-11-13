// Money in Indian rupees (decision P2): INR only, 2 decimal places, no tax.
//
// Amounts are handled as whole PAISE (1 rupee = 100 paise) so adding them up
// never gives floating-point surprises like 0.1 + 0.2 = 0.30000000000000004.
// The server always recalculates totals; the screen only shows a preview.

const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 })

// "1250", "1250.5", "1250.50" are valid; "-1", "1.234", "abc" are not.
export const AMOUNT_PATTERN = /^\d{1,10}(\.\d{1,2})?$/

/** "1250.5" -> 125050 (paise), or null when it is not a valid amount. */
export function toPaise(value) {
  const text = String(value ?? '').trim()
  if (!AMOUNT_PATTERN.test(text)) return null
  const [rupees, fraction = ''] = text.split('.')
  return Number(rupees) * 100 + Number(fraction.padEnd(2, '0'))
}

/** 125050 -> "₹1,250.50" (Indian digit grouping). */
export function formatPaise(paise) {
  return inr.format((paise ?? 0) / 100)
}

/** "1250.50" (as the server sends it) -> "₹1,250.50". */
export function formatAmount(value) {
  const paise = toPaise(value)
  return paise === null ? '' : formatPaise(paise)
}
