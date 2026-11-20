// Assets page: the asset register (Admin and IT Manager, Slice 4.1, AST-03, AST-05).
// Search by asset ID, serial number or name; filter by category, status and location
// (exact location, any case, chosen from the locations in use); sort and page on the
// server. Clicking a row (or Enter / Space on it) opens the asset page /assets/:assetId (D7).
// Reading only: editing and retiring are Slice 4.2; manual entry is Slice 4.5.
// The employee filter arrives with assignments in Slice 5.1 (owner's answer to A1).
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { Button, MenuItem, Stack, TextField, Typography } from '@mui/material'

import { ASSET_STATUS_LABELS, assetPath, assetStatusLabel, listAssetLocations, listAssets } from '../../api/assets'
import { listCategories } from '../../api/categories'
import DataTable from '../../components/DataTable'
import StatusBadge from '../../components/StatusBadge'

const dash = (
  <Typography variant="body2" color="text.secondary" component="span">
    —
  </Typography>
)

const COLUMNS = [
  { field: 'asset_code', label: 'Asset ID', sortable: true },
  { field: 'name', label: 'Name', sortable: true },
  { field: 'category', label: 'Category', sortable: true, render: (a) => a.category.name },
  { field: 'serial_number', label: 'Serial number', sortable: true },
  { field: 'model', label: 'Model', sortable: true, render: (a) => [a.brand, a.model].filter(Boolean).join(' ') },
  { field: 'location', label: 'Location', sortable: true, render: (a) => a.location || dash },
  { field: 'status', label: 'Status', sortable: true, render: (a) => <StatusBadge status={assetStatusLabel(a.status)} /> },
]

export default function AssetsPage() {
  const navigate = useNavigate()

  // Filters
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [locationFilter, setLocationFilter] = useState('')
  // While any filter is set: a Clear filters button, and "No matches" for an empty result (D9).
  const filtersActive = Boolean(categoryFilter || statusFilter || locationFilter)
  const clearFilters = () => {
    setCategoryFilter('')
    setStatusFilter('')
    setLocationFilter('')
  }

  // Filter choices: one-by-one categories (active and inactive; first 100 by name, B53)
  // and the locations already typed on assets.
  const [categories, setCategories] = useState([])
  const [locations, setLocations] = useState([])
  useEffect(() => {
    listCategories({ page: 1, pageSize: 100, sort: 'name', trackingType: 'serialized' })
      .then((data) => setCategories(data.items))
      .catch(() => setCategories([]))
    listAssetLocations()
      .then(setLocations)
      .catch(() => setLocations([]))
  }, [])

  const fetchRows = useCallback(
    (args) => listAssets({ ...args, categoryId: categoryFilter, status: statusFilter, location: locationFilter }),
    [categoryFilter, statusFilter, locationFilter],
  )

  const filters = (
    <>
      <TextField
        select
        size="small"
        label="Category"
        value={categoryFilter}
        onChange={(e) => setCategoryFilter(e.target.value)}
        sx={{ minWidth: 160 }}
      >
        <MenuItem value="">All categories</MenuItem>
        {categories.map((c) => (
          <MenuItem key={c.id} value={c.id}>
            {c.name}
            {c.status !== 'active' ? ' (inactive)' : ''}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        select
        size="small"
        label="Status"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
        sx={{ minWidth: 170 }}
      >
        <MenuItem value="">All statuses</MenuItem>
        {Object.entries(ASSET_STATUS_LABELS).map(([value, label]) => (
          <MenuItem key={value} value={value}>
            {label}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        select
        size="small"
        label="Location"
        value={locationFilter}
        onChange={(e) => setLocationFilter(e.target.value)}
        sx={{ minWidth: 170 }}
      >
        <MenuItem value="">All locations</MenuItem>
        {locations.map((loc) => (
          <MenuItem key={loc} value={loc}>
            {loc}
          </MenuItem>
        ))}
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
        Assets
      </Typography>

      <DataTable
        columns={COLUMNS}
        fetchRows={fetchRows}
        defaultSort="-asset_code"
        searchPlaceholder="Search asset ID, serial number or name"
        emptyTitle="No assets yet"
        emptyMessage="Assets are created when a purchase with one-by-one items is received."
        toolbar={filters}
        filtersActive={filtersActive}
        onClearFilters={clearFilters}
        onRowClick={(a) => navigate(assetPath(a))}
        rowLabel={(a) => `Open ${a.asset_code}`}
      />
    </Stack>
  )
}
