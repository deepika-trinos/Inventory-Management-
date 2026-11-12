// ONE list of every page in the app: its address, menu label, icon and which
// roles may open it. Both the sidebar menu and the route protection read this
// list, so they can never disagree.
//
// Reminder: hiding a page here is only for convenience. The SERVER checks the
// role on every request (backend require_roles), which is the real protection.
import AssignmentIndOutlined from '@mui/icons-material/AssignmentIndOutlined'
import BadgeOutlined from '@mui/icons-material/BadgeOutlined'
import BuildOutlined from '@mui/icons-material/BuildOutlined'
import CategoryOutlined from '@mui/icons-material/CategoryOutlined'
import DashboardOutlined from '@mui/icons-material/DashboardOutlined'
import DevicesOutlined from '@mui/icons-material/DevicesOutlined'
import HistoryOutlined from '@mui/icons-material/HistoryOutlined'
import Inventory2Outlined from '@mui/icons-material/Inventory2Outlined'
import LaptopOutlined from '@mui/icons-material/LaptopOutlined'
import ManageAccountsOutlined from '@mui/icons-material/ManageAccountsOutlined'
import ReportProblemOutlined from '@mui/icons-material/ReportProblemOutlined'
import ShoppingCartOutlined from '@mui/icons-material/ShoppingCartOutlined'
import StorefrontOutlined from '@mui/icons-material/StorefrontOutlined'
import SummarizeOutlined from '@mui/icons-material/SummarizeOutlined'

export const ROLES = {
  ADMIN: 'Admin',
  IT_MANAGER: 'IT Manager',
  EMPLOYEE: 'Employee',
}

const STAFF = [ROLES.ADMIN, ROLES.IT_MANAGER]
const ADMIN_ONLY = [ROLES.ADMIN]
const EMPLOYEE_ONLY = [ROLES.EMPLOYEE]

// Order here = order in the sidebar.
export const PAGES = [
  { path: '/dashboard', label: 'Dashboard', icon: DashboardOutlined, roles: STAFF, slice: 'Phase 7' },
  { path: '/assets', label: 'Assets', icon: DevicesOutlined, roles: STAFF, slice: 'Phase 4' },
  { path: '/inventory', label: 'Inventory', icon: Inventory2Outlined, roles: STAFF, slice: 'Phase 4' },
  { path: '/categories', label: 'Categories', icon: CategoryOutlined, roles: STAFF, slice: 'Slice 2.1' },
  { path: '/vendors', label: 'Vendors', icon: StorefrontOutlined, roles: STAFF, slice: 'Slice 2.3' },
  { path: '/purchases', label: 'Purchases', icon: ShoppingCartOutlined, roles: STAFF, slice: 'Phase 3' },
  { path: '/employees', label: 'Employees', icon: BadgeOutlined, roles: STAFF, slice: 'Slice 2.2' },
  { path: '/assignments', label: 'Assignments', icon: AssignmentIndOutlined, roles: STAFF, slice: 'Phase 5' },
  { path: '/maintenance', label: 'Maintenance', icon: BuildOutlined, roles: STAFF, slice: 'Phase 6' },
  { path: '/reports', label: 'Reports', icon: SummarizeOutlined, roles: STAFF, slice: 'Phase 7' },
  { path: '/users', label: 'Users', icon: ManageAccountsOutlined, roles: ADMIN_ONLY, slice: 'Slice 1.6' },
  { path: '/audit-log', label: 'Audit Log', icon: HistoryOutlined, roles: ADMIN_ONLY, slice: 'Slice 8.1' },

  { path: '/my/dashboard', label: 'My Dashboard', icon: DashboardOutlined, roles: EMPLOYEE_ONLY, slice: 'Slice 6.4' },
  { path: '/my/assets', label: 'My Assets', icon: LaptopOutlined, roles: EMPLOYEE_ONLY, slice: 'Slice 6.4' },
  { path: '/my/requests', label: 'My Requests', icon: ReportProblemOutlined, roles: EMPLOYEE_ONLY, slice: 'Slice 6.4' },
]

export function pagesForRole(role) {
  return PAGES.filter((page) => page.roles.includes(role))
}

export function canOpen(role, path) {
  const page = PAGES.find((p) => p.path === path)
  return Boolean(page && page.roles.includes(role))
}

// Where each role lands after logging in.
export function homePathFor(role) {
  return role === ROLES.EMPLOYEE ? '/my/dashboard' : '/dashboard'
}
