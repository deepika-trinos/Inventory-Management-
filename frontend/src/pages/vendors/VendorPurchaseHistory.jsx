// A vendor's purchase history (Slice 3.4, VEN-04), on the vendor detail page /vendors/:id.
// Every purchase from this vendor (draft, received and cancelled), newest purchase date
// first (D2), paged on the server. Inactive vendors still show their history.
// Clicking a row (or its purchase number) opens the purchase detail page.
import { useCallback } from 'react'
import { useNavigate } from 'react-router'
import { Divider, Paper, Typography } from '@mui/material'

import { listPurchases } from '../../api/purchases'
import DataTable from '../../components/DataTable'
import { purchaseHistoryColumns, purchasePath } from '../purchases/purchaseColumns'

const COLUMNS = purchaseHistoryColumns({ showVendor: false })

export default function VendorPurchaseHistory({ vendorId }) {
  const navigate = useNavigate()
  const fetchRows = useCallback((args) => listPurchases({ ...args, vendorId }), [vendorId])

  return (
    <Paper variant="outlined" sx={{ p: 2 }} data-testid="vendor-purchase-history" component="section" aria-label="Purchase history">
      <Typography variant="h6" component="h2">
        Purchase history
      </Typography>
      <Divider sx={{ my: 1 }} />
      <DataTable
        columns={COLUMNS}
        fetchRows={fetchRows}
        defaultSort="-purchase_date"
        searchPlaceholder="Search reference or purchase no."
        emptyTitle="No purchases from this vendor yet"
        emptyMessage="Purchases created on the Purchases page appear here."
        onRowClick={(p) => navigate(purchasePath(p))}
        rowLabel={(p) => `Open ${p.purchase_number}`}
        pageSizeOptions={[5, 10, 20]}
      />
    </Paper>
  )
}
