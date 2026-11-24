// My Assets: /my/assets (Employee role only, Slice 5.3: EMP-04; owner's answers N8, N11-N13).
// The logged-in employee's own current assets (overdue items flagged, N7) and past assignments,
// read-only. Shows asset, dates, expected return, return date and inspection outcome; not the
// condition notes or the staff who assigned or returned it (N12). Employees land here after
// login until Slice 6.4 builds My Dashboard (N11).
import { useCallback, useEffect, useState } from 'react'
import { Stack, Typography } from '@mui/material'

import { getMyAssignments } from '../../api/assignments'
import AssignmentTables from '../../components/AssignmentTables'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'

export default function MyAssetsPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setError(null)
    getMyAssignments().then(setData).catch(setError)
  }, [])

  useEffect(load, [load])

  if (error) return <ErrorMessage error={error} onRetry={load} />
  if (!data) return <LoadingState message="Loading your assets…" />

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1">
        My Assets
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Equipment assigned to you ({data.employee.full_name}, {data.employee.employee_code}). To return something or report a
        problem, contact the IT team.
      </Typography>
      <AssignmentTables data={data} emptyCurrent="You hold no assets right now." />
    </Stack>
  )
}
