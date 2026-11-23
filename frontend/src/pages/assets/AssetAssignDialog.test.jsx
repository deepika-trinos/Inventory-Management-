// Tests for the Assign form and its confirm box (Slice 5.1; owner's answers N1, N2, N3):
// screen checks (employee required; date not in the future and not before the asset was
// added; expected return not before the assignment date); only ACTIVE employees offered
// (with or without a login); the confirm box "Assign AST-000003 to Asha Kumar (EMP-001)?";
// what is sent; server problems shown under the right field or on top of the form.
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { assignAsset } from '../../api/assets'
import { listEmployees } from '../../api/employees'
import { todayInCompanyTimezone } from '../../utils/dates'
import AssetAssignDialog, { assetCreatedOn, validateAssignment } from './AssetAssignDialog'

vi.mock('../../api/assets', async (importOriginal) => ({ ...(await importOriginal()), assignAsset: vi.fn() }))
vi.mock('../../api/employees', async (importOriginal) => ({ ...(await importOriginal()), listEmployees: vi.fn() }))

const ASHA = { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar', status: 'active', department: 'Finance' }
const ASSET = {
  id: 3, asset_code: 'AST-000003', name: 'Laptops: Dell Latitude 5440', serial_number: 'DL-1003', status: 'available',
  created_at: '2026-11-01T06:30:00Z', // 1 Nov 2026 in Asia/Kolkata
}

let onAssigned
beforeEach(() => {
  vi.clearAllMocks()
  onAssigned = vi.fn()
  listEmployees.mockResolvedValue({ items: [ASHA], total: 1, page: 1, page_size: 20 })
})

function renderDialog(asset = ASSET) {
  render(<AssetAssignDialog open asset={asset} onClose={vi.fn()} onAssigned={onAssigned} />)
}

const form = () => within(screen.getByRole('dialog'))
const fill = (label, value) => fireEvent.change(form().getByLabelText(label), { target: { value } })

async function pickAsha() {
  const picker = form().getByRole('combobox', { name: /^Employee/ })
  fireEvent.change(picker, { target: { value: 'asha' } })
  fireEvent.click(await screen.findByRole('option', { name: /EMP-001 · Asha Kumar/ }))
}

describe('validateAssignment', () => {
  const ok = { employee: ASHA, assignmentDate: '2026-11-20', expectedReturnDate: '' }

  it('accepts today or earlier, not before the asset was added, with an optional expected return', () => {
    expect(validateAssignment(ok, '2026-11-01', '2026-11-23')).toEqual({})
    expect(validateAssignment({ ...ok, assignmentDate: '2026-11-01', expectedReturnDate: '2026-11-01' }, '2026-11-01', '2026-11-23')).toEqual({})
  })

  it('refuses a missing employee, a future date, a date before the asset was added and an early return', () => {
    expect(validateAssignment({ ...ok, employee: null }, '2026-11-01', '2026-11-23').employee).toBe('Choose the employee.')
    expect(validateAssignment({ ...ok, assignmentDate: '2026-11-24' }, '2026-11-01', '2026-11-23').assignmentDate).toBe(
      'The assignment date cannot be in the future.',
    )
    expect(validateAssignment({ ...ok, assignmentDate: '2026-10-31' }, '2026-11-01', '2026-11-23').assignmentDate).toBe(
      'The assignment date cannot be before the asset was added (01 Nov 2026).',
    )
    expect(validateAssignment({ ...ok, expectedReturnDate: '2026-11-19' }, '2026-11-01', '2026-11-23').expectedReturnDate).toBe(
      'The expected return date cannot be before the assignment date.',
    )
  })

  it('the asset was added on its creation day in the company timezone', () => {
    expect(assetCreatedOn({ created_at: '2026-11-01T20:00:00Z' })).toBe('2026-11-02') // 1:30 am IST
  })
})

describe('AssetAssignDialog', () => {
  it('starts with today as the assignment date and offers active employees with or without a login', async () => {
    renderDialog()
    expect(form().getByLabelText(/^Assignment date/).value).toBe(todayInCompanyTimezone())
    await pickAsha()
    expect(listEmployees.mock.calls.at(-1)[0]).toMatchObject({ status: 'active', hasLogin: undefined })
  })

  it('checks the form before asking the server', async () => {
    renderDialog()
    fill(/^Assignment date/, '2999-01-01')
    fireEvent.click(form().getByRole('button', { name: 'Assign…' }))

    expect(await screen.findByText('Choose the employee.')).toBeTruthy()
    expect(screen.getByText('The assignment date cannot be in the future.')).toBeTruthy()
    expect(assignAsset).not.toHaveBeenCalled()
  })

  it('asks to confirm, then assigns with the dates', async () => {
    const saved = { ...ASSET, status: 'assigned', current_assignment: { employee: ASHA } }
    assignAsset.mockResolvedValue(saved)
    renderDialog()
    await pickAsha()
    fill(/^Assignment date/, '2026-11-20')
    fill(/^Expected return date/, '2026-12-20')
    fireEvent.click(form().getByRole('button', { name: 'Assign…' }))

    const confirm = within(await screen.findByRole('dialog', { name: 'Assign AST-000003 to Asha Kumar (EMP-001)?' }))
    const lines = confirm.getAllByTestId('assign-confirm-line').map((l) => l.textContent)
    expect(lines).toContain('Assignment date: 20 Nov 2026.')
    expect(lines).toContain('Expected return: 20 Dec 2026.')
    fireEvent.click(confirm.getByRole('button', { name: 'Assign' }))

    await waitFor(() => expect(onAssigned).toHaveBeenCalledWith(saved))
    expect(assignAsset).toHaveBeenCalledWith('AST-000003', {
      employeeId: 3, assignmentDate: '2026-11-20', expectedReturnDate: '2026-12-20',
    })
  })

  it('the expected return date is optional', async () => {
    assignAsset.mockResolvedValue({ ...ASSET, status: 'assigned' })
    renderDialog()
    await pickAsha()
    fireEvent.click(form().getByRole('button', { name: 'Assign…' }))

    const confirm = within(await screen.findByRole('dialog', { name: /Assign AST-000003/ }))
    expect(confirm.getByText('No expected return date.')).toBeTruthy()
    fireEvent.click(confirm.getByRole('button', { name: 'Assign' }))
    await waitFor(() => expect(assignAsset).toHaveBeenCalledWith('AST-000003', expect.objectContaining({ expectedReturnDate: undefined })))
  })

  it('Go back returns to the form without saving', async () => {
    renderDialog()
    await pickAsha()
    fireEvent.click(form().getByRole('button', { name: 'Assign…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Assign AST-000003/ })).getByRole('button', { name: 'Go back' }))

    expect(await screen.findByRole('button', { name: 'Assign…' })).toBeTruthy()
    expect(assignAsset).not.toHaveBeenCalled()
  })

  it('an inactive employee refused by the server is shown under the employee', async () => {
    assignAsset.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'employee_inactive', message: 'Asha Kumar (EMP-001) is deactivated. Assets cannot be assigned to them.' } } },
    })
    renderDialog()
    await pickAsha()
    fireEvent.click(form().getByRole('button', { name: 'Assign…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Assign AST-000003/ })).getByRole('button', { name: 'Assign' }))

    expect(await screen.findByText('Asha Kumar (EMP-001) is deactivated. Assets cannot be assigned to them.')).toBeTruthy()
    expect(await screen.findByRole('button', { name: 'Assign…' })).toBeTruthy() // back on the form
    expect(onAssigned).not.toHaveBeenCalled()
  })

  it('an asset someone else assigned a moment ago is shown on top of the form', async () => {
    assignAsset.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'asset_already_assigned', message: 'AST-000003 is already assigned. Return it first.' } } },
    })
    renderDialog()
    await pickAsha()
    fireEvent.click(form().getByRole('button', { name: 'Assign…' }))
    fireEvent.click(within(await screen.findByRole('dialog', { name: /Assign AST-000003/ })).getByRole('button', { name: 'Assign' }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toBe('AST-000003 is already assigned. Return it first.')
  })
})
