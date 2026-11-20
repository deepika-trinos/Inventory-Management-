// Tests for the list-page filters on Vendors, Employees and Inventory (decision D9,
// same behaviour as Categories): filters combine; "Clear filters" appears while a
// filter is set and resets them; an empty result caused by filters says "No matches"
// (not "No ... yet") with a button that clears them; a truly empty list keeps its
// "No ... yet" message. The server is replaced by stand-ins. Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listCategories } from '../api/categories'
import { listDepartments, listEmployees } from '../api/employees'
import { listStockItems } from '../api/stockItems'
import { listVendors } from '../api/vendors'
import { NotificationProvider } from '../context/NotificationContext'
import EmployeesPage from './employees/EmployeesPage'
import InventoryPage from './inventory/InventoryPage'
import VendorsPage from './vendors/VendorsPage'

vi.mock('../api/vendors', async (importOriginal) => ({ ...(await importOriginal()), listVendors: vi.fn() }))
vi.mock('../api/employees', async (importOriginal) => ({
  ...(await importOriginal()),
  listEmployees: vi.fn(),
  listDepartments: vi.fn(),
}))
vi.mock('../api/stockItems', async (importOriginal) => ({ ...(await importOriginal()), listStockItems: vi.fn() }))
vi.mock('../api/categories', async (importOriginal) => ({ ...(await importOriginal()), listCategories: vi.fn() }))

const page = (items) => ({ items, total: items.length, page: 1, page_size: 20 })
const T = '2026-11-12T05:00:00Z'

const VENDORS = [
  { id: 1, name: 'Acme IT Supplies', status: 'active', created_at: T, updated_at: T },
  { id: 2, name: 'Gone Ltd', status: 'inactive', created_at: T, updated_at: T },
]
const EMPLOYEES = [
  { id: 1, employee_code: 'EMP-001', full_name: 'Asha Kumar', department: 'Finance', status: 'active', has_login: false, created_at: T, updated_at: T },
  { id: 2, employee_code: 'EMP-002', full_name: 'Ravi Shah', department: 'IT', status: 'inactive', has_login: false, created_at: T, updated_at: T },
]
const PERIPHERALS = { id: 2, name: 'Peripherals', tracking_type: 'bulk', status: 'active' }
const CABLES = { id: 3, name: 'Cables', tracking_type: 'bulk', status: 'active' }
const ITEMS = [
  { id: 1, name: 'USB mouse', category: PERIPHERALS, unit_of_measure: 'pieces', reorder_threshold: 5, quantity_on_hand: 25, status: 'active', created_at: T, updated_at: T },
  { id: 2, name: 'HDMI cable', category: CABLES, unit_of_measure: 'pieces', reorder_threshold: 0, quantity_on_hand: 0, status: 'inactive', created_at: T, updated_at: T },
]

// Stand-in servers that filter like the real ones (every filter must match).
const matches = (row, { status }) => !status || row.status === status

beforeEach(() => {
  vi.clearAllMocks()
  listVendors.mockImplementation((args) => Promise.resolve(page(VENDORS.filter((v) => matches(v, args)))))
  listEmployees.mockImplementation((args) =>
    Promise.resolve(page(EMPLOYEES.filter((e) => matches(e, args) && (!args.department || e.department === args.department)))),
  )
  listDepartments.mockResolvedValue(['Finance', 'IT'])
  listStockItems.mockImplementation((args) =>
    Promise.resolve(page(ITEMS.filter((i) => matches(i, args) && (!args.categoryId || i.category.id === args.categoryId)))),
  )
  listCategories.mockResolvedValue(page([CABLES, PERIPHERALS]))
})

function renderPage(Page) {
  render(
    <NotificationProvider>
      <MemoryRouter>
        <Page />
      </MemoryRouter>
    </NotificationProvider>,
  )
}

function choose(label, option) {
  fireEvent.mouseDown(screen.getByRole('combobox', { name: label }))
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: option }))
}

const dataRows = () => screen.getAllByRole('row').slice(1).filter((r) => within(r).queryAllByRole('cell').length > 1)

const PAGES = [
  { name: 'Vendors', Page: VendorsPage, api: listVendors, first: 'Acme IT Supplies', empty: 'No vendors yet' },
  { name: 'Employees', Page: EmployeesPage, api: listEmployees, first: 'Asha Kumar', empty: 'No employees yet' },
  { name: 'Inventory', Page: InventoryPage, api: listStockItems, first: 'USB mouse', empty: 'No stock items yet' },
]

describe.each(PAGES)('$name page filters', ({ Page, api, first, empty }) => {
  it('shows every row and no Clear filters button when no filter is set', async () => {
    renderPage(Page)
    await screen.findByText(first)
    expect(dataRows()).toHaveLength(2)
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('Inactive shows only the inactive row; the toolbar Clear filters resets it', async () => {
    renderPage(Page)
    await screen.findByText(first)
    choose(/Status/, 'Inactive')
    await waitFor(() => expect(dataRows()).toHaveLength(1))
    expect(screen.queryByText(first)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))

    await waitFor(() => expect(dataRows()).toHaveLength(2))
    expect(api.mock.calls.at(-1)[0]).toMatchObject({ status: '' })
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it(`an empty filtered result says "No matches" (not "${empty}") and can clear the filters`, async () => {
    api.mockImplementation(() => Promise.resolve(page([])))
    renderPage(Page)
    expect(await screen.findByText(empty)).toBeTruthy() // truly empty: unchanged message

    choose(/Status/, 'Active')

    expect(await screen.findByText('No matches')).toBeTruthy()
    expect(screen.getByText('Nothing matches the selected filters.')).toBeTruthy()
    expect(screen.queryByText(empty)).toBeNull()
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' }).at(-1)) // the one in the message
    expect(await screen.findByText(empty)).toBeTruthy()
  })
})

describe('filters combine (both must match)', () => {
  it('Employees: department and status together; Clear filters resets both', async () => {
    renderPage(EmployeesPage)
    await screen.findByText('Asha Kumar')
    choose(/Department/, 'IT')
    choose(/Status/, 'Active')

    expect(await screen.findByText('No matches')).toBeTruthy()
    expect(listEmployees.mock.calls.at(-1)[0]).toMatchObject({ department: 'IT', status: 'active' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' })[0]) // toolbar
    await waitFor(() => expect(dataRows()).toHaveLength(2))
    expect(listEmployees.mock.calls.at(-1)[0]).toMatchObject({ department: '', status: '' })
  })

  it('Inventory: category and status together; Clear filters resets both', async () => {
    renderPage(InventoryPage)
    await screen.findByText('USB mouse')
    choose(/Category/, 'Cables')
    choose(/Status/, 'Active')

    expect(await screen.findByText('No matches')).toBeTruthy()
    expect(listStockItems.mock.calls.at(-1)[0]).toMatchObject({ categoryId: 3, status: 'active' })

    fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' }).at(-1))
    await waitFor(() => expect(dataRows()).toHaveLength(2))
    expect(listStockItems.mock.calls.at(-1)[0]).toMatchObject({ categoryId: '', status: '' })
  })
})
