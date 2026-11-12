import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useAddInventoryItem } from '../features/inventory/useInventory'
import { PaintCard } from '../features/paints/components/PaintCard'
import { useWishlist } from '../features/wishlist/useWishlist'
import { describeError } from '../lib/http'

export function WishlistPage() {
  const [offset, setOffset] = useState(0)
  const wishlist = useWishlist(offset)
  const add = useAddInventoryItem()
  const items = wishlist.data?.items ?? []
  const total = wishlist.data?.total ?? 0
  // Al quitar el último deseo de una página, ofrecer volver a la anterior.
  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Lista de deseados</h1>
          <p className="page-lead">
            Las pinturas que has guardado con el corazón. Añadirlas al inventario conserva tu
            selección de deseados.
          </p>
        </div>
        <Link className="button" to="/paints">
          Explorar catálogo
        </Link>
      </div>
      {add.isSuccess && (
        <p className="form-success" role="status">
          Añadida al inventario: {add.data.paint.name}
        </p>
      )}
      {(wishlist.error || add.error) && (
        <p className="form-error" role="alert">
          {describeError(wishlist.error ?? add.error)}
        </p>
      )}
      {wishlist.isPending ? (
        <p className="muted">Cargando deseados…</p>
      ) : (
        !wishlist.error && (
          <>
            {items.length === 0 ? (
              <div className="empty-state">
                <p>
                  No hay pinturas en esta página de deseados. Usa el corazón del catálogo para
                  guardarlas.
                </p>
              </div>
            ) : (
              <div className="paint-grid">
                {items.map(({ paint }) => (
                  <PaintCard
                    key={paint.id}
                    paint={paint}
                    onAdd={(value) => add.mutate({ paint_id: value.id })}
                    isAdding={add.isPending}
                  />
                ))}
              </div>
            )}
            <nav className="pagination" aria-label="Paginación de deseados">
              <button
                className="button button--ghost"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - 24))}
              >
                Anterior
              </button>
              <span className="muted">
                {total} pinturas · Página {Math.floor(offset / 24) + 1}
              </span>
              <button
                className="button button--ghost"
                disabled={offset + 24 >= total}
                onClick={() => setOffset(offset + 24)}
              >
                Siguiente
              </button>
            </nav>
          </>
        )
      )}
    </section>
  )
}
