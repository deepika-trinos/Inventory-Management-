// Request page: /maintenance/:requestRef (Admin and IT Manager, Slice 6.2: MNT-04 to MNT-07; owner's
// answers S1-S14). :requestRef is the request number (MNT-000001) or the id.
// Shows the asset, the problem, priority, status, who reported / started / completed or cancelled it
// and when, the service provider, repair notes and cost, and the request's History (S13).
// Buttons by status: Start work… (Reported; greyed out "Return it first." while the asset is
// Assigned, S1), Mark completed… (In Progress), Cancel request… (Reported or In Progress) and Edit
// details (while open). Completed and Cancelled requests are final (S4) and read-only.
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import { Box, Button, Divider, Link, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Tooltip, Typography } from '@mui/material'

import { assetPath, assetStatusLabel } from '../../api/assets'
import { getErrorCode } from '../../api/errors'
import { getRequest, isOpenStatus, maintenanceStatusLabel, priorityLabel, reporterLabel } from '../../api/maintenance'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatDateTime, formatPlainDate } from '../../utils/dates'
import { formatAmount } from '../../utils/money'
import { maintenanceActionLabel, maintenanceHistoryNote } from './maintenanceHistory'
import { CancelDialog, CompleteDialog, EditRequestDialog, StartWorkDialog } from './RequestProgressDialogs'

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
const byWhen = (user, at) => (user ? `${user.email} · ${formatDateTime(at)}` : null)

/** Why Start work… is greyed out, or '' when it can be pressed (S1). */
export function startBlockedReason(request) {
  if (request.status !== 'reported') return ''
  if (request.asset.status === 'assigned') return `${request.asset.asset_code} is assigned. Return it first.`
  if (request.asset.status === 'retired') return `${request.asset.asset_code} is retired.`
  return ''
}

export default function MaintenanceRequestPage() {
  const { requestRef } = useParams()
  const [request, setRequest] = useState(null)
  const [error, setError] = useState(null)
  const [dialog, setDialog] = useState(null) // 'start' | 'complete' | 'cancel' | 'edit'
  const notify = useNotify()

  const load = useCallback(() => {
    setError(null)
    getRequest(requestRef).then(setRequest).catch(setError)
  }, [requestRef])

  useEffect(load, [load])

  const backLink = (
    <Button component={RouterLink} to="/maintenance" startIcon={<ArrowBackOutlined />} sx={{ alignSelf: 'flex-start' }}>
      All requests
    </Button>
  )

  if (error) {
    const notFound = getErrorCode(error) === 'maintenance_request_not_found' || error?.response?.status === 422
    return (
      <Stack spacing={2}>
        {backLink}
        {notFound ? (
          <EmptyState title="Request not found" message="It may have been typed wrongly in the address." />
        ) : (
          <ErrorMessage error={error} onRetry={load} />
        )}
      </Stack>
    )
  }
  if (!request) return <LoadingState message="Loading request…" />

  const r = request
  const open = isOpenStatus(r.status)
  const startBlocked = startBlockedReason(r)

  const afterSave = (message) => (saved) => {
    setRequest(saved)
    setDialog(null)
    notify.success(message(saved))
  }

  return (
    <Stack spacing={2}>
      {backLink}

      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center' }}>
          <Typography variant="h5" component="h1">
            Request {r.request_number}
          </Typography>
          <StatusBadge status={maintenanceStatusLabel(r.status)} />
        </Stack>
        {open ? (
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
            {r.status === 'reported' ? (
              <Tooltip title={startBlocked}>
                <span>
                  <Button variant="contained" disabled={Boolean(startBlocked)} onClick={() => setDialog('start')}>
                    Start work…
                  </Button>
                </span>
              </Tooltip>
            ) : null}
            {r.status === 'in_progress' ? (
              <Button variant="contained" onClick={() => setDialog('complete')}>
                Mark completed…
              </Button>
            ) : null}
            <Button variant="outlined" onClick={() => setDialog('edit')}>
              Edit details
            </Button>
            <Button variant="outlined" color="error" onClick={() => setDialog('cancel')}>
              Cancel request…
            </Button>
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {maintenanceStatusLabel(r.status)} requests are final. Read-only.
          </Typography>
        )}
      </Stack>

      <Section title="Request">
        <Box sx={grid}>
          <Detail
            label="Asset"
            testId="request-asset"
            value={
              <>
                <Link component={RouterLink} to={assetPath(r.asset)} underline="hover">
                  {r.asset.asset_code}
                </Link>
                {` · ${r.asset.name} · ${assetStatusLabel(r.asset.status)}`}
              </>
            }
          />
          <Detail label="Problem" value={r.issue_description} />
          <Detail label="Priority" value={priorityLabel(r.priority)} />
          <Detail label="Reported" value={`${formatPlainDate(r.reported_date)} by ${reporterLabel(r.reported_by)}`} />
          <Detail
            label="Work started"
            testId="request-started"
            value={r.started_date ? `${formatPlainDate(r.started_date)} · ${byWhen(r.started_by, r.started_at)}` : null}
          />
          {r.status === 'completed' ? (
            <Detail
              label="Completed"
              testId="request-completed"
              value={`${formatPlainDate(r.completion_date)} · ${byWhen(r.completed_by, r.completed_at)}`}
            />
          ) : null}
          {r.status === 'cancelled' ? (
            <>
              <Detail label="Cancelled" testId="request-cancelled" value={byWhen(r.cancelled_by, r.cancelled_at)} />
              <Detail label="Reason for cancelling" value={r.cancel_reason} />
            </>
          ) : null}
          <Detail label="Service provider or responsible person" testId="request-provider" value={r.service_provider} />
          <Detail label="Repair notes" testId="request-notes" value={r.repair_notes} />
          <Detail label="Cost" testId="request-cost" value={r.cost !== null && r.cost !== undefined ? formatAmount(r.cost) : null} />
        </Box>
      </Section>

      <Section title="History">
        <Table size="small" aria-label="Request history">
          <TableHead>
            <TableRow>
              {['When', 'What', 'By', 'Details'].map((label) => (
                <TableCell key={label}>{label}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {r.history.map((h) => (
              <TableRow key={h.id} data-testid="request-history-row">
                <TableCell>{formatDateTime(h.created_at)}</TableCell>
                <TableCell>{maintenanceActionLabel(h) ?? h.action}</TableCell>
                <TableCell>{h.actor?.email ?? 'System'}</TableCell>
                <TableCell sx={{ wordBreak: 'break-word' }}>{maintenanceHistoryNote(h) || '—'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Section>

      {dialog === 'start' ? (
        <StartWorkDialog
          request={r}
          onClose={() => setDialog(null)}
          onSaved={afterSave((s) => `Work started on ${s.request_number}. ${s.asset.asset_code} is Under Maintenance.`)}
        />
      ) : null}
      {dialog === 'complete' ? (
        <CompleteDialog
          request={r}
          onClose={() => setDialog(null)}
          onSaved={afterSave((s) => `${s.request_number} completed. ${s.asset.asset_code} stays Under Maintenance until inspected.`)}
        />
      ) : null}
      {dialog === 'cancel' ? (
        <CancelDialog request={r} onClose={() => setDialog(null)} onSaved={afterSave((s) => `${s.request_number} cancelled.`)} />
      ) : null}
      {dialog === 'edit' ? (
        <EditRequestDialog request={r} onClose={() => setDialog(null)} onSaved={afterSave((s) => `${s.request_number} saved.`)} />
      ) : null}
    </Stack>
  )
}
