// Tests for "Add existing asset" (Slice 4.5, AST-01; owner's answer A7): only active
// one-by-one categories are offered; category, name, serial and model are required;
// no future purchase date; warranty not before the purchase date; cost format; what is
// sent; server problems shown under the right field. The server is replaced by stand-ins.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createAsset } from '../../api/assets'
import { listCategories } from '../../api/categories'
import AssetCreateDialog, { validateAssetCreate } from './AssetCreateDialog'

vi.mock('../../api/assets', async (importOriginal) => ({ ...(await importOriginal()), createAsset: vi.fn() }))
vi.mock('../../api/categories', async (importOriginal) => ({ ...(await importOriginal()), listCategories: vi.fn() }))

const LAPTOPS = { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' }
const TODAY = '2026-11-23'

let onSaved
beforeEach(() => {
  vi.clearAllMocks()
  onSaved = vi.fn()
  listCategories.mockResolvedValue({ items: [LAPTOPS], total: 1, page: 1, page_size: 100 })
})

function renderDialog() {
  render(<AssetCreateDialog open onClose={vi.fn()} onSaved={onSaved} />)
}

const form = () => within(screen.getByRole('dialog'))
const fill = (label, value) => fireEvent.change(form().getByLabelText(label), { target: { value } })

async function chooseLaptops() {
  fireEvent.mouseDown(await form().findByRole('combobox', { name: /Category/ }))
  fireEvent.click(await within(screen.getByRole('listbox')).findByRole('option', { name: 'Laptops' }))
}

describe('AssetCreateDialog', () => {
  it('asks only for active one-by-one categories', async () => {
    renderDialog()
    await waitFor(() => expect(listCategories).toHaveBeenCalled())
    expect(listCategories.mock.calls[0][0]).toMatchObject({ trackingType: 'serialized', status: 'active' })
  })

  it('refuses missing required fields before asking the server', async () => {
    renderDialog()
    fireEvent.click(form().getByRole('button', { name: 'Add asset' }))
    expect(await screen.findByText('Please choose a category.')).toBeTruthy()
    expect(screen.getByText('Please enter the name.')).toBeTruthy()
    expect(screen.getByText('Please enter the serial number.')).toBeTruthy()
    expect(screen.getByText('Please enter the model.')).toBeTruthy()
    expect(createAsset).not.toHaveBeenCalled()
  })

  it('sends the trimmed details; empty optional fields as null', async () => {
    createAsset.mockResolvedValue({ id: 9, asset_code: 'AST-000009' })
    renderDialog()
    await chooseLaptops()
    fill(/^Name/, '  Dell Latitude 7490 ')
    fill(/^Serial number/, ' OLD-5001 ')
    fill(/^Model/, 'Latitude 7490')
    fill(/^Purchase date/, '2023-04-01')
    fill(/^Cost/, '64999.50')
    fireEvent.click(form().getByRole('button', { name: 'Add asset' }))

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith({ id: 9, asset_code: 'AST-000009' }))
    expect(createAsset).toHaveBeenCalledWith({
      category_id: 3, name: 'Dell Latitude 7490', serial_number: 'OLD-5001', model: 'Latitude 7490',
      brand: null, location: null, purchase_date: '2023-04-01', warranty_expiry: null, cost: '64999.50',
    })
  })

  it('a duplicate serial from the server is shown under the serial number', async () => {
    createAsset.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'serial_number_taken', message: 'Serial number "OLD-5001" is already used by AST-000002.' } } },
    })
    renderDialog()
    await chooseLaptops()
    fill(/^Name/, 'Laptop')
    fill(/^Serial number/, 'OLD-5001')
    fill(/^Model/, 'X1')
    fireEvent.click(form().getByRole('button', { name: 'Add asset' }))

    expect(await screen.findByText('Serial number "OLD-5001" is already used by AST-000002.')).toBeTruthy()
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('says so when there is no active one-by-one category', async () => {
    listCategories.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    renderDialog()
    expect(await screen.findByText(/There is no active one-by-one category/)).toBeTruthy()
    expect(form().getByRole('button', { name: 'Add asset' }).disabled).toBe(true)
  })
})

describe('validateAssetCreate', () => {
  const ok = { category_id: 3, name: 'L', serial_number: 'S', model: 'M', brand: '', location: '', purchase_date: '', warranty_expiry: '', cost: '' }

  it('accepts the required fields alone', () => {
    expect(validateAssetCreate(ok, TODAY)).toEqual({})
  })

  it('purchase date today or earlier, never future', () => {
    expect(validateAssetCreate({ ...ok, purchase_date: TODAY }, TODAY)).toEqual({})
    expect(validateAssetCreate({ ...ok, purchase_date: '2026-11-24' }, TODAY).purchase_date).toBe('The purchase date cannot be in the future.')
  })

  it('warranty not before the purchase date', () => {
    expect(validateAssetCreate({ ...ok, purchase_date: '2023-04-01', warranty_expiry: '2023-03-31' }, TODAY).warranty_expiry).toMatch(/Cannot be before the purchase date/)
    expect(validateAssetCreate({ ...ok, warranty_expiry: '2020-01-01' }, TODAY)).toEqual({})
  })

  it('cost 0 or more with up to 2 decimals', () => {
    for (const good of ['0', '45000', '45000.5', '45000.50']) expect(validateAssetCreate({ ...ok, cost: good }, TODAY)).toEqual({})
    for (const bad of ['-1', '1.234', 'abc', '12345678901']) expect(validateAssetCreate({ ...ok, cost: bad }, TODAY).cost).toMatch(/0 or more/)
  })
})
