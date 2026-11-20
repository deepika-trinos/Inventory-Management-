// A searchable, sortable, paged table that asks the SERVER for one page at a time
// (PRD 10: "use pagination and server-side filtering for growing datasets").
//
//   <DataTable
//     columns={[
//       { field: 'asset_code', label: 'Asset ID', sortable: true },
//       { field: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> },
//     ]}
//     fetchRows={({ page, pageSize, sort, search }) => api.listAssets(...)}  // returns { items, total }
//     defaultSort="-created_at"
//   />
//
// It matches the backend's paged-list helper: page starts at 1, sort is a field
// name with "-" for descending, and the answer is { items, total, page, page_size }.
//
// Filters: pass filtersActive (true when any of the page's own filters is set) and
// onClearFilters (resets them). Then an empty result says "No matches" instead of
// emptyTitle (which is meant for a list that is truly empty) and offers a button
// that clears the search box and the filters.
import { useCallback, useEffect, useState } from 'react'
import SearchOutlined from '@mui/icons-material/SearchOutlined'
import {
  Box,
  Button,
  InputAdornment,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
} from '@mui/material'

import EmptyState from './EmptyState'
import ErrorMessage from './ErrorMessage'
import LoadingState from './LoadingState'

const SEARCH_DELAY_MS = 400 // wait until the user pauses typing before asking the server

// Why an empty result is empty, when a search or filters are in use.
function noMatchesMessage(search, filtersActive) {
  if (search && filtersActive) return `Nothing matches “${search}” with the selected filters.`
  if (search) return `Nothing matches “${search}”.`
  return 'Nothing matches the selected filters.'
}

// The "clear" button's label, or null when there is nothing the table can clear.
function clearLabel(search, canClearFilters) {
  if (search && canClearFilters) return 'Clear search and filters'
  if (search) return 'Clear search'
  if (canClearFilters) return 'Clear filters'
  return null
}

function parseSort(sort) {
  if (!sort) return { field: null, direction: 'asc' }
  return sort.startsWith('-')
    ? { field: sort.slice(1), direction: 'desc' }
    : { field: sort, direction: 'asc' }
}

export default function DataTable({
  columns,
  fetchRows,
  rowKey = 'id',
  defaultSort = null,
  searchable = true,
  searchPlaceholder = 'Search…',
  emptyTitle = 'No records found',
  emptyMessage,
  pageSizeOptions = [10, 20, 50],
  reloadKey = 0, // change this number to make the table fetch again (e.g. after saving)
  filtersActive = false, // true when any of the page's own filters (toolbar) is set
  onClearFilters = null, // () => reset the page's own filters; the table clears its search box itself
  toolbar = null, // extra controls shown next to the search box (e.g. filters)
  onRowClick = null, // optional: (row) => ... makes each row open something (mouse, Enter or Space)
  rowLabel = null, // optional: (row) => accessible name of a clickable row
}) {
  const [page, setPage] = useState(0) // MUI counts pages from 0; the server from 1
  const [pageSize, setPageSize] = useState(pageSizeOptions[1] ?? pageSizeOptions[0])
  const [sort, setSort] = useState(defaultSort)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [result, setResult] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [attempt, setAttempt] = useState(0)

  // Wait for a pause in typing, then search from page 1.
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(0)
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [searchInput])

  // New filters (a new fetchRows function): start again from page 1.
  useEffect(() => {
    setPage(0)
  }, [fetchRows])

  // Ask the server for the current page whenever paging, sorting or search changes.
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.resolve(fetchRows({ page: page + 1, pageSize, sort, search }))
      .then((data) => {
        if (!cancelled) setResult({ items: data?.items ?? [], total: data?.total ?? 0 })
      })
      .catch((err) => {
        if (!cancelled) setError(err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true // ignore answers to old requests
    }
  }, [fetchRows, page, pageSize, sort, search, reloadKey, attempt])

  const { field: sortField, direction } = parseSort(sort)

  const handleSort = useCallback(
    (field) => {
      // first click: ascending; second click: descending
      setSort(sortField === field && direction === 'asc' ? `-${field}` : field)
      setPage(0)
    },
    [sortField, direction],
  )

  const firstLoad = loading && result.items.length === 0 && !error

  return (
    <Paper variant="outlined">
      {searchable || toolbar ? (
        <Box sx={{ p: 2, pb: 1, display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          {searchable ? (
            <TextField
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={searchPlaceholder}
              size="small"
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchOutlined fontSize="small" />
                    </InputAdornment>
                  ),
                },
                htmlInput: { 'aria-label': 'Search' },
              }}
              sx={{ flex: '1 1 240px', maxWidth: 360 }}
            />
          ) : null}
          {toolbar}
        </Box>
      ) : null}

      {/* thin bar while refreshing, keeping the old rows visible */}
      <Box sx={{ height: 4 }}>{loading && !firstLoad ? <LinearProgress /> : null}</Box>

      {error ? (
        <Box sx={{ p: 2 }}>
          <ErrorMessage error={error} onRetry={() => setAttempt((n) => n + 1)} />
        </Box>
      ) : firstLoad ? (
        <LoadingState />
      ) : (
        <TableContainer sx={{ overflowX: 'auto' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                {columns.map((col) => (
                  <TableCell
                    key={col.field}
                    align={col.align}
                    sortDirection={sortField === col.field ? direction : false}
                    sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}
                  >
                    {col.sortable ? (
                      <TableSortLabel
                        active={sortField === col.field}
                        direction={sortField === col.field ? direction : 'asc'}
                        onClick={() => handleSort(col.field)}
                      >
                        {col.label}
                      </TableSortLabel>
                    ) : (
                      col.label
                    )}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {result.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={columns.length}>
                    {search || filtersActive ? (
                      <EmptyState
                        title="No matches"
                        message={noMatchesMessage(search, filtersActive)}
                        action={
                          clearLabel(search, filtersActive && onClearFilters) ? (
                            <Button
                              size="small"
                              onClick={() => {
                                setSearchInput('')
                                setSearch('')
                                setPage(0)
                                if (filtersActive) onClearFilters?.()
                              }}
                            >
                              {clearLabel(search, filtersActive && onClearFilters)}
                            </Button>
                          ) : null
                        }
                      />
                    ) : (
                      <EmptyState title={emptyTitle} message={emptyMessage} />
                    )}
                  </TableCell>
                </TableRow>
              ) : (
                result.items.map((row) => (
                  <TableRow
                    key={row[rowKey]}
                    hover
                    {...(onRowClick
                      ? {
                          onClick: () => onRowClick(row),
                          onKeyDown: (e) => {
                            if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
                              e.preventDefault()
                              onRowClick(row)
                            }
                          },
                          tabIndex: 0,
                          'aria-label': rowLabel ? rowLabel(row) : undefined,
                          sx: { cursor: 'pointer' },
                        }
                      : {})}
                  >
                    {columns.map((col) => (
                      <TableCell key={col.field} align={col.align}>
                        {col.render ? col.render(row) : row[col.field]}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <TablePagination
        component="div"
        count={result.total}
        page={page}
        onPageChange={(_e, newPage) => setPage(newPage)}
        rowsPerPage={pageSize}
        onRowsPerPageChange={(e) => {
          setPageSize(Number(e.target.value))
          setPage(0)
        }}
        rowsPerPageOptions={pageSizeOptions}
      />
    </Paper>
  )
}
