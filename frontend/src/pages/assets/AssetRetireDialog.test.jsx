// Tests for the Retire asset confirm box (Slice 4.2, owner's answer A3): says it cannot
// be undone, needs a reason (up to 500 characters), sends the trimmed reason, and keeps
// the box open with the server's message when retiring is refused.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { retireAsset } from '../../api/assets'
import AssetRetireDialog from './AssetRetireDialog'

vi.mock('../../api/assets', async (importOriginal) => ({ ...(await importOriginal()), retireAsset: vi.fn() }))

const ASSET = { id: 1, asset_code: 'AST-000001', status: 'available' }

let onRetired
beforeEach(() => {
  vi.clearAllMocks()
  onRetired = vi.fn()
})

function renderDialog() {
  render(<AssetRetireDialog open asset={ASSET} onClose={vi.fn()} onRetired={onRetired} />)
  return within(screen.getByRole('dialog'))
}

const reasonBox = (d) => d.getByLabelText(/Reason for retiring/)
const retireButton = (d) => d.getByRole('button', { name: 'Retire asset' })

describe('AssetRetireDialog', () => {
  it('says retiring cannot be undone', () => {
    const d = renderDialog()
    expect(d.getByRole('heading', { name: 'Retire AST-000001?' })).toBeTruthy()
    expect(d.getByText(/permanent and cannot be undone/)).toBeTruthy()
  })

  it('keeps Retire off until a reason is typed (spaces do not count)', () => {
    const d = renderDialog()
    expect(retireButton(d).disabled).toBe(true)
    fireEvent.change(reasonBox(d), { target: { value: '   ' } })
    expect(retireButton(d).disabled).toBe(true)
    fireEvent.change(reasonBox(d), { target: { value: 'Beyond repair' } })
    expect(retireButton(d).disabled).toBe(false)
  })

  it('refuses a reason longer than 500 characters', () => {
    const d = renderDialog()
    fireEvent.change(reasonBox(d), { target: { value: 'r'.repeat(501) } })
    expect(d.getByText('Use at most 500 characters.')).toBeTruthy()
    expect(retireButton(d).disabled).toBe(true)
  })

  it('sends the trimmed reason and reports the retired asset', async () => {
    const saved = { ...ASSET, status: 'retired', retire_reason: 'Beyond repair' }
    retireAsset.mockResolvedValue(saved)
    const d = renderDialog()

    fireEvent.change(reasonBox(d), { target: { value: '  Beyond repair  ' } })
    fireEvent.click(retireButton(d))

    await waitFor(() => expect(onRetired).toHaveBeenCalledWith(saved))
    expect(retireAsset).toHaveBeenCalledWith('AST-000001', 'Beyond repair')
  })

  it("shows the server's refusal and stays open", async () => {
    retireAsset.mockRejectedValue({
      response: { status: 409, data: { error: { code: 'asset_not_retirable', message: 'AST-000001 is Assigned. Only Available or Damaged assets can be retired. Return it first.' } } },
    })
    const d = renderDialog()
    fireEvent.change(reasonBox(d), { target: { value: 'Lost' } })
    fireEvent.click(retireButton(d))

    expect(await d.findByText(/Only Available or Damaged assets can be retired/)).toBeTruthy()
    expect(onRetired).not.toHaveBeenCalled()
    expect(screen.getByRole('dialog')).toBeTruthy()
  })
})
