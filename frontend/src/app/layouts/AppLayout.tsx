import { Link, Outlet, useNavigate } from 'react-router-dom'

import { useLogout, useSession } from '../../features/auth/useAuth'

export function AppLayout() {
  const session = useSession()
  const logout = useLogout()
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      await logout.mutateAsync()
    } catch {
      // La sesión local se invalida igualmente en `onSettled`.
    } finally {
      navigate('/login', { replace: true })
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <Link className="app-brand" to="/">
          MiniPaint <span>AI</span>
        </Link>
        <nav className="app-nav" aria-label="Navegación principal">
          <Link to="/">Inicio</Link>
          {session.data ? (
            <>
              <Link to="/paints">Catálogo</Link>
              <Link to="/inventory">Inventario</Link>
              <Link to="/wishlist">Deseados</Link>
              <Link to="/projects">Proyectos</Link>
              <Link to="/guides">Guías</Link>
              <span className="app-user">{session.data.display_name}</span>
              <button
                className="button button--ghost"
                type="button"
                onClick={handleLogout}
                disabled={logout.isPending}
              >
                {logout.isPending ? 'Saliendo…' : 'Salir'}
              </button>
            </>
          ) : (
            <>
              <Link to="/login">Iniciar sesión</Link>
              <Link to="/register">Crear cuenta</Link>
            </>
          )}
        </nav>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <p>Trabajo de Fin de Máster · MiniPaint AI</p>
      </footer>
    </div>
  )
}
