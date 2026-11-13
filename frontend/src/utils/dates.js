// Show dates in the company timezone (decision Q11 / BR-14).
//
// The server always sends UTC times like "2026-11-11T04:30:00Z". These
// helpers convert them for display, e.g. "11 Nov 2026, 10:00 am" in Asia/Kolkata.
// Use them everywhere a date appears, so every screen shows the same format.
import { APP_TIMEZONE } from '../config'

const dateTimeFormat = new Intl.DateTimeFormat('en-IN', {
  timeZone: APP_TIMEZONE,
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

const dateFormat = new Intl.DateTimeFormat('en-IN', {
  timeZone: APP_TIMEZONE,
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

function toDate(value) {
  if (value === null || value === undefined || value === '') return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/** "11 Nov 2026, 10:00 am" (empty text for missing or invalid values). */
export function formatDateTime(value) {
  const date = toDate(value)
  return date ? dateTimeFormat.format(date) : ''
}

/** "11 Nov 2026" */
export function formatDate(value) {
  const date = toDate(value)
  return date ? dateFormat.format(date) : ''
}

// ---- Plain dates (no time), e.g. a purchase date "2026-11-12" -------------------------
// They are calendar days, not moments, so they are shown exactly as stored (no
// timezone shift). "Today" is today in the company timezone (Q11).

const plainDateFormat = new Intl.DateTimeFormat('en-IN', {
  timeZone: 'UTC',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

/** "2026-11-12" -> "12 Nov 2026" (empty text for missing or invalid values). */
export function formatPlainDate(value) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return ''
  const date = new Date(`${value}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? '' : plainDateFormat.format(date)
}

/** Today in the company timezone as "YYYY-MM-DD" (the format of <input type="date">). */
export function todayInCompanyTimezone(now = new Date()) {
  // en-CA writes dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', { timeZone: APP_TIMEZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now)
}
