// Tests for returning an asset (Slice 5.2; owner's answers Q5, N4, N5): the Return form
// (outcome-dependent notes rule, 0 / 1,000 counter, date rules), the confirm box (holder,
// dates, new status), what is sent, server problems under the right field, and on the asset
// page: "Return…" only while Assigned, the new status and no holder afterwards, and the
// history line "Returned by Asha Kumar — Damaged: screen cracked".
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getAsset, getAssetHistory, returnAsset } from '../../api/assets'
import { NotificationProvider } from '../../context/NotificationContext'
import { todayInCompanyTimezone } from '../../utils/dates'
import AssetDetailPage, { historyNote } from './AssetDetailPage'
import AssetReturnDialog, { notesRequired, validateReturn } from './AssetReturnDialog'

// Slice 6.1: the asset page also loads its maintenance requests; none here.
vi.mock('../../api/maintenance', async (importOriginal) => ({
  ...(await importOriginal()),
  getAssetRequests: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../../api/assets', async (importOriginal) => ({
  ...(await importOriginal()),
  getAsset: vi.fn(),
  getAssetHistory: vi.fn(),
  returnAsset: vi.fn(),
}))

const USER = { id: 2, email: 'manager@example.com' }
const ASHA = { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar', status: 'active' }
const HOLDING = {
  id: 5, employee: ASHA, assignment_date: '2026-11-20', expected_return_date: null, assigned_by: USER, created_at: '2026-11-20T05:00:00Z',
}
const ASSET = {
  id: 3, asset_code: 'AST-000003', name: 'Dell Latitude 5440', brand: 'Dell', model: 'Latitude 5440', serial_number: 'DL-503',
  status: 'assigned', location: null, warranty_expiry: null, purchase_date: null, cost: null,
  category: { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' }, purchase: null,
  created_by: USER, created_at: '2026-11-01T06:30:00Z', updated_at: '2026-11-20T05:00:00Z', current_assignment: HOLDING,
}
const RETURNED_ENTRY = {
  id: 41, action: 'assignment.returned', created_at: '2026-11-23T05:00:00Z', actor: USER, before: { status: 'assigned' },
  after: { status: 'damaged', employee_name: 'Asha Kumar', employee_code: 'EMP-001', inspection_outcome: 'damaged', condition_notes: 'screen cracked' },
}
const history = (items) => ({ items, total: items.length, page: 1, page_size: 10 })

let onReturned
beforeEach(() => {
  vi.clearAllMocks()
  onReturned = vi.fn()
  getAsset.mockResolvedValue(ASSET)
  getAssetHistory.mockResolvedValue(history([]))
})

function renderDialog(asset = ASSET) {
  render(<AssetReturnDialog open asset={asset} onClose={vi.fn()} onReturned={onReturned} />)
}

const form = () => within(screen.getByRole('dialog'))
const fill = (label, value) => fireEvent.change(form().getByLabelText(label), { target: { value } })
const pick = (label) => fireEvent.click(form().getByRole('radio', { name: label }))

describe('validateReturn', () => {
  const ok = { returnDate: '2026-11-22', outcome: 'available', notes: '' }

  it('notes are required unless the outcome is Available', () => {
    expect(notesRequired('available')).toBe(false)
    expect(notesRequired('damaged')).toBe(true)
    expect(notesRequired('under_maintenance')).toBe(true)
    expect(validateReturn(ok, '2026-11-20', '2026-11-23')).toEqual({})
    expect(validateReturn({ ...ok, outcome: 'damaged', notes: '   ' }, '2026-11-20', '2026-11-23').notes).toBe(
      'Please describe the condition: required when the outcome is Damaged.',
    )
    expect(validateReturn({ ...ok, outcome: 'under_maintenance', notes: 'Keyboard' }, '2026-11-20', '2026-11-23')).toEqual({})
  })

  it('refuses a missing outcome, a future date, a date before the assignment and long notes', () => {
    expect(validateReturn({ ...ok, outcome: '' }, '2026-11-20', '2026-11-23').outcome).toBe('Choose the inspection outcome.')
    expect(validateReturn({ ...ok, returnDate: '2026-11-24' }, '2026-11-20', '2026-11-23').returnDate).toBe(
      'The return date cannot be in the future.',
    )
    expect(validateReturn({ ...ok, returnDate: '2026-11-19' }, '2026-11-20', '2026-11-23').returnDate).toBe(
      'The return date cannot be before the assignment date (20 Nov 2026).',
    )
    expect(validateReturn({ ...ok, returnDate: '2026-11-20' }, '2026-11-20', '2026-11-23')).toEqual({}) // same day allowed
    expect(validateReturn({ ...ok, notes: 'x'.repeat(1001) }, '2026-11-20', '2026-11-23').notes).toBe('Use at most 1,000 characters.')
  })
})

describe('AssetReturnDialog', () => {
  it('shows the holder, today as the return date and the three outcomes', () => {
    renderDialog()
    expect(screen.getByTestId('return-holder').textContent).toBe('Held by Asha Kumar (EMP-001) since 20 Nov 2026')
    expect(form().getByLabelText(/^Return date/).value).toBe(todayInCompanyTimezone())
    expect(form().getAllByRole('radio').map((r) => r.value)).toEqual(['available', 'under_maintenance', 'damaged'])
  })

  it('marks the notes required only when the outcome is not Available, with a 0 / 1,000 counter', () => {
    renderDialog()
    expect(form().getByLabelText(/^Condition notes \(optional\)/)).toBeTruthy()
    expect(form().getByText('0 / 1,000')).toBeTruthy()

    pick('Damaged')
    expect(form().queryByLabelText(/\(optional\)/)).toBeNull()
    expect(form().getByText('0 / 1,000 · required for this outcome')).toBeTruthy()
    fill(/^Condition notes/, 'Screen cracked')
    expect(form().getByText('14 / 1,000 · required for this outcome')).toBeTruthy()

    pick('Available')
    expect(form().getByLabelText(/^Condition notes \(optional\)/)).toBeTruthy()
  })

  it('checks the form before asking the server', async () => {
    renderDialog()
    fireEvent.click(form().getByRole('button', { name: 'Return…' }))
    expect(await screen.findByText('Choose the inspection outcome.')).toBeTruthy()

    pick('Under Maintenance')
    fill(/^Return date/, '2026-11-19')
    fireEvent.click(form().getByRole('button', { name: 'Return…' }))
    expect(await screen.findByText('Please describe the condition: required when the outcome is Under Maintenance.')).toBeTruthy()
    expect(screen.getByText('The return date cannot be before the assignment date (20 Nov 2026).')).toBeTruthy()
    expect(returnAsset).not.toHaveBeenCalled()
  })

  it('a good return: confirm box with holder, dates and new status, then sends it', async () => {
    const saved = { ...ASSET, status: 'available', current_assignment: null }
    returnAsset.mockResolvedValue(saved)
    renderDialog()
    pick('Available')
    fill(/^Return date/, '2026-11-22')
    fireEvent.click(form().getByRole('button', { name: 'Return…' }))

    const confirm = within(await screen.findByRole('dialog', { name: 'Return AST-000003 as Available?' }))
    const lines = confirm.getAllByTestId('return-confirm-line').map((l) => l.textContent)
    expect(lines).toEqual([
      'Returned by Asha Kumar (EMP-001).',
      'Assigned on 20 Nov 2026 · returned on 22 Nov 2026.',
      'New status: Available.',
      'No condition notes.',
    ])
    fireEvent.click(confirm.getByRole('button', { name: 'Return' }))

    await waitFor(() => expect(onReturned).toHaveBeenCalledWith(saved, 'available'))
    expect(returnAsset).toHaveBeenCalledWith('AST-000003', { returnDate: '2026-11-22', outcome: 'available', notes: '' })
  })

  it('Under Maintenance says it sets the status only (N5) and sends the notes trimmed', async () => {
    returnAsset.mockResolvedValue({ ...ASSET, status: 'under_maintenance', current_assignment: null })
    renderDialog()
    pick('Under Maintenance')
    fill(/^Condition notes/, '  Keyboard not working  ')
    fireEvent.click(form().getByRole('button', { name: 'Return…' }))

    const confirm = within(await screen.findByRole('dialog', { name: 'Return AST-000003 as Under Maintenance?' }))
    expect(confirm.getByText('Condition: Keyboard not working')).toBeTruthy()
    expect(confirm.getByText('This sets the status only; no maintenance request is opened.')).toBeTruthy()
    fireEvent.click(confirm.getByRole('button', { name: 'Return' }))
    await waitFor(() =>
      expect(returnAsset).toHaveBeenCalledWith('AST-000003', expect.objectContaining({ outcome: 'under_maintenance', notes: 'Keyboard not working' })),
    )
  })

  it('a server refusal returns to the form with the message under the field', async () => {
    returnAsset.mockRejectedValue({
      response: { status: 422, data: { error: { code: 'return_date_before_assignment', message: 'The return date cannot be before the assignment date (2026-11-20).' } } },
    })
    renderDialog()
    pick('Available')
    fireEvent.click(form().getByRole('button', { name: 'Return…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Return AST-000003 as/ })).getByRole('button', { name: 'Return' }))

    expect(await screen.findByText('The return date cannot be before the assignment date (2026-11-20).')).toBeTruthy()
    expect(await screen.findByRole('button', { name: 'Return…' })).toBeTruthy()
    expect(onReturned).not.toHaveBeenCalled()
  })

  it('an asset someone else returned a moment ago is shown on top of the form', async () => {
    returnAsset.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'asset_not_assigned', message: 'AST-000003 is not assigned to anyone, so it cannot be returned.' } } },
    })
    renderDialog()
    pick('Available')
    fireEvent.click(form().getByRole('button', { name: 'Return…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Return AST-000003 as/ })).getByRole('button', { name: 'Return' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toBe('AST-000003 is not assigned to anyone, so it cannot be returned.')
  })
})

function renderPage() {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={['/assets/AST-000003']}>
        <Routes>
          <Route path="/assets/:assetId" element={<AssetDetailPage />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

describe('Return on the asset page', () => {
  it('Return… is shown only while the asset is Assigned', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: 'Return…' })).toBeTruthy()
  })

  it.each(['available', 'under_maintenance', 'damaged'])('no Return… for a %s asset', async (status) => {
    getAsset.mockResolvedValue({ ...ASSET, status, current_assignment: null })
    renderPage()
    await screen.findByRole('button', { name: 'Edit' })
    expect(screen.queryByRole('button', { name: 'Return…' })).toBeNull()
  })

  it('after a damaged return: new status, no holder, history refreshed', async () => {
    returnAsset.mockResolvedValue({ ...ASSET, status: 'damaged', current_assignment: null })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Return…' }))
    const d = within(await screen.findByRole('dialog', { name: 'Return AST-000003' }))
    fireEvent.click(d.getByRole('radio', { name: 'Damaged' }))
    fireEvent.change(d.getByLabelText(/^Condition notes/), { target: { value: 'screen cracked' } })
    fireEvent.click(d.getByRole('button', { name: 'Return…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: 'Return AST-000003 as Damaged?' })).getByRole('button', { name: 'Return' }))

    expect(await screen.findByText('AST-000003 returned. Status: Damaged.')).toBeTruthy()
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Assigned to' })).toBeNull())
    expect(screen.queryByRole('button', { name: 'Return…' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Assign…' }).disabled).toBe(true) // Damaged: cannot be assigned
    await waitFor(() => expect(getAssetHistory.mock.calls.length).toBeGreaterThan(1))
  })

  it('history says "Returned by Asha Kumar — Damaged: screen cracked"', async () => {
    getAsset.mockResolvedValue({ ...ASSET, status: 'damaged', current_assignment: null })
    getAssetHistory.mockResolvedValue(history([RETURNED_ENTRY]))
    renderPage()
    expect(await screen.findByText('Returned by Asha Kumar — Damaged: screen cracked')).toBeTruthy()
    expect(screen.getByText('Returned')).toBeTruthy()
    expect(historyNote({ ...RETURNED_ENTRY, after: { ...RETURNED_ENTRY.after, status: 'available', inspection_outcome: 'available', condition_notes: null } })).toBe(
      'Returned by Asha Kumar — Available',
    )
  })
})
