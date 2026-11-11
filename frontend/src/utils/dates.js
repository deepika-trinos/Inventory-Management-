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
