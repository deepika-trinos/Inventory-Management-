// Maintenance page: /maintenance (Admin and IT Manager, Slice 6.1: MNT-02, MNT-03; owner's answer O12).
// Every maintenance request, newest first: number, asset, issue, priority, status, reported date and
// who reported it (an Employee's own reports included). Search, status filter, paging, sorted on the
// server. No "new request" button: staff report a problem from the asset page. A row opens the
// request page (Slice 6.2; in 6.1 it opened the asset page). Slice 6.3: an "Awaiting inspection" filter,
// and the status shows "Awaiting inspection" / "Inspected: …" underneath.
import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router'
import { Button, MenuItem, Stack, TextField, Typography } from '@mui/material'

import {
  listRequests,
  AWAITING_INSPECTION_FILTER,
  inspectionLabel,
  MAINTENANCE_STATUS_LABELS,
  maintenanceStatusLabel,
  priorityLabel,
  reporterLabel,
  requestPath,
} from '../../api/maintenance'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'
import { formatPlainDate } from '../../utils/dates'

const dash = '—'

// The status, with "Awaiting inspection" / "Inspected: …" underneath when there is one (Slice 6.3).
function RequestStatus({ request }) {
  const inspection = inspectionLabel(request)
  return (
    <Stack spacing={0.5} sx={{ alignItems: 'flex-start' }}>
      <StatusBadge status={maintenanceStatusLabel(request.status)} />
      {inspection ? (
        <Typography variant="caption" color={request.awaiting_inspection ? 'warning.main' : 'text.secondary'}>
          {inspection}
        </Typography>
      ) : null}
    </Stack>
  )
}

const COLUMNS = [
  { field: 'request_number', label: 'Request', sortable: true },
  { field: 'asset_code', label: 'Asset', sortable: true, render: (r) => `${r.asset.asset_code} · ${r.asset.name}` },
  { field: 'issue', label: 'Problem', render: (r) => r.issue_description },
  { field: 'priority', label: 'Priority', sortable: true, render: (r) => (r.priority ? priorityLabel(r.priority) : dash) },
  { field: 'status', label: 'Status', sortable: true, render: (r) => <RequestStatus request={r} /> },
  { field: 'reported_date', label: 'Reported on', sortable: true, render: (r) => formatPlainDate(r.reported_date) },
  { field: 'reported_by', label: 'Reported by', render: (r) => reporterLabel(r.reported_by) },
]

export default function MaintenancePage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('')
  const filtersActive = Boolean(statusFilter)
  const clearFilters = () => setStatusFilter('')

  const fetchRows = useCallback((args) => listRequests({ ...args, status: statusFilter }), [statusFilter])

  const filters = (
    <>
      <TextField
        select
        size="small"
        label="Status"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        sx={{ minWidth: 160 }}
      >
        <MenuItem value="">All statuses</MenuItem>
        {Object.entries(MAINTENANCE_STATUS_LABELS).map(([value, label]) => (
          <MenuItem key={value} value={value}>
            {label}
          </MenuItem>
        ))}
        <MenuItem value={AWAITING_INSPECTION_FILTER}>Awaiting inspection</MenuItem>
      </TextField>
      {filtersActive ? (
        <Button size="small" onClick={clearFilters}>
          Clear filters
        </Button>
      ) : null}
    </>
  )

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1">
        Maintenance requests
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Problems reported by employees and the IT team. To report a new problem, open the asset and choose Report a problem.
      </Typography>
      <DataTable
        columns={COLUMNS}
        fetchRows={fetchRows}
        defaultSort="-request_number"
        searchPlaceholder="Search request number, asset ID, asset or serial number"
        emptyTitle="No maintenance requests"
        emptyMessage="Problems reported from an asset's page or from My Assets will be listed here."
        toolbar={filters}
        filtersActive={filtersActive}
        onClearFilters={clearFilters}
        onRowClick={(r) => navigate(requestPath(r))}
        rowLabel={(r) => `Open ${r.request_number} (${r.asset.asset_code})`}
      />
    </Stack>
  )
}
