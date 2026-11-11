// DEVELOPMENT ONLY (/dev/components): try every reusable component in one place.
// Not in the menu and not included in production builds. The table uses
// made-up rows and a fake "server" so paging, sorting and searching can be
// tested before any real list page exists.
import { useCallback, useState } from 'react'
import { Button, Divider, Paper, Stack, Typography } from '@mui/material'

import ConfirmDialog from '../../components/ConfirmDialog'
import DataTable from '../../components/DataTable'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import FormField from '../../components/FormField'
import LoadingState from '../../components/LoadingState'
import StatusBadge, { ASSET_STATUSES } from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatDate, formatDateTime } from '../../utils/dates'

const SAMPLE_ROWS = Array.from({ length: 47 }, (_, i) => ({
  id: i + 1,
  code: `AST-${String(i + 1).padStart(6, '0')}`,
  name: ['Dell Latitude 5440', 'HP EliteBook 840', 'Dell P2422H Monitor', 'Lenovo ThinkPad T14'][i % 4],
  status: ASSET_STATUSES[i % ASSET_STATUSES.length],
  created_at: new Date(Date.UTC(2026, 10, 1 + (i % 10), 4, 30 + i)).toISOString(),
}))

// Pretends to be the backend's paged-list endpoint.
function fakeServer({ page, pageSize, sort, search }) {
  let rows = SAMPLE_ROWS.filter((r) =>
    search ? `${r.code} ${r.name} ${r.status}`.toLowerCase().includes(search.toLowerCase()) : true,
  )
  if (sort) {
    const desc = sort.startsWith('-')
    const field = sort.replace('-', '')
    rows = [...rows].sort((a, b) => (a[field] > b[field] ? 1 : -1) * (desc ? -1 : 1))
  }
  const start = (page - 1) * pageSize
  return new Promise((resolve) =>
    setTimeout(() => resolve({ items: rows.slice(start, start + pageSize), total: rows.length }), 500),
  )
}

function Section({ title, children }) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        {title}
      </Typography>
      {children}
    </Paper>
  )
}

export default function ComponentGalleryPage() {
  const notify = useNotify()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [field, setField] = useState('')
  const fetchRows = useCallback(fakeServer, [])
  const failingFetch = useCallback(() => Promise.reject(new Error('demo')), [])

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1">
        Component gallery (development only)
      </Typography>

      <Section title="DataTable (fake server, 47 rows)">
        <DataTable
          columns={[
            { field: 'code', label: 'Asset ID', sortable: true },
            { field: 'name', label: 'Name', sortable: true },
            { field: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
            { field: 'created_at', label: 'Added', sortable: true, render: (r) => formatDateTime(r.created_at) },
          ]}
          fetchRows={fetchRows}
          defaultSort="code"
          searchPlaceholder="Search ID, name or status"
        />
      </Section>

      <Section title="DataTable when the server fails">
        <DataTable columns={[{ field: 'x', label: 'X' }]} fetchRows={failingFetch} searchable={false} />
      </Section>

      <Section title="StatusBadge">
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          {ASSET_STATUSES.map((s) => (
            <StatusBadge key={s} status={s} />
          ))}
        </Stack>
      </Section>

      <Section title="FormField">
        <FormField
          label="Vendor name"
          required
          value={field}
          onChange={(e) => setField(e.target.value)}
          error={field ? '' : 'Please enter the vendor name.'}
        />
        <FormField label="Notes" helperText="Optional" multiline minRows={2} />
      </Section>

      <Section title="ConfirmDialog and snackbar messages">
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Button variant="outlined" color="error" onClick={() => setConfirmOpen(true)}>
            Retire asset…
          </Button>
          <Button variant="outlined" onClick={() => notify.success('Saved successfully.')}>
            Success message
          </Button>
          <Button variant="outlined" onClick={() => notify.error('Could not save. Please try again.')}>
            Error message
          </Button>
        </Stack>
        <ConfirmDialog
          open={confirmOpen}
          title="Retire this asset?"
          message="A retired asset can never be assigned again. This cannot be undone."
          confirmLabel="Retire"
          destructive
          onCancel={() => setConfirmOpen(false)}
          onConfirm={async () => {
            await new Promise((r) => setTimeout(r, 800))
            setConfirmOpen(false)
            notify.success('Asset retired (demo).')
          }}
        />
      </Section>

      <Section title="Loading, empty and error states">
        <LoadingState />
        <Divider />
        <EmptyState title="No vendors yet" message="Add your first vendor to get started." />
        <Divider sx={{ mb: 2 }} />
        <ErrorMessage message="Cannot reach the server." onRetry={() => notify.info('Retry clicked')} />
      </Section>

      <Section title="Dates in the company timezone">
        <Typography variant="body2">UTC value: 2026-11-11T04:30:00Z</Typography>
        <Typography variant="body2">formatDateTime: {formatDateTime('2026-11-11T04:30:00Z')}</Typography>
        <Typography variant="body2">formatDate: {formatDate('2026-11-11T20:00:00Z')}</Typography>
      </Section>
    </Stack>
  )
}
