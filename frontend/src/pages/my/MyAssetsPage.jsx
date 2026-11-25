// My Assets: /my/assets (Employee role only, Slice 5.3: EMP-04; owner's answers N8, N11-N13).
// The logged-in employee's own current assets (overdue items flagged, N7) and past assignments,
// read-only. Shows asset, dates, expected return, return date and inspection outcome; not the
// condition notes or the staff who assigned or returned it (N12). Employees land here after
// login until Slice 6.4 builds My Dashboard (N11).
// Slice 6.1 (MNT-01; owner's answers O3, O6, O12): each CURRENT asset has "Report a problem"
// (issue only); after reporting, "Problem reported: MNT-000001. The IT team will review it." and
// the row shows "Problem reported (MNT-…)" instead of the button while that request is open.
// Past assets have no button (O6). The full My Requests page is Slice 6.4.
import { useCallback, useEffect, useState } from 'react'
import BuildOutlined from '@mui/icons-material/BuildOutlined'
import { Button, Chip, Stack, Typography } from '@mui/material'

import { getMyAssignments } from '../../api/assignments'
import AssignmentTables from '../../components/AssignmentTables'
import ErrorMessage from '../../components/ErrorMessage'
import LoadingState from '../../components/LoadingState'
import { useNotify } from '../../context/NotificationContext'
import ReportProblemDialog from '../maintenance/ReportProblemDialog'

export default function MyAssetsPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [reporting, setReporting] = useState(null) // the asset being reported, or null
  const notify = useNotify()

  const load = useCallback(() => {
    setError(null)
    getMyAssignments().then(setData).catch(setError)
  }, [])

  useEffect(load, [load])

  if (error) return <ErrorMessage error={error} onRetry={load} />
  if (!data) return <LoadingState message="Loading your assets…" />

  const problemColumn = {
    label: 'Problem',
    render: (a) =>
      a.open_request ? (
        <Chip
          size="small"
          color="warning"
          variant="outlined"
          label={`Problem reported (${a.open_request.request_number})`}
          data-testid="open-request"
        />
      ) : (
        <Button size="small" startIcon={<BuildOutlined />} onClick={() => setReporting(a.asset)}>
          Report a problem
        </Button>
      ),
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1">
        My Assets
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Equipment assigned to you ({data.employee.full_name}, {data.employee.employee_code}). To report a problem with
        something you hold, use Report a problem. To return something, contact the IT team.
      </Typography>
      <AssignmentTables data={data} emptyCurrent="You hold no assets right now." extraCurrentColumns={[problemColumn]} />

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
