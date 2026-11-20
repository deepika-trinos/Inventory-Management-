// Purchase detail page: /purchases/:purchaseId (Admin and IT Manager, Slice 3.4, PUR-09).
// Shows the vendor (with contact details), the purchase details, every line (item,
// ordered and received quantities, unit cost, line total) with the total, and for a
// received purchase the assets created and the stock movements written, plus who
// created and who received it, and when.
// Received and cancelled purchases are read-only (final, P6). A draft keeps its
// existing actions (edit, receive, cancel), which open the same boxes as the list.
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import MoveToInboxOutlined from '@mui/icons-material/MoveToInboxOutlined'
import {
  Box,
  Button,
  Divider,
  Link,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableFooter,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'

import { getErrorCode, getErrorMessage } from '../../api/errors'
import { cancelPurchase, getPurchase, movementTypeLabel, purchaseStatusLabel } from '../../api/purchases'
import ConfirmDialog from '../../components/ConfirmDialog'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatDateTime, formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'
import AssetDetailsDialog from '../assets/AssetDetailsDialog'
import PurchaseFormDialog from './PurchaseFormDialog'
import { CANCEL_PURCHASE_MESSAGE } from './PurchasesPage'
import ReceivePurchaseDialog from './ReceivePurchaseDialog'
import { quantityWithUnit, receivedMessage } from './receiveForm'

function Detail({ label, value, testId }) {
  return (
    <Box data-testid={testId}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1" component="div" sx={{ whiteSpace: 'pre-line', wordBreak: 'break-word' }}>
        {value || '—'}
      </Typography>
    </Box>
  )
}

function Section({ title, children, label }) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }} component="section" aria-label={label ?? title}>
      <Typography variant="h6" component="h2">
        {title}
      </Typography>
      <Divider sx={{ my: 1 }} />
      {children}
    </Paper>
  )
}

const headCell = { fontWeight: 600, whiteSpace: 'nowrap' }

/** "USB mouse" / "Laptops: Dell Latitude 5440" and the kind of line underneath. */
function lineItem(line) {
  if (line.line_type === 'bulk') {
    return { name: line.stock_item?.name ?? '—', kind: 'By quantity' }
  }
  return { name: line.description, kind: `One-by-one · ${line.category?.name ?? ''}` }
}

const lineQuantity = (line, quantity) =>
  line.line_type === 'bulk' ? quantityWithUnit(quantity, line.stock_item?.unit_of_measure) : String(quantity)

// What the empty "assets" / "movements" boxes say, by status.
function nothingYet(status, what) {
  if (status === 'draft') return { title: `No ${what} yet`, message: `${what === 'assets' ? 'Assets are created' : 'Stock is added'} when the purchase is received.` }
  if (status === 'cancelled') return { title: `No ${what}`, message: 'A cancelled purchase never changes stock or creates assets.' }
  return {
    title: `No ${what}`,
    message: what === 'assets' ? 'No one-by-one items were received on this purchase.' : 'No by-quantity items were received on this purchase.',
  }
}

