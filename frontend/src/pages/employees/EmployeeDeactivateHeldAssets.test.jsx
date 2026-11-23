// Tests for deactivating an employee who still holds assets (Slice 5.1, owner's answer N6):
// the server refuses with employee_has_assets; the confirm box stays open, shows the
// message and lists the assets still held (with links to them), and the Deactivate
// button is greyed out. The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listDepartments, listEmployees, setEmployeeActive } from '../../api/employees'
import { NotificationProvider } from '../../context/NotificationContext'
import EmployeesPage from './EmployeesPage'

vi.mock('../../api/employees', async (importOriginal) => ({
  ...(await importOriginal()),
  listEmployees: vi.fn(),
  listDepartments: vi.fn(),
  setEmployeeActive: vi.fn(),
}))

const ASHA = { id: 3, employee_code: 'EMP-001', full_name: 'Asha Kumar', department: 'Finance', status: 'active', user: null }
const MESSAGE = 'Asha Kumar (EMP-001) still holds 2 assets: AST-000001, AST-000003. Return them before deactivating this employee.'

beforeEach(() => {
  vi.clearAllMocks()
  listEmployees.mockResolvedValue({ items: [ASHA], total: 1, page: 1, page_size: 20 })
  listDepartments.mockResolvedValue(['Finance'])
})

function renderPage() {
  render(
    <NotificationProvider>
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>
    </NotificationProvider>,
  )
}

describe('Deactivating an employee who holds assets', () => {
  it('lists the assets still held and keeps the employee active', async () => {
    setEmployeeActive.mockRejectedValue({
      response: {
        status: 409,
        data: {
          error: {
            code: 'employee_has_assets',
            message: MESSAGE,
            details: { assets: [
              { id: 1, asset_code: 'AST-000001', name: 'Laptops: Dell Latitude 5440' },
              { id: 3, asset_code: 'AST-000003', name: 'Spare monitor' },
            ] },
          },
        },
      },
    })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Deactivate Asha Kumar' }))
    const box = within(await screen.findByRole('dialog', { name: 'Deactivate Asha Kumar?' }))
    fireEvent.click(box.getByRole('button', { name: 'Deactivate' }))

    const refusal = within(await screen.findByTestId('employee-has-assets'))
    expect(refusal.getByText(MESSAGE)).toBeTruthy()
    expect(refusal.getByRole('link', { name: 'AST-000001' }).getAttribute('href')).toBe('/assets/AST-000001')
    expect(refusal.getByRole('link', { name: 'AST-000003' }).getAttribute('href')).toBe('/assets/AST-000003')
    expect(refusal.getByText(/Spare monitor/)).toBeTruthy()
    await waitFor(() => expect(box.getByRole('button', { name: 'Deactivate' }).disabled).toBe(true))
    expect(setEmployeeActive).toHaveBeenCalledTimes(1)
  })

  it('Cancel closes the box and clears the message for next time', async () => {
    setEmployeeActive.mockRejectedValueOnce({
      response: { status: 409, data: { error: { code: 'employee_has_assets', message: MESSAGE, details: { assets: [] } } } },
    })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Deactivate Asha Kumar' }))
    fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Deactivate' }))
    await screen.findByTestId('employee-has-assets')
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(screen.queryByTestId('employee-has-assets')).toBeNull())

    setEmployeeActive.mockResolvedValueOnce({ ...ASHA, status: 'inactive' })
    fireEvent.click(await screen.findByRole('button', { name: 'Deactivate Asha Kumar' }))
    const box = within(await screen.findByRole('dialog', { name: 'Deactivate Asha Kumar?' }))
    expect(box.queryByTestId('employee-has-assets')).toBeNull()
    fireEvent.click(box.getByRole('button', { name: 'Deactivate' }))
    expect(await screen.findByText('Asha Kumar deactivated.')).toBeTruthy()
  })
})
