// Tests for the Edit asset dialog (Slice 4.2, owner's answer A2): only the editable fields
// are inputs; asset ID, status, category and purchase facts are shown read-only; the
// screen checks (required, limits, warranty not before the purchase date); what is sent;
// server problems shown under the right field. The server is replaced by stand-ins.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { updateAsset } from '../../api/assets'
import { listCategories } from '../../api/categories'
import AssetEditDialog, { validateAssetEdit } from './AssetEditDialog'

vi.mock('../../api/assets', async (importOriginal) => ({ ...(await importOriginal()), updateAsset: vi.fn() }))
vi.mock('../../api/categories', async (importOriginal) => ({ ...(await importOriginal()), listCategories: vi.fn() }))

const ASSET = {
  id: 1,
  asset_code: 'AST-000001',
  name: 'Laptops: Dell Latitude 5440',
  category: { id: 3, name: 'Laptops', tracking_type: 'serialized', status: 'active' },
  brand: 'Dell',
  model: 'Latitude 5440',
  serial_number: 'DL-1001',
  status: 'available',
  location: 'Bangalore Floor 2',
  warranty_expiry: '2029-11-10',
  purchase_date: '2026-11-10',
  cost: '85000.00',
  purchase: { purchase_id: 9, purchase_number: 'PUR-000009', purchase_line_id: 11, vendor_id: 4, vendor: 'Acme IT Supplies', reference_number: 'INV-2026-0042' },
}
const serverError = (code, message, status = 409) => ({ response: { status, data: { error: { code, message } } } })

let onSaved
let onClose
beforeEach(() => {
  vi.clearAllMocks()
  onSaved = vi.fn()
  onClose = vi.fn()
})

function renderDialog(asset = ASSET) {
  render(<AssetEditDialog open asset={asset} onClose={onClose} onSaved={onSaved} />)
  return within(screen.getByRole('dialog'))
}

const save = (d) => fireEvent.click(d.getByRole('button', { name: 'Save' }))

describe('AssetEditDialog', () => {
  it('has inputs only for the editable fields, filled with the current values', () => {
    const d = renderDialog()
    const inputs = d.getAllByRole('textbox').map((i) => i.getAttribute('name') ?? i.closest('.MuiFormControl-root').querySelector('label').textContent)
    expect(inputs.join(' | ')).toMatch(/Name.*Serial number.*Model.*Brand.*Location/)
    expect(d.getByLabelText(/^Name/).value).toBe('Laptops: Dell Latitude 5440')
    expect(d.getByLabelText(/Serial number/).value).toBe('DL-1001')
    expect(d.getByLabelText('Warranty expiry').value).toBe('2029-11-10')
    expect(d.queryByLabelText(/Status/)).toBeNull()
    expect(d.queryByLabelText(/Cost/)).toBeNull()
    expect(d.queryByLabelText(/Category/)).toBeNull()
  })

  it('shows asset ID, status, category, purchase, purchase date and cost read-only', () => {
    const d = renderDialog()
    const locked = within(d.getByTestId('asset-locked-fields'))
    for (const text of ['AST-000001', 'Available', 'Laptops', 'PUR-000009 · Acme IT Supplies', '10 Nov 2026']) {
      expect(locked.getByText(text)).toBeTruthy()
    }
    expect(locked.getByText(/85,000\.00/)).toBeTruthy()
  })

  it('sends trimmed values, empty optional fields as null, and reports the saved asset', async () => {
    const saved = { ...ASSET, location: null, brand: 'DELL' }
    updateAsset.mockResolvedValue(saved)
    const d = renderDialog()

    fireEvent.change(d.getByLabelText('Location'), { target: { value: '   ' } })
    fireEvent.change(d.getByLabelText('Brand'), { target: { value: '  DELL ' } })
    fireEvent.change(d.getByLabelText('Warranty expiry'), { target: { value: '' } })
    save(d)

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved))
    expect(updateAsset).toHaveBeenCalledWith('AST-000001', {
      name: 'Laptops: Dell Latitude 5440', brand: 'DELL', model: 'Latitude 5440', serial_number: 'DL-1001',
      location: null, warranty_expiry: null,
    })
  })

  it('refuses an empty name, model or serial number on screen', async () => {
    const d = renderDialog()
    fireEvent.change(d.getByLabelText(/^Name/), { target: { value: ' ' } })
    fireEvent.change(d.getByLabelText(/Serial number/), { target: { value: '' } })
    save(d)

    expect(await d.findByText('Please enter the name.')).toBeTruthy()
    expect(d.getByText('Please enter the serial number.')).toBeTruthy()
    expect(updateAsset).not.toHaveBeenCalled()
  })

  it('refuses a warranty date before the purchase date on screen', async () => {
    const d = renderDialog()
    fireEvent.change(d.getByLabelText('Warranty expiry'), { target: { value: '2019-11-10' } })
    save(d)

    expect(await d.findByText('Cannot be before the purchase date (10 Nov 2026).')).toBeTruthy()
    expect(updateAsset).not.toHaveBeenCalled()
  })

  it('shows a taken serial number under the serial field and stays open', async () => {
    updateAsset.mockRejectedValue(serverError('serial_number_taken', 'Serial number "DL-1002" is already used by another asset.'))
    const d = renderDialog()
    fireEvent.change(d.getByLabelText(/Serial number/), { target: { value: 'DL-1002' } })
    save(d)

    expect(await d.findByText('Serial number "DL-1002" is already used by another asset.')).toBeTruthy()
    expect(onSaved).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toBeTruthy()
  })

  it('shows other server errors at the top (e.g. retired meanwhile)', async () => {
    updateAsset.mockRejectedValue(serverError('asset_retired', 'AST-000001 is retired. A retired asset cannot be changed.'))
    const d = renderDialog()
    save(d)
    expect(await d.findByText('AST-000001 is retired. A retired asset cannot be changed.')).toBeTruthy()
  })

  it('validation helper: limits', () => {
    const values = { name: 'n'.repeat(201), brand: '', model: 'M', serial_number: 'S', location: 'l'.repeat(201), warranty_expiry: '' }
    expect(validateAssetEdit(values, null)).toEqual({ name: 'Use at most 200 characters.', location: 'Use at most 200 characters.' })
  })
})

