// Calls to the asset endpoints (/api/v1/assets, Slice 3.2). Admin and IT Manager only.
// Only "get one asset" exists for now; the asset register (list, search) is Slice 4.1.
import apiClient from './client'

const BASE = '/api/v1/assets'

// The server stores statuses in lower case (PRD 8.1); the screen shows these labels.
export const ASSET_STATUS_LABELS = {
  available: 'Available',
  assigned: 'Assigned',
  under_maintenance: 'Under Maintenance',
  damaged: 'Damaged',
  retired: 'Retired',
}

export function assetStatusLabel(value) {
  return ASSET_STATUS_LABELS[value] ?? value
}

// ref: the asset's id (7) or asset ID ("AST-000007").
export async function getAsset(ref) {
  const { data } = await apiClient.get(`${BASE}/${encodeURIComponent(ref)}`)
  return data
}
