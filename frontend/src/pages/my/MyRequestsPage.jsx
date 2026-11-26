// My Requests: /my/requests (Employee role only, Slice 6.4: MNT-08; owner's answers in decisions.md
// section 37). The maintenance requests the logged-in user reported, newest first, also for assets they
// have since returned (O6). Read-only: no cancel, no comments (S11). Each row shows the request, asset,
// problem, status, reported date and the progress ("Work started … · Completed …", or "Cancelled … —
// Reason: …"). No priority, service provider, repair notes, cost, staff e-mails or inspection details:
// the server never sends them.
// "Report a problem…" opens a picker of the assets held now (greyed out while one has an open request),
// then the same report form as My Assets (Slice 6.1).
import { useCallback, useEffect, useState } from 'react'
import BuildOutlined from '@mui/icons-material/BuildOutlined'
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItemButton,
  ListItemText,
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

import { getMyAssignments } from '../../api/assignments'
import { getMyRequests, maintenanceStatusLabel, myRequestProgress } from '../../api/maintenance'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { useNotify } from '../../context/NotificationContext'
import { formatPlainDate } from '../../utils/dates'
import ReportProblemDialog from '../maintenance/ReportProblemDialog'

/** Pick one of the assets held now (Q8). Assets with an open request are shown but cannot be picked. */
export function AssetPicker({ current, onPick, onClose }) {
  return (
    <Dialog open onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Which asset has the problem?</DialogTitle>
      <DialogContent>
        <List dense>
          {current.map((row) => (
            <ListItemButton
              key={row.asset.id}
              disabled={Boolean(row.open_request)}
              onClick={() => onPick(row.asset)}
              data-testid="pick-asset"
            >
              <ListItemText
                primary={`${row.asset.asset_code} · ${row.asset.name}`}
                secondary={
                  row.open_request
                    ? `Problem already reported (${row.open_request.request_number})`
                    : `Serial ${row.asset.serial_number}`
                }
              />
            </ListItemButton>
          ))}
        </List>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}

export default function MyRequestsPage() {
  const [requests, setRequests] = useState(null)
  const [error, setError] = useState(null)
  const [current, setCurrent] = useState(null) // assets held now, for the picker; [] if not linked
  const [picking, setPicking] = useState(false)
  const [reporting, setReporting] = useState(null)
  const notify = useNotify()

  const load = useCallback(() => {
    setError(null)
    getMyRequests().then(setRequests).catch(setError)
    getMyAssignments()
      .then((data) => setCurrent(data.current))
      .catch(() => setCurrent([])) // e.g. login not linked: nothing to report on
  }, [])

  useEffect(load, [load])

  if (error) return <ErrorMessage error={error} onRetry={load} />
  if (!requests) return <LoadingState message="Loading your requests…" />

  const noAssets = current !== null && current.length === 0
  const reportBlocked = noAssets ? 'You hold no assets.' : ''

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" component="h1">
          My Requests
        </Typography>
        <Tooltip title={reportBlocked}>
          <span>
            <Button
              variant="contained"
              startIcon={<BuildOutlined />}
              disabled={current === null || noAssets}
              onClick={() => setPicking(true)}
            >
              Report a problem…
            </Button>
          </span>
        </Tooltip>
      </Stack>
      <Typography variant="body2" color="text.secondary">
        Problems you reported, newest first. The IT team updates them as the repair goes on.
      </Typography>

      {requests.length === 0 ? (
        <EmptyState title="No requests yet" message="Problems you report will be listed here." />
      ) : (
        <TableContainer>
          <Table size="small" aria-label="My requests">
            <TableHead>
              <TableRow>
                {['Request', 'Asset', 'Problem', 'Status', 'Reported on', 'Progress'].map((label) => (
                  <TableCell key={label}>{label}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {requests.map((r) => (
                <TableRow key={r.request_number} data-testid="my-request-row">
                  <TableCell>{r.request_number}</TableCell>
                  <TableCell>{`${r.asset.asset_code} · ${r.asset.name}`}</TableCell>
                  <TableCell sx={{ wordBreak: 'break-word' }}>{r.issue_description}</TableCell>
                  <TableCell>
                    <StatusBadge status={maintenanceStatusLabel(r.status)} />
                  </TableCell>
                  <TableCell>{formatPlainDate(r.reported_date)}</TableCell>
                  <TableCell sx={{ wordBreak: 'break-word' }} data-testid="my-request-progress">
                    {myRequestProgress(r)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {picking ? (
        <AssetPicker
          current={current ?? []}
          onClose={() => setPicking(false)}
          onPick={(asset) => {
            setPicking(false)
            setReporting(asset)
          }}
        />
      ) : null}
      {reporting ? (
        <ReportProblemDialog
          open
          asset={reporting}
          onClose={() => setReporting(null)}
          onReported={(saved) => {
            setReporting(null)
            notify.success(`Problem reported: ${saved.request_number}. The IT team will review it.`)
            load()
          }}
        />
      ) : null}
    </Stack>
  )
}
