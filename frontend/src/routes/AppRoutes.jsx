// The list of pages and their web addresses. Slice 1.5 adds /login and
// role-protected routes here.
import { Route, Routes } from 'react-router'

import MainLayout from '../layouts/MainLayout'
import HomePage from '../pages/HomePage'
import NotFoundPage from '../pages/NotFoundPage'

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route index element={<HomePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
