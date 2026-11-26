// Asset page: /assets/:assetId (Admin and IT Manager, Slice 4.1, AST-02, AST-05).
// :assetId is the asset ID (AST-000007) or the id (7).
// Shows the asset's details, where it came from (its purchase, with links to the
// purchase and the vendor; "entered by hand" when there is none), who created it and
// when, and its full history: every audit log entry about the asset, newest first,
// paged on the server. Later slices add entries there automatically (5.x assign /
// return, 6.x maintenance).
// Slice 4.2 (AST-04, AST-07): an Edit button (allowed details only, owner's answer A2)
// and a Retire… button (only Available or Damaged, required reason, cannot be undone,
// A3). A retired asset shows who retired it, when and why, and has no Edit or Retire.
// History lists each edit (old -> new value) and the retirement with its reason.
// Slice 4.5: an asset entered by hand shows "Entered by hand" next to its status and in
// its Purchase section (with its purchase date and cost, if typed).
// Slice 5.1 (ASN-01 to ASN-04): an "Assign…" button (only for Available assets; greyed
// out with the reason otherwise) opening a form and a confirm box; an "Assigned to"
// section with the current holder; history shows "Assigned to Asha Kumar (EMP-001)".
// Slice 5.2 (ASN-05, ASN-06, BR-04): a "Return…" button (only while Assigned) opening one
// form for the return and the inspection (Q5, N4), then a confirm box; afterwards the page
// shows the new status and no holder; history shows "Returned by Asha Kumar — Damaged: …".
// Slice 6.1 (MNT-02, MNT-03; owner's answers Q9, Q10, O1, O2, O10, O12): a "Report a problem…"
// button (not on Retired assets; greyed out while a request is open, O2) opening a form with the
// issue, optional priority and reported date (no confirm box, O10). The asset keeps its status
// (Q9). A "Maintenance requests" section lists the asset's requests; history shows
// "Problem reported · MNT-000001 · High · Screen flickers".
// Slice 6.2 (MNT-04 to MNT-07; S13, S14): request numbers link to the request page; History shows
// "Work started", "Repair completed", "Request cancelled" and "Request edited" rows; Retire… is greyed
// out while a request is open ("Cancel or finish MNT-… first.").
// Slice 6.3 (MNT-07): while a request awaits inspection, a note "Awaiting inspection after MNT-…" with an
// Inspect… button (the same form as on the request page); Assign… and Report a problem… are greyed out
// with that reason. The requests table shows "Awaiting inspection" / "Inspected: …"; History shows
// "Inspected" rows (and "Retired" when the outcome was Retired).
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import AssignmentReturnOutlined from '@mui/icons-material/AssignmentReturnOutlined'
import BuildOutlined from '@mui/icons-material/BuildOutlined'
import BlockOutlined from '@mui/icons-material/BlockOutlined'
import EditOutlined from '@mui/icons-material/EditOutlined'
import PersonAddAltOutlined from '@mui/icons-material/PersonAddAltOutlined'
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Link,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material'

import {
  assetStatusLabel,
  assignBlockedReason,
  getAsset,
  getAssetHistory,
  historyActionLabel,
  RETIRABLE_STATUSES,
} from '../../api/assets'
import { getErrorCode } from '../../api/errors'
import {
  getAssetRequests,
  INSPECTION_OUTCOME_LABELS,
  inspectionLabel,
  isOpenStatus,
  maintenanceStatusLabel,
  priorityLabel,
  reporterLabel,
  requestPath,
} from '../../api/maintenance'
import DataTable from '../../components/DataTable'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { formatDateTime, formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'
import { useNotify } from '../../context/NotificationContext'
import AssetAssignDialog, { employeeName } from './AssetAssignDialog'
import AssetEditDialog from './AssetEditDialog'
import AssetRetireDialog from './AssetRetireDialog'
import AssetReturnDialog from './AssetReturnDialog'
import { maintenanceActionLabel, maintenanceHistoryNote } from '../maintenance/maintenanceHistory'
import InspectDialog from '../maintenance/InspectDialog'
import ReportProblemDialog from '../maintenance/ReportProblemDialog'

function Detail({ label, value, testId }) {
  return (
    <Box data-testid={testId}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1" component="div" sx={{ wordBreak: 'break-word' }}>
        {value || '—'}
      </Typography>
    </Box>
  )
}

function Section({ title, children }) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }} component="section" aria-label={title}>
      <Typography variant="h6" component="h2">
        {title}
      </Typography>
      <Divider sx={{ my: 1 }} />
      {children}
    </Paper>
  )
}