export default function PurchaseDetailPage() {
  const { purchaseId } = useParams()
  const notify = useNotify()
  const [purchase, setPurchase] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(null) // 'edit' | 'receive' | 'cancel'
  const [viewAsset, setViewAsset] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getPurchase(purchaseId)
      .then(setPurchase)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [purchaseId])

  useEffect(load, [load])

  const backLink = (
    <Button component={RouterLink} to="/purchases" startIcon={<ArrowBackOutlined />} sx={{ alignSelf: 'flex-start' }}>
      All purchases
    </Button>
  )

  if (loading && !purchase) return <LoadingState message="Loading purchase…" />
  if (error) {
    const notFound = getErrorCode(error) === 'purchase_not_found' || error?.response?.status === 422
    return (
      <Stack spacing={2}>
        {backLink}
        {notFound ? (
          <EmptyState title="Purchase not found" message="It may have been typed wrongly in the address." />
        ) : (
          <ErrorMessage error={error} onRetry={load} />
        )}
      </Stack>
    )
  }

  const p = purchase
  const draft = p.status === 'draft'
  const vendor = p.vendor
  const assets = p.lines.flatMap((line, i) => line.assets.map((asset) => ({ ...asset, lineNumber: i + 1, line })))
  const movements = p.lines.flatMap((line, i) => line.stock_movements.map((m) => ({ ...m, lineNumber: i + 1, line })))

  const close = () => setDialog(null)
  const afterChange = () => {
    close()
    load()
  }

  const doCancel = async () => {
    try {
      await cancelPurchase(p.id)
      notify.success(`${p.purchase_number} cancelled.`)
      afterChange()
    } catch (err) {
      notify.error(getErrorMessage(err))
    }
  }

  let receivedBy = null
  if (p.status === 'received') {
    receivedBy = p.received_by ? `${p.received_by.email} · ${formatDateTime(p.received_at)}` : 'Not recorded'
  }

  return (
    <Stack spacing={2}>
      {backLink}

      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <Typography variant="h5" component="h1">
            Purchase {p.purchase_number}
          </Typography>
          <StatusBadge status={purchaseStatusLabel(p.status)} />
        </Stack>
        {draft ? (
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button variant="outlined" startIcon={<EditOutlined />} onClick={() => setDialog('edit')}>
              Edit
            </Button>
            <Button variant="contained" startIcon={<MoveToInboxOutlined />} onClick={() => setDialog('receive')}>
              Receive…
            </Button>
            <Button variant="outlined" color="error" startIcon={<BlockOutlined />} onClick={() => setDialog('cancel')}>
              Cancel purchase
            </Button>
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {p.status === 'received' ? 'Received purchases are final.' : 'Cancelled purchases are final.'} Read-only.
          </Typography>
        )}
      </Stack>

      <Section title="Details">
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' } }}>
          <Detail
            label="Vendor"
            testId="purchase-vendor"
            value={
              <>
                <Link component={RouterLink} to={`/vendors/${vendor.id}`} underline="hover">
                  {vendor.name}
                </Link>
                {vendor.status !== 'active' ? ' (inactive)' : ''}
              </>
            }
          />
          <Detail label="Contact person" value={vendor.contact_person} />
          <Detail label="Vendor email / phone" value={[vendor.email, vendor.phone].filter(Boolean).join(' · ')} />
          <Detail label="Vendor address" value={vendor.address} />
          <Detail label="Invoice / reference no." value={p.reference_number} />
          <Detail label="Purchase date" value={formatPlainDate(p.purchase_date)} />
          <Detail label="Received date" value={p.received_date ? formatPlainDate(p.received_date) : null} />
          <Detail label="Created by" testId="purchase-created-by" value={`${p.created_by.email} · ${formatDateTime(p.created_at)}`} />
          <Detail label="Received by" testId="purchase-received-by" value={receivedBy} />
          <Detail label="Notes" value={p.notes} />
        </Box>
      </Section>

      <Section title="Lines">
        <TableContainer sx={{ overflowX: 'auto' }}>
          <Table size="small" aria-label="Purchase lines">
            <TableHead>
              <TableRow>
                <TableCell sx={headCell}>#</TableCell>
                <TableCell sx={headCell}>Item</TableCell>
                <TableCell sx={headCell} align="right">Ordered</TableCell>
                <TableCell sx={headCell} align="right">Received</TableCell>
                <TableCell sx={headCell} align="right">Unit cost</TableCell>
                <TableCell sx={headCell} align="right">Line total</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {p.lines.map((line, i) => {
                const item = lineItem(line)
                return (
                  <TableRow key={line.id}>
                    <TableCell>{i + 1}</TableCell>
                    <TableCell>
                      <Typography variant="body2">{item.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.kind}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">{lineQuantity(line, line.quantity)}</TableCell>
                    <TableCell align="right">
                      {line.received_quantity === null || line.received_quantity === undefined ? '—' : lineQuantity(line, line.received_quantity)}
                    </TableCell>
                    <TableCell align="right">{formatAmount(line.unit_cost)}</TableCell>
                    <TableCell align="right">{formatAmount(line.line_total)}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colSpan={5} align="right" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  Total
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 600, color: 'text.primary' }} data-testid="purchase-total">
                  {formatAmount(p.total_amount)}
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </TableContainer>
      </Section>

      <Section title={`Assets created (${assets.length})`} label="Assets created">
        {assets.length === 0 ? (
          <EmptyState {...nothingYet(p.status, 'assets')} />
        ) : (
          <TableContainer sx={{ overflowX: 'auto' }}>
            <Table size="small" aria-label="Assets created">
              <TableHead>
                <TableRow>
                  <TableCell sx={headCell}>Asset ID</TableCell>
                  <TableCell sx={headCell}>Serial number</TableCell>
                  <TableCell sx={headCell}>From line</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {assets.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>
                      <Link component="button" type="button" underline="hover" onClick={() => setViewAsset(a.asset_code)}>
                        {a.asset_code}
                      </Link>
                    </TableCell>
                    <TableCell>{a.serial_number}</TableCell>
                    <TableCell>
                      {a.lineNumber}. {a.line.description}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Section>

      <Section title={`Stock movements (${movements.length})`} label="Stock movements">
        {movements.length === 0 ? (
          <EmptyState {...nothingYet(p.status, 'stock movements')} />
        ) : (
          <TableContainer sx={{ overflowX: 'auto' }}>
            <Table size="small" aria-label="Stock movements">
              <TableHead>
                <TableRow>
                  <TableCell sx={headCell}>Stock item</TableCell>
                  <TableCell sx={headCell}>Type</TableCell>
                  <TableCell sx={headCell} align="right">Quantity</TableCell>
                  <TableCell sx={headCell} align="right">Balance after</TableCell>
                  <TableCell sx={headCell}>Date</TableCell>
                  <TableCell sx={headCell}>Saved</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {movements.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{m.line.stock_item?.name}</TableCell>
                    <TableCell>{movementTypeLabel(m.movement_type)}</TableCell>
                    <TableCell align="right">+{quantityWithUnit(m.quantity, m.line.stock_item?.unit_of_measure)}</TableCell>
                    <TableCell align="right">{quantityWithUnit(m.balance_after, m.line.stock_item?.unit_of_measure)}</TableCell>
                    <TableCell>{formatPlainDate(m.movement_date)}</TableCell>
                    <TableCell>
                      {formatDateTime(m.created_at)} · {m.created_by.email}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Section>

      {dialog === 'edit' ? (
        <PurchaseFormDialog
          open
          purchaseId={p.id}
          onClose={close}
          onSaved={(saved) => {
            notify.success(`${saved.purchase_number} saved.`)
            afterChange()
          }}
          onReceive={() => setDialog('receive')}
        />
      ) : null}

      {dialog === 'receive' ? (
        <ReceivePurchaseDialog
          open
          purchaseId={p.id}
          onClose={close}
          onReceived={(saved) => {
            notify.success(receivedMessage(saved))
            afterChange()
          }}
        />
      ) : null}

      <ConfirmDialog
        open={dialog === 'cancel'}
        title={`Cancel purchase ${p.purchase_number}?`}
        message={CANCEL_PURCHASE_MESSAGE}
        confirmLabel="Cancel purchase"
        cancelLabel="Keep draft"
        destructive
        onCancel={close}
        onConfirm={doCancel}
      />

      {viewAsset ? <AssetDetailsDialog open assetRef={viewAsset} onClose={() => setViewAsset(null)} /> : null}
    </Stack>
  )
}
