// Tests for the Categories page filters (fix after Phase 1-3 testing, decision D9):
// the Tracking and Status filters combine; "Clear filters" resets them; an empty
// result caused by filters or search says "No matches" (not "No categories yet")
// and offers a button that clears them. The server is replaced by stand-ins.
// Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listCategories } from '../../api/categories'
import { NotificationProvider } from '../../context/NotificationContext'
import CategoriesPage from './CategoriesPage'

vi.mock('../../api/categories', async (importOriginal) => ({ ...(await importOriginal()), listCategories: vi.fn() }))

const cat = (id, name, tracking_type, status) => ({
  id, name, tracking_type, status, description: null, updated_at: '2026-11-12T05:00:00Z',
})
const ALL = [
  cat(1, 'Laptops', 'serialized', 'inactive'),
  cat(2, 'Mice', 'bulk', 'active'),
  cat(3, 'laptop', 'serialized', 'active'),
  cat(4, 'keyboard', 'bulk', 'active'),
]

// A stand-in server that filters like the real one (both filters must match).
function fakeServer({ trackingType, status, search }) {
  const items = ALL.filter(
    (c) =>
      (!trackingType || c.tracking_type === trackingType) &&
      (!status || c.status === status) &&
      (!search || c.name.toLowerCase().includes(search.toLowerCase())),
  )
  return Promise.resolve({ items, total: items.length, page: 1, page_size: 20 })
}

beforeEach(() => {
  vi.clearAllMocks()
  listCategories.mockImplementation(fakeServer)
})

function renderPage() {
  render(
    <NotificationProvider>
      <CategoriesPage />
    </NotificationProvider>,
  )
}

function choose(label, option) {
  fireEvent.mouseDown(screen.getByRole('combobox', { name: label }))
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: option }))
}

const shownNames = () =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => within(row).queryAllByRole('cell')[0]?.textContent)
    .filter(Boolean)

const lastCall = () => listCategories.mock.calls.at(-1)[0]

describe('CategoriesPage filters', () => {
  it('lists every category when no filter is set, without a Clear filters button', async () => {
    renderPage()
    await screen.findByText('keyboard')
    expect(shownNames()).toHaveLength(4)
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('Inactive shows the inactive category', async () => {
    renderPage()
    await screen.findByText('keyboard')
    choose(/Status/, 'Inactive')
    await waitFor(() => expect(shownNames()).toEqual(['Laptops']))
  })

  it('By quantity shows both by-quantity categories', async () => {
    renderPage()
    await screen.findByText('keyboard')
    choose(/Tracking/, 'By quantity')
    await waitFor(() => expect(shownNames()).toEqual(['Mice', 'keyboard']))
  })

  it('the two filters combine: both must match', async () => {
    renderPage()
    await screen.findByText('keyboard')
    choose(/Status/, 'Active')
    choose(/Tracking/, 'One-by-one')

    await waitFor(() => expect(shownNames()).toEqual(['laptop']))
    expect(lastCall()).toMatchObject({ trackingType: 'serialized', status: 'active' })
  })

  it('an empty result from filters says "No matches", not "No categories yet", and can clear them', async () => {
    renderPage()
    await screen.findByText('keyboard')
    choose(/Status/, 'Inactive')
    choose(/Tracking/, 'By quantity')

    expect(await screen.findByText('No matches')).toBeTruthy()
    expect(screen.getByText('Nothing matches the selected filters.')).toBeTruthy()
    expect(screen.queryByText('No categories yet')).toBeNull()

    const clearButtons = screen.getAllByRole('button', { name: 'Clear filters' }) // toolbar + empty message
    fireEvent.click(clearButtons.at(-1))

    await waitFor(() => expect(shownNames()).toHaveLength(4))
    expect(lastCall()).toMatchObject({ trackingType: '', status: '' })
    // Both dropdowns are back to "All" (empty value), so no filter button is left.
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('the toolbar Clear filters button resets both filters', async () => {
    renderPage()
    await screen.findByText('keyboard')
    choose(/Status/, 'Active')
    choose(/Tracking/, 'One-by-one')
    await waitFor(() => expect(shownNames()).toEqual(['laptop']))

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))

    await waitFor(() => expect(shownNames()).toHaveLength(4))
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('search plus filters with no result offers "Clear search and filters", which empties the search box too', async () => {
    renderPage()
    await screen.findByText('keyboard')
    choose(/Tracking/, 'By quantity')
    fireEvent.change(screen.getByRole('textbox', { name: 'Search' }), { target: { value: 'laptop' } })

    expect(await screen.findByText('Nothing matches “laptop” with the selected filters.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Clear search and filters' }))

    await waitFor(() => expect(shownNames()).toHaveLength(4))
    expect(screen.getByRole('textbox', { name: 'Search' }).value).toBe('')
  })

  it('a truly empty list still says "No categories yet"', async () => {
    listCategories.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
    renderPage()
    expect(await screen.findByText('No categories yet')).toBeTruthy()
    expect(screen.queryByText('No matches')).toBeNull()
  })
})
