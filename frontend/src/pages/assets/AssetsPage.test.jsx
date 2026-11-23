// Tests for the Assets page, the asset register (Slice 4.1, AST-03, AST-05): columns,
// search, the category / status / location filters (combined), Clear filters and
// "No matches" (D9), and clickable rows that open the asset page (D7).
// The server is replaced by stand-ins (no network). Run with: npm test
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useParams } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createAsset, listAssetLocations, listAssets } from '../../api/assets'
import { listCategories } from '../../api/categories'
import { NotificationProvider } from '../../context/NotificationContext'
import AssetsPage from './AssetsPage'

vi.mock('../../api/assets', async (importOriginal) => ({
  ...(await importOriginal()),
  listAssets: vi.fn(),
  listAssetLocations: vi.fn(),
  createAsset: vi.fn(),
}))
vi.mock('../../api/categories', async (importOriginal) => ({ ...(await importOriginal()), listCategories: vi.fn() }))

const page = (items) => ({ items, total: items.length, page: 1, page_size: 20 })
const T = '2026-11-12T05:00:00Z'
const LAPTOPS = { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' }
const MONITORS = { id: 4, name: 'Monitors', tracking_type: 'serialized', status: 'inactive' }
const asset = (id, extra) => ({
  id, asset_code: `AST-00000${id}`, brand: 'Dell', model: 'Latitude 5440', status: 'available', location: null,
  warranty_expiry: null, created_at: T, category: LAPTOPS, ...extra,
})
const ASSETS = [
  asset(1, { name: 'Laptops: Dell Latitude 5440', serial_number: 'DL-1001', location: 'Chennai' }),
  asset(2, { name: 'CEO laptop', serial_number: 'DL-1002', status: 'assigned' }),
  asset(3, { name: 'Spare monitor', serial_number: 'MON-1', brand: null, model: 'P2422H', category: MONITORS, location: 'Chennai' }),
]

// A stand-in server that searches and filters like the real one (every filter must match).
function fakeList({ search, categoryId, status, location }) {
  const term = (search ?? '').toLowerCase()
  return Promise.resolve(
    page(
      ASSETS.filter(
        (a) =>
          (!term || [a.asset_code, a.serial_number, a.name].some((v) => v.toLowerCase().includes(term))) &&
          (!categoryId || a.category.id === categoryId) &&
          (!status || a.status === status) &&
          (!location || (a.location ?? '').toLowerCase() === location.toLowerCase()),
      ),
    ),
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  listAssets.mockImplementation(fakeList)
  listAssetLocations.mockResolvedValue(['Chennai'])
  listCategories.mockResolvedValue(page([LAPTOPS, MONITORS]))
})

function AssetPageStandIn() {
  const { assetId } = useParams()
  return <p>Asset page {assetId}</p>
}

function renderPage() {
  render(
    <NotificationProvider>
      <MemoryRouter initialEntries={['/assets']}>
        <Routes>
          <Route path="/assets" element={<AssetsPage />} />
          <Route path="/assets/:assetId" element={<AssetPageStandIn />} />
        </Routes>
      </MemoryRouter>
    </NotificationProvider>,
  )
}

function choose(label, option) {
  fireEvent.mouseDown(screen.getByRole('combobox', { name: label }))
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: option }))
}

const dataRows = () => screen.getAllByRole('row').slice(1).filter((r) => within(r).queryAllByRole('cell').length > 1)
const shownCodes = () => dataRows().map((r) => within(r).getAllByRole('cell')[0].textContent)

