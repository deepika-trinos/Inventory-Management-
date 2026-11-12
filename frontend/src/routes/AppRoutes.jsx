// Which address shows which page.
//   /login                 : open to everyone
//   everything else        : must be logged in (RequireAuth)
//   each page in PAGES     : must also have an allowed role (RequireRole)
//   DETAIL_PAGES           : pages under a menu page (e.g. /vendors/12), same roles as that page
//   /                      : sends you to your role's home page
//   /dev/components        : component gallery, development builds only
import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router'

import LoadingState from '../components/LoadingState'
import { useAuth } from '../context/AuthContext'
import MainLayout from '../layouts/MainLayout'
import ComingSoonPage from '../pages/ComingSoonPage'
import LoginPage from '../pages/LoginPage'
import NotFoundPage from '../pages/NotFoundPage'
import CategoriesPage from '../pages/categories/CategoriesPage'
import EmployeesPage from '../pages/employees/EmployeesPage'
import InventoryPage from '../pages/inventory/InventoryPage'
import UsersPage from '../pages/users/UsersPage'
import VendorDetailPage from '../pages/vendors/VendorDetailPage'
import VendorsPage from '../pages/vendors/VendorsPage'
import { homePathFor, PAGES } from './navigation'
import RequireAuth from './RequireAuth'
import RequireRole from './RequireRole'

// Loaded only when opened, and left out of production builds entirely.
const ComponentGalleryPage = import.meta.env.DEV
  ? lazy(() => import('../pages/dev/ComponentGalleryPage'))
  : null

// Pages that are built. Every other page in PAGES shows "Coming soon".
const BUILT_PAGES = {
  '/categories': CategoriesPage,
  '/employees': EmployeesPage,
  '/inventory': InventoryPage,
  '/users': UsersPage,
  '/vendors': VendorsPage,
}

// Detail pages: not in the menu; they use the roles of their menu page (parent).
const DETAIL_PAGES = [{ path: '/vendors/:vendorId', parent: '/vendors', Page: VendorDetailPage }]

function HomeRedirect() {
  const { role } = useAuth()
  return <Navigate to={homePathFor(role)} replace />
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<MainLayout />}>
          <Route index element={<HomeRedirect />} />

          {PAGES.map((page) => {
            const Page = BUILT_PAGES[page.path]
            return (
              <Route
                key={page.path}
                path={page.path}
                element={
                  <RequireRole roles={page.roles}>
                    {Page ? <Page /> : <ComingSoonPage page={page} />}
                  </RequireRole>
                }
              />
            )
          })}

          {DETAIL_PAGES.map(({ path, parent, Page }) => (
            <Route
              key={path}
              path={path}
              element={
                <RequireRole roles={PAGES.find((p) => p.path === parent).roles}>
                  <Page />
                </RequireRole>
              }
            />
          ))}

          {ComponentGalleryPage ? (
            <Route
              path="/dev/components"
              element={
                <Suspense fallback={<LoadingState />}>
                  <ComponentGalleryPage />
                </Suspense>
              }
            />
          ) : null}

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  )
}