// Slice 4.5 (I4): an asset entered by hand can also change category, purchase date and cost.
describe('AssetEditDialog: asset entered by hand', () => {
  const MANUAL = { ...ASSET, purchase: null, purchase_date: '2023-04-01', cost: '50000.00', warranty_expiry: '2026-04-01' }
  const DESKTOPS = { id: 5, name: 'Desktops', tracking_type: 'serialized', status: 'active' }

  beforeEach(() => {
    listCategories.mockResolvedValue({ items: [ASSET.category, DESKTOPS], total: 2, page: 1, page_size: 100 })
  })

  it('has category, purchase date and cost inputs and asks only for active one-by-one categories', async () => {
    const d = renderDialog(MANUAL)
    expect(d.getByLabelText(/^Purchase date/).value).toBe('2023-04-01')
    expect(d.getByLabelText(/^Cost/).value).toBe('50000.00')
    expect(d.getByRole('combobox', { name: /Category/ })).toBeTruthy()
    await waitFor(() => expect(listCategories).toHaveBeenCalled())
    expect(listCategories.mock.calls[0][0]).toMatchObject({ trackingType: 'serialized', status: 'active' })
    expect(within(d.getByTestId('asset-locked-fields')).getByText('None (entered by hand)')).toBeTruthy()
  })

  it('sends the new category, purchase date and cost', async () => {
    updateAsset.mockResolvedValue(MANUAL)
    const d = renderDialog(MANUAL)
    fireEvent.mouseDown(d.getByRole('combobox', { name: /Category/ }))
    fireEvent.click(await within(screen.getByRole('listbox')).findByRole('option', { name: 'Desktops' }))
    fireEvent.change(d.getByLabelText(/^Purchase date/), { target: { value: '2023-03-01' } })
    fireEvent.change(d.getByLabelText(/^Cost/), { target: { value: '45000' } })
    save(d)

    await waitFor(() => expect(onSaved).toHaveBeenCalled())
    expect(updateAsset).toHaveBeenCalledWith('AST-000001', expect.objectContaining({ category_id: 5, purchase_date: '2023-03-01', cost: '45000' }))
  })

  it('refuses a future purchase date, a bad cost and a warranty before the new purchase date', async () => {
    const d = renderDialog(MANUAL)
    fireEvent.change(d.getByLabelText(/^Purchase date/), { target: { value: '2999-01-01' } })
    fireEvent.change(d.getByLabelText(/^Cost/), { target: { value: '-3' } })
    save(d)
    expect(await screen.findByText('The purchase date cannot be in the future.')).toBeTruthy()
    expect(screen.getByText(/0 or more/)).toBeTruthy()
    expect(screen.getByText(/Cannot be before the purchase date/)).toBeTruthy()
    expect(updateAsset).not.toHaveBeenCalled()
  })

  it('a received asset never sends category, purchase date or cost', async () => {
    updateAsset.mockResolvedValue(ASSET)
    const d = renderDialog(ASSET)
    save(d)
    await waitFor(() => expect(updateAsset).toHaveBeenCalled())
    const sent = updateAsset.mock.calls[0][1]
    expect('category_id' in sent || 'purchase_date' in sent || 'cost' in sent).toBe(false)
  })
})