describe('AssetsPage', () => {
  it('lists assets newest asset ID first with their columns', async () => {
    renderPage()
    await screen.findByText('AST-000001')

    expect(listAssets.mock.calls[0][0]).toMatchObject({ page: 1, sort: '-asset_code' })
    for (const header of ['Asset ID', 'Name', 'Category', 'Serial number', 'Model', 'Location', 'Status']) {
      expect(screen.getByRole('columnheader', { name: header })).toBeTruthy()
    }
    const first = within(dataRows()[0])
    expect(first.getByText('Laptops: Dell Latitude 5440')).toBeTruthy()
    expect(first.getByText('Laptops')).toBeTruthy()
    expect(first.getByText('DL-1001')).toBeTruthy()
    expect(first.getByText('Dell Latitude 5440')).toBeTruthy()
    expect(first.getByText('Chennai')).toBeTruthy()
    expect(first.getByText('Available')).toBeTruthy()
    expect(within(dataRows()[1]).getByText('Assigned')).toBeTruthy()
    expect(screen.queryByRole('combobox', { name: /Employee/ })).toBeNull() // A1: arrives in Slice 5.1
  })

  it('finds an asset by ID, serial number or name', async () => {
    renderPage()
    await screen.findByText('AST-000001')
    const box = screen.getByRole('textbox', { name: 'Search' })

    for (const [term, expected] of [['ast-000002', ['AST-000002']], ['MON-1', ['AST-000003']], ['ceo', ['AST-000002']]]) {
      fireEvent.change(box, { target: { value: term } })
      await waitFor(() => expect(shownCodes()).toEqual(expected))
      expect(listAssets.mock.calls.at(-1)[0]).toMatchObject({ search: term })
    }
  })

  it('offers one-by-one categories (inactive marked), every status and the locations in use', async () => {
    renderPage()
    await screen.findByText('AST-000001')

    expect(listCategories).toHaveBeenCalledWith(expect.objectContaining({ trackingType: 'serialized', pageSize: 100 }))
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /Category/ }))
    expect(within(screen.getByRole('listbox')).getByRole('option', { name: 'Monitors (inactive)' })).toBeTruthy()
    fireEvent.keyDown(screen.getByRole('listbox'), { key: 'Escape' })

    fireEvent.mouseDown(screen.getByRole('combobox', { name: /Status/ }))
    const statuses = within(screen.getByRole('listbox')).getAllByRole('option').map((o) => o.textContent)
    expect(statuses).toEqual(['All statuses', 'Available', 'Assigned', 'Under Maintenance', 'Damaged', 'Retired'])
    fireEvent.keyDown(screen.getByRole('listbox'), { key: 'Escape' })

    fireEvent.mouseDown(screen.getByRole('combobox', { name: /Location/ }))
    expect(within(screen.getByRole('listbox')).getAllByRole('option').map((o) => o.textContent)).toEqual(['All locations', 'Chennai'])
  })

  it('filters combine and Clear filters resets them', async () => {
    renderPage()
    await screen.findByText('AST-000001')

    choose(/Location/, 'Chennai')
    await waitFor(() => expect(shownCodes()).toEqual(['AST-000001', 'AST-000003']))
    choose(/Category/, 'Laptops')
    await waitFor(() => expect(shownCodes()).toEqual(['AST-000001']))
    expect(listAssets.mock.calls.at(-1)[0]).toMatchObject({ location: 'Chennai', categoryId: 3, status: '' })

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))

    await waitFor(() => expect(shownCodes()).toHaveLength(3))
    expect(listAssets.mock.calls.at(-1)[0]).toMatchObject({ location: '', categoryId: '', status: '' })
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('an empty filtered result says "No matches" and can clear the filters', async () => {
    renderPage()
    await screen.findByText('AST-000001')

    choose(/Status/, 'Retired')

    expect(await screen.findByText('No matches')).toBeTruthy()
    expect(screen.getByText('Nothing matches the selected filters.')).toBeTruthy()
    expect(screen.queryByText('No assets yet')).toBeNull()
    fireEvent.click(screen.getAllByRole('button', { name: 'Clear filters' }).at(-1))
    await waitFor(() => expect(shownCodes()).toHaveLength(3))
  })

  it('a truly empty register says "No assets yet"', async () => {
    listAssets.mockResolvedValue(page([]))
    renderPage()
    expect(await screen.findByText('No assets yet')).toBeTruthy()
  })

  it('clicking a row opens the asset page', async () => {
    renderPage()
    await screen.findByText('AST-000001')

    fireEvent.click(screen.getByRole('row', { name: 'Open AST-000002' }))
    expect(await screen.findByText('Asset page AST-000002')).toBeTruthy()
  })

  it('Enter on a row opens the asset page', async () => {
    renderPage()
    await screen.findByText('AST-000001')

    fireEvent.keyDown(screen.getByRole('row', { name: 'Open AST-000003' }), { key: 'Enter' })
    expect(await screen.findByText('Asset page AST-000003')).toBeTruthy()
  })
})

// Slice 4.5 (A7): "Add existing asset" opens the form; after saving, the new asset's page opens.
describe('AssetsPage: Add existing asset', () => {
  it('opens the form and goes to the new asset after saving', async () => {
    createAsset.mockResolvedValue({ id: 9, asset_code: 'AST-000009' })
    listCategories.mockResolvedValue(page([LAPTOPS]))
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: 'Add existing asset' }))
    const d = within(await screen.findByRole('dialog', { name: 'Add existing asset' }))
    fireEvent.mouseDown(await d.findByRole('combobox', { name: /Category/ }))
    fireEvent.click(await within(screen.getByRole('listbox')).findByRole('option', { name: 'Laptops' }))
    fireEvent.change(d.getByLabelText(/^Name/), { target: { value: 'Old laptop' } })
    fireEvent.change(d.getByLabelText(/^Serial number/), { target: { value: 'OLD-1' } })
    fireEvent.change(d.getByLabelText(/^Model/), { target: { value: 'T480' } })
    fireEvent.click(d.getByRole('button', { name: 'Add asset' }))

    expect(await screen.findByText('Asset page AST-000009')).toBeTruthy()
    expect(screen.getByText('AST-000009 added.')).toBeTruthy()
  })
})
