// Tests for the Inventory list's Slice 4.3 additions (INV-02, INV-06): the "Low stock"
// badge on flagged items, the Stock level filter (with Clear filters and "No matches",
// D9), and the item name linking to the item's page. The server is replaced by stand-ins.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useParams } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listCategories } from '../../api/categories'
import { listStockItems } from '../../api/stockItems'
import { NotificationProvider } from '../../context/NotificationContext'
import InventoryPage from './InventoryPage'

vi.mock('../../api/stockItems', async (importOriginal) => ({ ...(await importOriginal()), listStockItems: vi.fn() }))
vi.mock('../../api/categories', async (importOriginal) => ({ ...(await importOriginal()), listCategories: vi.fn() }))

const page = (items) => ({ items, total: items.length, page: 1, page_size: 20 })
const T = '2026-11-22T05:00:00Z'
const PERIPHERALS = { id: 2, name: 'Peripherals', tracking_type: 'bulk', status: 'active' }
const item = (id, name, onHand, threshold, low, status = 'active') => ({
  id, name, category: PERIPHERALS, unit_of_measure: 'pieces', reorder_threshold: threshold,
  quantity_on_hand: onHand, low_stock: low, status, created_at: T, updated_at: T,
})
const ITEMS = [item(1, 'HDMI cable', 2, 5, true), item(2, 'USB mouse', 25, 5, false), item(3, 'Old mouse', 0, 0, false, 'inactive')]

beforeEach(() => {
  vi.clearAllMocks()
  listStockItems.mockImplementation(({ lowStock }) => Promise.resolve(page(lowStock === true ? ITEMS.filter((i) => i.low_stock) : ITEMS)))
  listCategories.mockResolvedValue(page([PERIPHERALS]))
})

function ItemPageStandIn() {
  const { itemId } = useParams()
  return <p>Stock item page {itemId}</p>
}

function renderPage() {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={['/inventory']}>
        <Routes>
          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="/inventory/:itemId" element={<ItemPageStandIn />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

const rowOf = (name) => screen.getByText(name).closest('tr')
const dataRows = () => screen.getAllByRole('row').slice(1).filter((r) => within(r).queryAllByRole('cell').length > 1)

describe('Inventory page: stock balances', () => {
  it('shows "Low stock" only on flagged items', async () => {
    renderPage()
    await screen.findByText('HDMI cable')

    expect(within(rowOf('HDMI cable')).getByText('Low stock')).toBeTruthy()
    expect(within(rowOf('USB mouse')).queryByText('Low stock')).toBeNull()
    expect(within(rowOf('Old mouse')).queryByText('Low stock')).toBeNull()
    expect(within(rowOf('HDMI cable')).getByText('2')).toBeTruthy()
  })

  it('the Stock level filter asks for low-stock items only, and Clear filters resets it', async () => {
    renderPage()
    await screen.findByText('HDMI cable')

    fireEvent.mouseDown(screen.getByRole('combobox', { name: /Stock level/ }))
    fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: 'Low stock' }))

    await waitFor(() => expect(dataRows()).toHaveLength(1))
    expect(listStockItems.mock.calls.at(-1)[0]).toMatchObject({ lowStock: true })

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    await waitFor(() => expect(dataRows()).toHaveLength(3))
    expect(listStockItems.mock.calls.at(-1)[0].lowStock).toBeUndefined()
  })

  it('no low-stock items says "No matches", not "No stock items yet"', async () => {
    listStockItems.mockImplementation(({ lowStock }) => Promise.resolve(page(lowStock ? [] : ITEMS)))
    renderPage()
    await screen.findByText('HDMI cable')

    fireEvent.mouseDown(screen.getByRole('combobox', { name: /Stock level/ }))
    fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: 'Low stock' }))

    expect(await screen.findByText('No matches')).toBeTruthy()
    expect(screen.queryByText('No stock items yet')).toBeNull()
  })

  it('the item name opens the item page', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('link', { name: 'USB mouse' }))
    expect(await screen.findByText('Stock item page 2')).toBeTruthy()
  })
})
