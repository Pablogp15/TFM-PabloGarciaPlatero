import { useDeferredValue, useState } from 'react'
import { Link } from 'react-router-dom'

import { useAddInventoryItem } from '../features/inventory/useInventory'
import { PaintCard } from '../features/paints/components/PaintCard'
import {
  PaintFiltersBar,
  type PaintFilterField,
  type PaintFilterValues,
} from '../features/paints/components/PaintFiltersBar'
import { PaintColorSearch } from '../features/paints/components/PaintColorSearch'
import type { FinishType, Paint, PaintFilters, PaintType } from '../features/paints/types'
import { usePaintFacets, usePaints, usePaintsByColor } from '../features/paints/usePaints'
import { describeError } from '../lib/http'

const PAGE_SIZE = 24

const EMPTY_FILTERS: PaintFilterValues = {
  q: '',
  brand: '',
  rangeName: '',
  paintType: '',
  finish: '',
}

export function PaintsPage() {
  const [filterValues, setFilterValues] = useState<PaintFilterValues>(EMPTY_FILTERS)
  const [colorHex, setColorHex] = useState('')
  const [offset, setOffset] = useState(0)
  const deferredQuery = useDeferredValue(filterValues.q)

  const filters: PaintFilters = {
    q: deferredQuery.trim() || undefined,
    brand: filterValues.brand || undefined,
    range_name: filterValues.rangeName || undefined,
    paint_type: filterValues.paintType ? (filterValues.paintType as PaintType) : undefined,
    finish: filterValues.finish ? (filterValues.finish as FinishType) : undefined,
    limit: PAGE_SIZE,
    offset,
  }

  const paints = usePaints(filters)
  const colorPaints = usePaintsByColor(
    {
      hex_color: colorHex,
      q: filters.q,
      brand: filters.brand,
      range_name: filters.range_name,
      paint_type: filters.paint_type,
      finish: filters.finish,
      limit: PAGE_SIZE,
      offset,
    },
    Boolean(colorHex),
  )
  const facets = usePaintFacets()
  const add = useAddInventoryItem()

  const activeQuery = colorHex ? colorPaints : paints
  const items = colorHex
    ? (colorPaints.data?.items ?? []).map((item) => item.paint)
    : (paints.data?.items ?? [])
  const distances = new Map(
    (colorPaints.data?.items ?? []).map(({ paint, distance }) => [paint.id, distance]),
  )
  const total = activeQuery.data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  function handleFilterChange(field: PaintFilterField, value: string) {
    setOffset(0)
    setFilterValues((current) => {
      if (field === 'brand') {
        return { ...current, brand: value, rangeName: '' }
      }
      return { ...current, [field]: value }
    })
  }

  function handleClearFilters() {
    setFilterValues(EMPTY_FILTERS)
    setColorHex('')
    setOffset(0)
  }

  function handleColorSearch(hex: string | undefined) {
    setColorHex(hex ?? '')
    setOffset(0)
  }

  function handleAdd(paint: Paint) {
    add.mutate({ paint_id: paint.id })
  }

  const hasFilters = Object.values(filterValues).some(Boolean) || Boolean(colorHex)

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Catálogo de pinturas</h1>
          <p className="page-lead">
            Consulta las pinturas disponibles y añade a tu inventario las que ya tengas.
          </p>
        </div>
        <Link className="button button--ghost" to="/inventory">
          Ver mi inventario
        </Link>
      </div>

      <PaintFiltersBar
        values={filterValues}
        facets={facets.data}
        onChange={handleFilterChange}
        onClear={handleClearFilters}
      />
      <PaintColorSearch key={colorHex} value={colorHex} onSearch={handleColorSearch} />

      {add.isSuccess && add.data && (
        <p className="form-success" role="status">
          Añadida al inventario: {add.data.paint.name}
        </p>
      )}
      {add.error && (
        <p className="form-error" role="alert">
          {describeError(add.error)}
        </p>
      )}

      {activeQuery.isPending ? (
        <p className="muted">{colorHex ? 'Buscando colores aproximados…' : 'Cargando catálogo…'}</p>
      ) : activeQuery.error ? (
        <p className="form-error" role="alert">
          {describeError(activeQuery.error)}
        </p>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p>No hay pinturas que coincidan con los filtros.</p>
          {hasFilters && (
            <button className="button button--ghost" type="button" onClick={handleClearFilters}>
              Limpiar filtros
            </button>
          )}
        </div>
      ) : (
        <>
          {activeQuery.isFetching && <p className="muted">Actualizando…</p>}
          {colorHex && (
            <p className="muted paint-color-search__summary">
              Pinturas ordenadas por parecido con <strong>{colorHex}</strong>. ΔE menor indica un
              color más cercano.
            </p>
          )}

          <div className="paint-grid">
            {items.map((paint) => (
              <PaintCard
                key={paint.id}
                paint={paint}
                distance={colorHex ? distances.get(paint.id) : undefined}
                onAdd={handleAdd}
                isAdding={add.isPending && add.variables?.paint_id === paint.id}
              />
            ))}
          </div>

          <nav className="pagination" aria-label="Paginación del catálogo">
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
