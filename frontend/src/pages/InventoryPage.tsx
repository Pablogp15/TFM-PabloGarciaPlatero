import { useDeferredValue, useState } from 'react'
import { Link } from 'react-router-dom'

import { type InventoryFilters, type InventoryItem } from '../features/inventory/types'
import {
  useDeleteInventoryItem,
  useInventory,
  useInventoryStats,
  useUpdateInventoryItem,
} from '../features/inventory/useInventory'
import { describeError } from '../lib/http'

const PAGE_SIZE = 20

export function InventoryPage() {
  const [runningLow, setRunningLow] = useState(false)
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const deferredQuery = useDeferredValue(query)

  const filters: InventoryFilters = {
    running_low: runningLow || undefined,
    q: deferredQuery.trim() || undefined,
    limit: PAGE_SIZE,
    offset,
  }

  const inventory = useInventory(filters)
  const stats = useInventoryStats()
  const update = useUpdateInventoryItem()
  const remove = useDeleteInventoryItem()

  const items = inventory.data?.items ?? []
  const total = inventory.data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1
  const mutationError = update.error ?? remove.error

  function changeQuantity(item: InventoryItem, delta: number) {
    const next = Math.min(999, Math.max(0, item.quantity + delta))
    if (next !== item.quantity) {
      update.mutate({ id: item.id, payload: { quantity: next } })
    }
  }

  function handleDelete(id: string) {
    setConfirmId(null)
    // Si se elimina el único elemento de una página posterior, se retrocede
    // para no dejar al usuario en una página vacía.
    if (items.length === 1 && offset > 0) {
      setOffset(Math.max(0, offset - PAGE_SIZE))
    }
    remove.mutate(id)
  }

  const statCards = [
    { label: 'Pinturas distintas', value: stats.data?.total_items },
    { label: 'Botes', value: stats.data?.total_quantity },
    { label: 'Queda poco', value: stats.data?.running_low },
    { label: 'Marcas', value: stats.data?.brands },
  ]

  const hasFilters = Boolean(runningLow || query)

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Mi inventario</h1>
          <p className="page-lead">
            Controla las pinturas que tienes y marca las que están a punto de acabarse.
          </p>
        </div>
        <Link className="button" to="/paints">
          Explorar catálogo
        </Link>
      </div>

      <div className="stats-grid">
        {statCards.map((card) => (
          <div className="stat" key={card.label}>
            <span className="stat__value">{card.value ?? '—'}</span>
            <span className="stat__label">{card.label}</span>
          </div>
        ))}
      </div>

      <div className="filters">
        <label className="filter-field filter-field--search">
          <span>Buscar</span>
          <input
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setOffset(0)
            }}
            placeholder="Nombre, marca o código"
          />
        </label>

        <label className="filter-field">
          <span>Disponibilidad</span>
          <select
            value={runningLow ? 'low' : ''}
            onChange={(event) => {
              setRunningLow(event.target.value === 'low')
              setOffset(0)
            }}
          >
            <option value="">Todas mis pinturas</option>
            <option value="low">Solo las que queda poco</option>
          </select>
        </label>

        {hasFilters && (
          <button
            className="button button--ghost filter-clear"
            type="button"
            onClick={() => {
              setRunningLow(false)
              setQuery('')
              setOffset(0)
            }}
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {mutationError && (
        <p className="form-error" role="alert">
          {describeError(mutationError)}
        </p>
      )}

      {inventory.isPending ? (
        <p className="muted">Cargando inventario…</p>
      ) : inventory.error ? (
        <p className="form-error" role="alert">
          {describeError(inventory.error)}
        </p>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p>
            {hasFilters
              ? 'No hay pinturas que coincidan con los filtros.'
              : 'Todavía no has añadido ninguna pintura.'}
          </p>
          <Link className="button" to="/paints">
            Ir al catálogo
          </Link>
        </div>
      ) : (
        <>
          {inventory.isFetching && <p className="muted">Actualizando…</p>}

          <ul className="inventory-list">
            {items.map((item) => {
              const updating = update.isPending && update.variables?.id === item.id
              const deleting = remove.isPending && remove.variables === item.id

              return (
                <li className="inventory-item" key={item.id}>
                  <span
                    className="swatch"
                    style={{ backgroundColor: item.paint.hex }}
                    aria-hidden="true"
                  />

                  <div className="inventory-item__info">
                    <strong>{item.paint.name}</strong>
                    <span className="muted">
                      {item.paint.brand} · {item.paint.range_name}
                      {item.paint.code ? ` · ${item.paint.code}` : ''}
                    </span>
                    {item.notes && <span className="inventory-item__notes">{item.notes}</span>}
                  </div>

                  <div className="quantity" aria-label={`Cantidad de ${item.paint.name}`}>
                    <button
                      className="quantity__button"
                      type="button"
                      onClick={() => changeQuantity(item, -1)}
                      disabled={updating || item.quantity === 0}
                      aria-label="Quitar un bote"
                    >
                      −
                    </button>
                    <span className="quantity__value">{item.quantity}</span>
                    <button
                      className="quantity__button"
                      type="button"
                      onClick={() => changeQuantity(item, 1)}
                      disabled={updating || item.quantity >= 999}
                      aria-label="Añadir un bote"
                    >
                      +
                    </button>
                  </div>

                  <button
                    className="button button--ghost low-stock-button"
                    type="button"
                    aria-pressed={item.running_low}
                    aria-label={`Queda poco de ${item.paint.name}`}
                    disabled={update.isPending}
                    onClick={() =>
                      update.mutate({ id: item.id, payload: { running_low: !item.running_low } })
                    }
                  >
                    {item.running_low ? '● Queda poco' : 'Marcar que queda poco'}
                  </button>

                  <div className="inventory-item__actions">
                    {confirmId === item.id ? (
                      <>
                        <button
                          className="button button--danger"
                          type="button"
                          onClick={() => handleDelete(item.id)}
                          disabled={deleting}
                        >
                          {deleting ? 'Quitando…' : 'Confirmar'}
                        </button>
                        <button
                          className="button button--ghost"
                          type="button"
                          onClick={() => setConfirmId(null)}
                        >
                          Cancelar
                        </button>
                      </>
                    ) : (
                      <button
                        className="button button--ghost"
                        type="button"
                        onClick={() => setConfirmId(item.id)}
                      >
                        Quitar
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>

          <nav className="pagination" aria-label="Paginación del inventario">
            <button
              className="button button--ghost"
              type="button"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
            >
              Anterior
            </button>
            <span className="muted">
              Página {currentPage} de {pageCount} · {total} pinturas
            </span>
            <button
              className="button button--ghost"
              type="button"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
            >
              Siguiente
            </button>
          </nav>
        </>
      )}
    </section>
  )
}
