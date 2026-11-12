import { Link } from 'react-router-dom'

import { useSession } from '../features/auth/useAuth'
import { useWishlistIds } from '../features/wishlist/useWishlist'
import { useInventoryStats } from '../features/inventory/useInventory'

export function DashboardPage() {
  const session = useSession()
  const stats = useInventoryStats()
  const wishlist = useWishlistIds()

  return (
    <section className="page">
      <h1>{session.data ? `Hola, ${session.data.display_name}` : 'MiniPaint AI'}</h1>
      <p className="page-lead">
        Plataforma de apoyo al pintado de miniaturas que combina inventario de pinturas, generación
        de imágenes y guías personalizadas.
      </p>

      <div className="stats-grid">
        <div className="stat">
          <span className="stat__value">{stats.data?.total_items ?? '—'}</span>
          <span className="stat__label">Pinturas distintas</span>
        </div>
        <div className="stat">
          <span className="stat__value">{stats.data?.total_quantity ?? '—'}</span>
          <span className="stat__label">Botes en total</span>
        </div>
        <div className="stat">
          <span className="stat__value">{stats.data?.running_low ?? '—'}</span>
          <span className="stat__label">Queda poco</span>
        </div>
        <div className="stat">
          <span className="stat__value">{wishlist.data?.length ?? '—'}</span>
          <span className="stat__label">Lista de deseos</span>
        </div>
      </div>

      <div className="card-grid">
        <article className="card">
          <h2>Catálogo de pinturas</h2>
          <p className="muted">
            Explora las pinturas de Vallejo, Green Stuff World y Citadel, filtra por marca o tipo y
            encuentra colores parecidos.
          </p>
          <Link className="button" to="/paints">
            Explorar catálogo
          </Link>
        </article>

        <article className="card">
          <h2>Mi inventario</h2>
          <p className="muted">
            Lleva la cuenta de los botes que tienes y marca los que están a punto de acabarse.
          </p>
          <Link className="button button--ghost" to="/inventory">
            Ver inventario
          </Link>
        </article>

        <article className="card">
          <h2>Lista de deseados</h2>
          <p className="muted">Guarda con el corazón las pinturas que te interesan.</p>
          <Link className="button button--ghost" to="/wishlist">
            Ver deseados
          </Link>
        </article>
        <article className="card">
          <h2>Mis proyectos</h2>
          <p className="muted">
            Crea proyectos para tus miniaturas, define su esquema de color y guarda imágenes de
            origen y de avance.
          </p>
          <Link className="button button--ghost" to="/projects">
            Ver proyectos
          </Link>
        </article>
      </div>

      <div className="card">
        <h2>Estado del proyecto</h2>
        <p>
          La base de datos, las migraciones, la autenticación, el catálogo con inventario y la
          gestión de proyectos con sus imágenes ya están operativos. Puedes generar imágenes con
          Qwen desde tus proyectos cuando el servicio local esté iniciado. Las guías asistidas se
          incorporarán en las siguientes fases.
        </p>
      </div>
    </section>
  )
}
