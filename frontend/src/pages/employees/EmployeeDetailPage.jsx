// Employee page: /employees/:employeeId (Admin and IT Manager, Slice 5.3: EMP-04, ASN-07).
// The employee's details, what they hold now ("Current assets", overdue items flagged, N7) and
// every past assignment with its return details, newest return first. Inactive employees too.
// Editing and activating stay on the Employees list.
import { useCallback, useEffect, useState } from 'react'
import { Link as RouterLink, useParams } from 'react-router'
import ArrowBackOutlined from '@mui/icons-material/ArrowBackOutlined'
import { Box, Button, Paper, Stack, Typography } from '@mui/material'

import { getEmployeeAssignments } from '../../api/assignments'
import { getEmployee } from '../../api/employees'
import { getErrorCode } from '../../api/errors'
import AssignmentTables from '../../components/AssignmentTables'
import EmptyState from '../../components/EmptyState'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import StatusBadge, { recordStatusLabel } from '../../components/StatusBadge'

function Detail({ label, value }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1" sx={{ wordBreak: 'break-word' }}>
        {value || '—'}
      </Typography>
    </Box>
  )
}

export default function EmployeeDetailPage() {
  const { employeeId } = useParams()
  const [employee, setEmployee] = useState(null)
  const [held, setHeld] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([getEmployee(employeeId), getEmployeeAssignments(employeeId)])
      .then(([e, h]) => {
        setEmployee(e)
        setHeld(h)
      })
      .catch(setError)
      .finally(() => setLoading(false))
  }, [employeeId])

  useEffect(load, [load])

  const backLink = (
    <Button component={RouterLink} to="/employees" startIcon={<ArrowBackOutlined />} sx={{ alignSelf: 'flex-start' }}>
      All employees
    </Button>
  )

  if (loading && !employee) return <LoadingState message="Loading employee…" />
  if (error) {
    const notFound = getErrorCode(error) === 'employee_not_found' || error?.response?.status === 422
    return (
      <Stack spacing={2}>
        {backLink}
        {notFound ? (
          <EmptyState title="Employee not found" message="It may have been typed wrongly in the address." />
        ) : (
          <ErrorMessage error={error} onRetry={load} />
        )}
      </Stack>
    )
  }

  const e = employee
  return (
    <Stack spacing={2}>
      {backLink}
      <Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
        <Typography variant="h5" component="h1">
          {e.full_name} ({e.employee_code})
        </Typography>
        <StatusBadge status={recordStatusLabel(e.status)} />
      </Stack>

      <Paper variant="outlined" sx={{ p: 2 }} component="section" aria-label="Details">
        <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: '1fr 1fr 1fr' } }}>
          <Detail label="Department" value={e.department} />
          <Detail label="Designation" value={e.designation} />
          <Detail label="Work email" value={e.work_email} />
          <Detail label="Phone" value={e.phone} />
          <Detail label="Login" value={e.user ? `${e.user.email}${e.user.is_active ? '' : ' (deactivated)'}` : 'No login'} />
        </Box>
      </Paper>

      <AssignmentTables data={held} staff />
    </Stack>
  )
}
