// Assignments page: /assignments (Admin and IT Manager, Slice 5.3: ASN-08; owner's answers N7, N10).
// For now it shows the OVERDUE list only (N10): assignments whose expected return date is before
// today (company timezone) and that are not returned. Most late first; search by asset or employee;
// sorted and paged on the server. A row opens the asset page, where the return is recorded.
// No e-mail reminders (N7).
import { useNavigate } from 'react-router'
import { Stack, Typography } from '@mui/material'

import { assetPath } from '../../api/assets'
import { listOverdue } from '../../api/assignments'
import { OverdueBadge } from '../../components/AssignmentTables'
import DataTable from '../../components/DataTable'
import { formatPlainDate } from '../../utils/dates'

const COLUMNS = [
  { field: 'asset_code', label: 'Asset ID', sortable: true, render: (a) => a.asset.asset_code },
  { field: 'asset_name', label: 'Asset', render: (a) => a.asset.name },
  {
    field: 'employee',
    label: 'Employee',
    sortable: true,
    render: (a) => `${a.employee.full_name} (${a.employee.employee_code})${a.employee.status !== 'active' ? ' (inactive)' : ''}`,
  },
  { field: 'assignment_date', label: 'Assigned on', sortable: true, render: (a) => formatPlainDate(a.assignment_date) },
  { field: 'expected_return_date', label: 'Expected return', sortable: true, render: (a) => formatPlainDate(a.expected_return_date) },
  { field: 'days_overdue', label: 'Overdue', render: (a) => <OverdueBadge days={a.days_overdue} /> },
]

export default function AssignmentsPage() {
  const navigate = useNavigate()
  return (
    <Stack spacing={2}>
      <Typography variant="h5" component="h1">
        Overdue returns
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Assets whose expected return date has passed and that have not been returned. Open one to record its return.
      </Typography>
      <DataTable
        columns={COLUMNS}
        fetchRows={listOverdue}
        defaultSort="expected_return_date"
        searchPlaceholder="Search asset ID, asset, serial number or employee"
        emptyTitle="No overdue returns"
        emptyMessage="Every asset with an expected return date is either back or not due yet."
        onRowClick={(a) => navigate(assetPath(a.asset))}
        rowLabel={(a) => `Open ${a.asset.asset_code}`}
      />
    </Stack>
  )
}
