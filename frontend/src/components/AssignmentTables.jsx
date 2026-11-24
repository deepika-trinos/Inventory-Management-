// An employee's "Current assets" and "Past assignments" (Slice 5.3: EMP-04, ASN-07; owner's answers
// N7, N8, N12). Used by the employee page (staff) and My Assets (the employee, read-only).
//
//   <AssignmentTables data={{ current, past }} staff />
//
// staff: asset IDs link to the asset page, and the past table also shows the condition notes and
// who assigned / returned it. Without it (My Assets) those are left out (N12) and nothing links to
// pages an Employee cannot open. An overdue item (N7) gets a red "N days overdue" badge.
import { Link as RouterLink } from 'react-router'
import { Chip, Link, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material'

import { assetStatusLabel } from '../api/assets'
import { overdueLabel } from '../api/assignments'
import { formatPlainDate } from '../utils/dates'

const dash = '—'

export function OverdueBadge({ days }) {
  return <Chip size="small" color="error" label={overdueLabel(days)} data-testid="overdue-badge" />
}

function AssetCell({ asset, staff }) {
  const text = `${asset.asset_code} · ${asset.name}`
  if (!staff) return text
  return (
    <>
      <Link component={RouterLink} to={`/assets/${encodeURIComponent(asset.asset_code)}`} underline="hover">
        {asset.asset_code}
      </Link>
      {` · ${asset.name}`}
    </>
  )
}

function Section({ title, empty, columns, rows }) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }} component="section" aria-label={title}>
      <Typography variant="h6" component="h2" sx={{ mb: 1 }}>
        {title}
      </Typography>
      {rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {empty}
        </Typography>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                {columns.map((c) => (
                  <TableCell key={c.label}>{c.label}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id}>
                  {columns.map((c) => (
                    <TableCell key={c.label}>{c.render(row)}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  )
}

export default function AssignmentTables({ data, staff = false, emptyCurrent = 'No assets held now.' }) {
  const date = (value) => (value ? formatPlainDate(value) : dash)
  const asset = { label: 'Asset', render: (a) => <AssetCell asset={a.asset} staff={staff} /> }
  const serial = { label: 'Serial number', render: (a) => a.asset.serial_number }

  const currentColumns = [
    asset,
    serial,
    { label: 'Assigned on', render: (a) => date(a.assignment_date) },
    {
      label: 'Expected return',
      render: (a) => (
        <>
          {a.expected_return_date ? formatPlainDate(a.expected_return_date) : 'Not set'}{' '}
          {a.is_overdue ? <OverdueBadge days={a.days_overdue} /> : null}
        </>
      ),
    },
  ]
  if (staff) currentColumns.push({ label: 'Assigned by', render: (a) => a.assigned_by?.email ?? dash })

  const pastColumns = [
    asset,
    { label: 'Assigned on', render: (a) => date(a.assignment_date) },
    { label: 'Expected return', render: (a) => date(a.expected_return_date) },
    { label: 'Returned on', render: (a) => date(a.return_date) },
    { label: 'Inspection outcome', render: (a) => (a.return_outcome ? assetStatusLabel(a.return_outcome) : dash) },
  ]
  if (staff) {
    pastColumns.push(
      { label: 'Condition notes', render: (a) => a.condition_notes || dash },
      { label: 'Returned by', render: (a) => a.returned_by?.email ?? dash },
    )
  }

  return (
    <>
      <Section title="Current assets" empty={emptyCurrent} columns={currentColumns} rows={data.current} />
      <Section title="Past assignments" empty="No past assignments." columns={pastColumns} rows={data.past} />
    </>
  )
}
