// My Dashboard: /my/dashboard (Employee role only, Slice 6.4: MNT-08, PRD 4.2; owner's answers in
// decisions.md section 37). The Employee's home page after login (N11). Only their own data, from the
// two /me endpoints (no dashboard endpoint): three counts (assets I hold, overdue returns, my open
// requests), the overdue returns and the open requests, with links to My Assets and My Requests.
// A login not linked to an employee record sees the server's message for the asset part; its requests
// still show (they go by who reported them).
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink } from 'react-router'
import { Box, Button, Card, CardContent, Divider, Paper, Stack, Typography } from '@mui/material'

import { getMyAssignments, overdueLabel } from '../../api/assignments'
import { getErrorCode, getErrorMessage } from '../../api/errors'
import { getMyRequests, isOpenStatus, maintenanceStatusLabel } from '../../api/maintenance'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge from '../../components/StatusBadge'
import { formatPlainDate } from '../../utils/dates'

function Count({ label, value, testId, warn = false }) {
  return (
    <Card variant="outlined" sx={{ flex: '1 1 160px' }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h4" component="p" color={warn && value > 0 ? 'error' : 'text.primary'} data-testid={testId}>
          {value ?? '—'}
        </Typography>
      </CardContent>
    </Card>
  )
}

function Section({ title, link, linkLabel, children }) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }} component="section" aria-label={title}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" component="h2">
          {title}
        </Typography>
        <Button component={RouterLink} to={link} size="small">
          {linkLabel}
        </Button>
      </Stack>
      <Divider sx={{ my: 1 }} />
      {children}
    </Paper>
  )
}

export default function MyDashboardPage() {
  const [assets, setAssets] = useState(null) // the /me/assignments answer
  const [assetsError, setAssetsError] = useState(null)
  const [requests, setRequests] = useState(null)
  const [requestsError, setRequestsError] = useState(null)

  const load = useCallback(() => {
    setAssetsError(null)
    setRequestsError(null)
    getMyAssignments().then(setAssets).catch(setAssetsError)
    getMyRequests().then(setRequests).catch(setRequestsError)
  }, [])

  useEffect(load, [load])

  const notLinked = getErrorCode(assetsError) === 'employee_not_linked'
  if ((assetsError && !notLinked) || requestsError) {
    return <ErrorMessage error={requestsError ?? assetsError} onRetry={load} />
  }
  if ((!assets && !notLinked) || !requests) return <LoadingState message="Loading your dashboard…" />

  const held = assets?.current ?? []
  const overdue = held.filter((a) => a.is_overdue)
  const open = requests.filter((r) => isOpenStatus(r.status))

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1">
        My Dashboard
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {assets ? `Welcome, ${assets.employee.full_name}. ` : ''}Your assets and the problems you reported.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Count label="Assets I hold" value={notLinked ? null : held.length} testId="count-held" />
        <Count label="Overdue returns" value={notLinked ? null : overdue.length} testId="count-overdue" warn />
        <Count label="My open requests" value={open.length} testId="count-open" />
      </Box>

      <Section title="Overdue returns" link="/my/assets" linkLabel="My Assets">
        {notLinked ? (
          <Typography variant="body2" color="text.secondary" data-testid="not-linked">
            {getErrorMessage(assetsError)}
          </Typography>
        ) : overdue.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Nothing overdue.
          </Typography>
        ) : (
          overdue.map((a) => (
            <Typography key={a.asset.asset_code} variant="body2" data-testid="overdue-row">
              {`${a.asset.asset_code} · ${a.asset.name} — expected back ${formatPlainDate(a.expected_return_date)} · `}
              <Typography component="span" variant="body2" color="error">
                {overdueLabel(a.days_overdue)}
              </Typography>
            </Typography>
          ))
        )}
      </Section>

      <Section title="My open requests" link="/my/requests" linkLabel="My Requests">
        {open.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No open requests.
          </Typography>
        ) : (
          <Stack spacing={1}>
            {open.map((r) => (
              <Stack key={r.request_number} direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }} data-testid="open-request-row">
                <Typography variant="body2">{`${r.request_number} · ${r.asset.asset_code} · ${r.issue_description}`}</Typography>
                <StatusBadge status={maintenanceStatusLabel(r.status)} />
                <Typography variant="caption" color="text.secondary">
                  reported {formatPlainDate(r.reported_date)}
                </Typography>
              </Stack>
            ))}
          </Stack>
        )}
      </Section>
    </Stack>
  )
}
