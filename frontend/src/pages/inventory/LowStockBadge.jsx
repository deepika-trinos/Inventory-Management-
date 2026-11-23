// "Low stock" label (Slice 4.3, INV-06): shown on active stock items whose quantity on
// hand is at or below their reorder threshold (decisions B37, G1). The server decides
// (low_stock in every stock item it returns); this only draws it.
import { Chip, Tooltip } from '@mui/material'

export default function LowStockBadge({ size = 'small' }) {
  return (
    <Tooltip title="At or below the reorder threshold">
      <Chip label="Low stock" color="warning" variant="outlined" size={size} />
    </Tooltip>
  )
}
