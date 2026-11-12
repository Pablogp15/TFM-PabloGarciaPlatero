import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { RequireAuth } from '../features/auth/RequireAuth'
import { DashboardPage } from '../pages/DashboardPage'
import { GuidesPage } from '../pages/GuidesPage'
import { WishlistPage } from '../pages/WishlistPage'
import { InventoryPage } from '../pages/InventoryPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { PaintsPage } from '../pages/PaintsPage'
import { ProjectDetailPage } from '../pages/ProjectDetailPage'
import { ProjectsPage } from '../pages/ProjectsPage'
import { RegisterPage } from '../pages/RegisterPage'
import { AppLayout } from './layouts/AppLayout'

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: (
          <RequireAuth>
            <DashboardPage />
          </RequireAuth>
        ),
      },
      {
        path: 'paints',
        element: (
          <RequireAuth>
            <PaintsPage />
          </RequireAuth>
        ),
      },
      {
        path: 'inventory',
        element: (
          <RequireAuth>
            <InventoryPage />
          </RequireAuth>
        ),
      },
      {
        path: 'wishlist',
        element: (
          <RequireAuth>
            <WishlistPage />
          </RequireAuth>
        ),
      },
      {
        path: 'guides',
        element: (
          <RequireAuth>
            <GuidesPage />
          </RequireAuth>
        ),
      },
      {
        path: 'projects',
        element: (
          <RequireAuth>
            <ProjectsPage />
          </RequireAuth>
        ),
      },
      {
        path: 'projects/:projectId',
        element: (
          <RequireAuth>
            <ProjectDetailPage />
          </RequireAuth>
        ),
      },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
