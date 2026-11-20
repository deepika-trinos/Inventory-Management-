// The purchase history columns (Slice 3.4, PUR-09 / VEN-04), shared by the Purchases
// page and a vendor's purchase history so both show the same fields the same way:
// purchase no. (opens the detail page), vendor, invoice / reference, purchase date,
// received date, number of lines, total (₹) and status.
import { Link as RouterLink } from 'react-router'
import { Link, Typography } from '@mui/material'

import { purchaseStatusLabel } from '../../api/purchases'
import StatusBadge from '../../components/StatusBadge'
import { formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'

const dash = (
  <Typography variant="body2" color="text.secondary" component="span">
    —
  </Typography>
)

export const purchasePath = (purchase) => `/purchases/${purchase.id}`

/** showVendor: false on a vendor's own page (every row is that vendor). */
export function purchaseHistoryColumns({ showVendor = true } = {}) {
  return [
    {
      field: 'purchase_number',
      label: 'Purchase no.',
      sortable: true,
      render: (p) => (
        <Link
          component={RouterLink}
          to={purchasePath(p)}
          underline="hover"
          onClick={(e) => e.stopPropagation()} // the row may open it too; open it once
        >
          {p.purchase_number}
        </Link>
      ),
    },
    ...(showVendor ? [{ field: 'vendor', label: 'Vendor', sortable: true, render: (p) => p.vendor.name }] : []),
    { field: 'reference_number', label: 'Invoice / ref.', sortable: true },
    { field: 'purchase_date', label: 'Purchase date', sortable: true, render: (p) => formatPlainDate(p.purchase_date) },
    {
      field: 'received_date',
      label: 'Received',
      sortable: true,
      render: (p) => (p.received_date ? formatPlainDate(p.received_date) : dash),
    },
    { field: 'line_count', label: 'Lines', align: 'right' },
    { field: 'total_amount', label: 'Total', align: 'right', render: (p) => formatAmount(p.total_amount) },
    {
      field: 'status',
      label: 'Status',
      sortable: true,
      render: (p) => <StatusBadge status={purchaseStatusLabel(p.status)} />,
    },
  ]
}