const grid = { display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' } }

// How each edited field is named in the history.
const FIELD_LABELS = {
  name: 'Name',
  brand: 'Brand',
  model: 'Model',
  serial_number: 'Serial number',
  location: 'Location',
  warranty_expiry: 'Warranty expiry',
  category: 'Category',
  purchase_date: 'Purchase date',
  cost: 'Cost',
}

function shownValue(field, value) {
  if (value === null || value === undefined || value === '') return '(empty)'
  if (field === 'warranty_expiry' || field === 'purchase_date') return formatPlainDate(value)
  if (field === 'cost') return formatAmount(value)
  return value
}

// A short note under each history entry, from what the audit log recorded.
export function historyNote(entry) {
  const after = entry.after ?? {}
  const before = entry.before ?? {}
  if (entry.action === 'asset.created') {
    return after.purchase_number ? `Received on purchase ${after.purchase_number}` : 'Entered by hand'
  }
  if (entry.action === 'assignment.returned') {
    // e.g. "Returned by Asha Kumar — Damaged: screen cracked"
    const who = after.employee_name ?? 'an employee'
    const outcome = assetStatusLabel(after.inspection_outcome ?? after.status)
    return `Returned by ${who} — ${outcome}${after.condition_notes ? `: ${after.condition_notes}` : ''}`
  }
  if (entry.action === 'assignment.created') {
    // e.g. "Assigned to Asha Kumar (EMP-001) · from 23 Nov 2026 · expected back 23 Dec 2026"
    const who = after.employee_name ? `${after.employee_name} (${after.employee_code})` : 'an employee'
    return [
      `Assigned to ${who}`,
      after.assignment_date ? `from ${formatPlainDate(after.assignment_date)}` : null,
      after.expected_return_date ? `expected back ${formatPlainDate(after.expected_return_date)}` : null,
    ]
      .filter(Boolean)
      .join(' · ')
  }
  const maintenance = maintenanceHistoryNote(entry) // Slice 6.1 / 6.2
  if (maintenance !== null) return maintenance
  if (entry.action === 'asset.updated') {
    // e.g. "Location: Bangalore Floor 2 → Chennai; Serial number: DL-1O01 → DL-1001"
    // category_id is shown by name (the "category" entry), not by number.
    return Object.keys(after)
      .filter((field) => field !== 'category_id')
      .map((field) => `${FIELD_LABELS[field] ?? field}: ${shownValue(field, before[field])} → ${shownValue(field, after[field])}`)
      .join('; ')
  }
  if (after.reason) return `Reason: ${after.reason}`
  return ''
}

const HISTORY_COLUMNS = [
  { field: 'created_at', label: 'When', render: (e) => formatDateTime(e.created_at) },
  { field: 'action', label: 'What', render: (e) => maintenanceActionLabel(e) ?? historyActionLabel(e.action) },
  { field: 'actor', label: 'By', render: (e) => e.actor?.email ?? 'System' },
  { field: 'note', label: 'Details', render: (e) => historyNote(e) || '—' },
]

// The asset's maintenance requests, newest first (Slice 6.1, O12).
function MaintenanceRequests({ requests, error, onRetry }) {
  if (error) return <ErrorMessage error={error} onRetry={onRetry} />
  if (!requests) return <LoadingState message="Loading maintenance requests…" />
  if (requests.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No maintenance requests.
      </Typography>
    )
  }
  return (
    <TableContainer>
      <Table size="small" aria-label="Maintenance requests">
        <TableHead>
          <TableRow>
            {['Request', 'Reported on', 'Reported by', 'Priority', 'Status', 'Problem'].map((label) => (
              <TableCell key={label}>{label}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {requests.map((r) => (
            <TableRow key={r.id} data-testid="maintenance-request-row">
              <TableCell>
                <Link component={RouterLink} to={requestPath(r)} underline="hover">
                  {r.request_number}
                </Link>
              </TableCell>
              <TableCell>{formatPlainDate(r.reported_date)}</TableCell>
              <TableCell>{reporterLabel(r.reported_by)}</TableCell>
              <TableCell>{r.priority ? priorityLabel(r.priority) : '—'}</TableCell>
              <TableCell>
                <StatusBadge status={maintenanceStatusLabel(r.status)} />
                {inspectionLabel(r) ? (
                  <Typography
                    variant="caption"
                    component="div"
                    color={r.awaiting_inspection ? 'warning.main' : 'text.secondary'}
                    data-testid="request-inspection"
                  >
                    {inspectionLabel(r)}
                  </Typography>
                ) : null}
              </TableCell>
              <TableCell sx={{ wordBreak: 'break-word' }}>{r.issue_description}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function AssetHistory({ assetRef, reloadKey }) {
  const fetchRows = useCallback((args) => getAssetHistory(assetRef, args), [assetRef])
  return (
    <DataTable
      columns={HISTORY_COLUMNS}
      fetchRows={fetchRows}
      reloadKey={reloadKey}
      searchable={false}
      emptyTitle="No history recorded"
      emptyMessage="Changes to this asset will be listed here."
      pageSizeOptions={[5, 10, 20]}
    />
  )
}

export default function AssetDetailPage() {
  const { assetId } = useParams()
  const [asset, setAsset] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState(null) // 'edit' | 'retire' | 'assign' | 'return' | 'report' | 'inspect'
  const [historyKey, setHistoryKey] = useState(0)
  const [requests, setRequests] = useState(null) // Slice 6.1
  const [requestsError, setRequestsError] = useState(null)
  const notify = useNotify()

  const loadRequests = useCallback(() => {
    setRequestsError(null)
    getAssetRequests(assetId).then(setRequests).catch(setRequestsError)
  }, [assetId])

  useEffect(loadRequests, [loadRequests])

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    getAsset(assetId)
      .then(setAsset)
      .catch(setError)
      .finally(() => setLoading(false))
  }, [assetId])

  useEffect(load, [load])

  const backLink = (
    <Button component={RouterLink} to="/assets" startIcon={<ArrowBackOutlined />} sx={{ alignSelf: 'flex-start' }}>
      All assets
    </Button>
  )

  if (loading && !asset) return <LoadingState message="Loading asset…" />
  if (error) {
    const notFound = getErrorCode(error) === 'asset_not_found' || error?.response?.status === 422
    return (
      <Stack spacing={2}>
        {backLink}
        {notFound ? (
          <EmptyState title="Asset not found" message="It may have been typed wrongly in the address." />
        ) : (
          <ErrorMessage error={error} onRetry={load} />
        )}
      </Stack>
    )
  }

  const a = asset
  const purchase = a.purchase
  const retired = a.status === 'retired'
  const canRetire = RETIRABLE_STATUSES.includes(a.status)
  const holder = a.current_assignment
  const openRequest = (requests ?? []).find((r) => isOpenStatus(r.status))
  const waiting = (requests ?? []).find((r) => r.awaiting_inspection) // Slice 6.3
  const assignBlocked = waiting ? `Awaiting inspection (${waiting.request_number}).` : assignBlockedReason(a.status)
  let reportBlocked = ''
  if (openRequest) reportBlocked = `${openRequest.request_number} is already open.`
  else if (waiting) reportBlocked = `${waiting.request_number} is awaiting inspection. Inspect the asset first.`
  // S14: no retiring while a request is open.
  let retireBlocked = canRetire ? '' : 'Only Available or Damaged assets can be retired.'
  if (!retireBlocked && openRequest) retireBlocked = `Cancel or finish ${openRequest.request_number} first.`

  // After a save: show the new values and the new history entry.
  const afterChange = (saved, message) => {
    setAsset(saved)
    setDialog(null)
    setHistoryKey((n) => n + 1)
    notify.success(message)
  }

  let retiredBy = null
  if (retired) {
    retiredBy = a.retired_by ? `${a.retired_by.email} · ${formatDateTime(a.retired_at)}` : 'Not recorded'
  }

  return (
    <Stack spacing={2}>
      {backLink}

      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
          <Typography variant="h5" component="h1">
            Asset {a.asset_code}
          </Typography>
          <StatusBadge status={assetStatusLabel(a.status)} />
          {purchase ? null : <Chip size="small" variant="outlined" label="Entered by hand" data-testid="asset-origin" />}
        </Stack>
        {retired ? (
          <Typography variant="body2" color="text.secondary">
            Retired assets are final. Read-only.
          </Typography>
        ) : (
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Tooltip title={assignBlocked}>
              <span>
                <Button
                  variant="contained"
                  startIcon={<PersonAddAltOutlined />}
                  disabled={Boolean(assignBlocked)}
                  onClick={() => setDialog('assign')}
                >
                  Assign…
                </Button>
              </span>
            </Tooltip>
            {holder ? (
              <Button variant="contained" startIcon={<AssignmentReturnOutlined />} onClick={() => setDialog('return')}>
                Return…
              </Button>
            ) : null}
            {waiting ? (
              <Button variant="contained" onClick={() => setDialog('inspect')}>
                Inspect…
              </Button>
            ) : null}
            <Tooltip title={reportBlocked}>
              <span>
                <Button
                  variant="outlined"
                  startIcon={<BuildOutlined />}
                  disabled={Boolean(reportBlocked) || requests === null}
                  onClick={() => setDialog('report')}
                >
                  Report a problem…
                </Button>
              </span>
            </Tooltip>
            <Button variant="outlined" startIcon={<EditOutlined />} onClick={() => setDialog('edit')}>
              Edit
            </Button>
            <Tooltip title={retireBlocked}>
              <span>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<BlockOutlined />}
                  disabled={Boolean(retireBlocked)}
                  onClick={() => setDialog('retire')}
                >
                  Retire…
                </Button>
              </span>
            </Tooltip>
          </Stack>
        )}
      </Stack>

      {waiting ? (
        <Alert severity="warning" data-testid="awaiting-inspection">
          Awaiting inspection after{' '}
          <Link component={RouterLink} to={requestPath(waiting)} underline="hover">
            {waiting.request_number}
          </Link>
          . {a.asset_code} stays Under Maintenance until it is inspected.
        </Alert>
      ) : null}

      <Section title="Details">
        <Box sx={grid}>
          <Detail label="Name" value={a.name} />
          <Detail label="Category" value={`${a.category.name}${a.category.status !== 'active' ? ' (inactive)' : ''}`} />
          <Detail label="Serial number" value={a.serial_number} />
          <Detail label="Model" value={a.model} />
          <Detail label="Brand" value={a.brand} />
          <Detail label="Location" value={a.location} />
          <Detail label="Warranty expiry" value={a.warranty_expiry ? formatPlainDate(a.warranty_expiry) : null} />
          <Detail label="Status" value={assetStatusLabel(a.status)} />
          <Detail label="Created by" testId="asset-created-by" value={`${a.created_by.email} · ${formatDateTime(a.created_at)}`} />
          {retired ? <Detail label="Retired by" testId="asset-retired-by" value={retiredBy} /> : null}
          {retired ? <Detail label="Reason for retiring" testId="asset-retire-reason" value={a.retire_reason} /> : null}
        </Box>
      </Section>

      {holder ? (
        <Section title="Assigned to">
          <Box sx={grid}>
            <Detail
              label="Employee"
              testId="asset-assigned-to"
              value={`${employeeName(holder.employee)}${holder.employee.status !== 'active' ? ' (inactive)' : ''}`}
            />
            <Detail label="Assignment date" testId="asset-assignment-date" value={formatPlainDate(holder.assignment_date)} />
            <Detail
              label="Expected return"
              testId="asset-expected-return"
              value={
                <>
                  {holder.expected_return_date ? formatPlainDate(holder.expected_return_date) : 'Not set'}{' '}
                  {holder.is_overdue ? <Chip size="small" color="error" label="Overdue" data-testid="asset-overdue" /> : null}
                </>
              }
            />
            <Detail label="Assigned by" value={`${holder.assigned_by.email} · ${formatDateTime(holder.created_at)}`} />
          </Box>
        </Section>
      ) : null}

      <Section title="Purchase">
        {purchase ? (
          <Box sx={grid}>
            <Detail
              label="Purchase"
              testId="asset-purchase"
              value={
                <Link component={RouterLink} to={`/purchases/${purchase.purchase_id}`} underline="hover">
                  {purchase.purchase_number}
                </Link>
              }
            />
            <Detail
              label="Vendor"
              value={
                <Link component={RouterLink} to={`/vendors/${purchase.vendor_id}`} underline="hover">
                  {purchase.vendor}
                </Link>
              }
            />
            <Detail label="Invoice / reference no." value={purchase.reference_number} />
            <Detail label="Purchase date" value={a.purchase_date ? formatPlainDate(a.purchase_date) : null} />
            <Detail label="Cost" value={a.cost ? formatAmount(a.cost) : null} />
          </Box>
        ) : (
          <Box sx={grid}>
            <Detail
              label="Origin"
              testId="asset-purchase"
              value="Entered by hand (existing equipment, no purchase or vendor)"
            />
            <Detail label="Purchase date" value={a.purchase_date ? formatPlainDate(a.purchase_date) : null} />
            <Detail label="Cost" value={a.cost ? formatAmount(a.cost) : null} />
          </Box>
        )}
      </Section>

      <Section title="Maintenance requests">
        <MaintenanceRequests requests={requests} error={requestsError} onRetry={loadRequests} />
      </Section>

      <Section title="History">
        <AssetHistory assetRef={a.asset_code} reloadKey={historyKey} />
      </Section>

      {dialog === 'edit' ? (
        <AssetEditDialog
          open
          asset={a}
          onClose={() => setDialog(null)}
          onSaved={(saved) => afterChange(saved, `${saved.asset_code} saved.`)}
        />
      ) : null}

      {dialog === 'report' ? (
        <ReportProblemDialog
          open
          staff
          asset={a}
          onClose={() => setDialog(null)}
          onReported={(saved) => {
            setDialog(null)
            setHistoryKey((n) => n + 1)
            loadRequests()
            notify.success(`${saved.request_number} reported.`)
          }}
        />
      ) : null}

      {dialog === 'inspect' && waiting ? (
        <InspectDialog
          request={waiting}
          onClose={() => setDialog(null)}
          onSaved={(saved) => {
            setDialog(null)
            setHistoryKey((n) => n + 1)
            load()
            loadRequests()
            notify.success(`${saved.asset.asset_code} inspected. Status: ${INSPECTION_OUTCOME_LABELS[saved.inspection_outcome]}.`)
          }}
        />
      ) : null}

      {dialog === 'return' ? (
        <AssetReturnDialog
          open
          asset={a}
          onClose={() => setDialog(null)}
          onReturned={(saved) => afterChange(saved, `${saved.asset_code} returned. Status: ${assetStatusLabel(saved.status)}.`)}
        />
      ) : null}

      {dialog === 'assign' ? (
        <AssetAssignDialog
          open
          asset={a}
          onClose={() => setDialog(null)}
          onAssigned={(saved) =>
            afterChange(saved, `${saved.asset_code} assigned to ${employeeName(saved.current_assignment?.employee)}.`)
          }
        />
      ) : null}

      {dialog === 'retire' ? (
        <AssetRetireDialog
          open
          asset={a}
          onClose={() => setDialog(null)}
          onRetired={(saved) => afterChange(saved, `${saved.asset_code} retired.`)}
        />
      ) : null}
    </Stack>
  )
}
