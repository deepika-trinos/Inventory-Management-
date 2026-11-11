// Which address shows which page.
//   /login                 : open to everyone
//   everything else        : must be logged in (RequireAuth)
//   each page in PAGES     : must also have an allowed role (RequireRole)
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
import { homePathFor, PAGES } from './navigation'
import RequireAuth from './RequireAuth'
import RequireRole from './RequireRole'

// Loaded only when opened, and left out of production builds entirely.
const ComponentGalleryPage = import.meta.env.DEV
  ? lazy(() => import('../pages/dev/ComponentGalleryPage'))
  : null

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

          {PAGES.map((page) => (
            <Route
              key={page.path}
              path={page.path}
              element={
                <RequireRole roles={page.roles}>
                  <ComingSoonPage page={page} />
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
