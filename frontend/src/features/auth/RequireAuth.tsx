import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useSession } from './useAuth'

interface RequireAuthProps {
  children: ReactNode
}

/** Redirige al inicio de sesión si no hay una sesión válida. */
export function RequireAuth({ children }: RequireAuthProps) {
  const location = useLocation()
  const session = useSession()

  if (session.isPending) {
    return <p className="muted">Comprobando sesión…</p>
  }

  if (!session.data) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}
