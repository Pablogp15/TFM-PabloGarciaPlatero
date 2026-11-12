import {
  FINISH_LABELS,
  FINISH_TYPES,
  PAINT_TYPE_LABELS,
  PAINT_TYPES,
  type PaintFacets,
} from '../types'

export type PaintFilterField = 'q' | 'brand' | 'rangeName' | 'paintType' | 'finish'

export interface PaintFilterValues {
  q: string
  brand: string
  rangeName: string
  paintType: string
  finish: string
}

interface PaintFiltersBarProps {
  values: PaintFilterValues
  facets: PaintFacets | undefined
  onChange: (field: PaintFilterField, value: string) => void
  onClear: () => void
}

export function PaintFiltersBar({ values, facets, onChange, onClear }: PaintFiltersBarProps) {
  const ranges = (facets?.ranges ?? []).filter(
    (range) => !values.brand || range.brand === values.brand,
  )
  const hasFilters = Object.values(values).some(Boolean)

  return (
    <div className="filters">
      <label className="filter-field filter-field--search">
        <span>Buscar</span>
        <input
          type="search"
          value={values.q}
          onChange={(event) => onChange('q', event.target.value)}
          placeholder="Nombre, marca o código"
        />
      </label>

      <label className="filter-field">
        <span>Marca</span>
        <select value={values.brand} onChange={(event) => onChange('brand', event.target.value)}>
          <option value="">Todas</option>
          {(facets?.brands ?? []).map((brand) => (
            <option key={brand} value={brand}>
              {brand}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-field">
        <span>Gama</span>
        <select
          value={values.rangeName}
          onChange={(event) => onChange('rangeName', event.target.value)}
        >
          <option value="">Todas</option>
          {ranges.map((range) => (
            <option key={`${range.brand}-${range.range_name}`} value={range.range_name}>
              {range.brand} · {range.range_name}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-field">
        <span>Tipo</span>
        <select
          value={values.paintType}
          onChange={(event) => onChange('paintType', event.target.value)}
        >
          <option value="">Todos</option>
          {PAINT_TYPES.map((type) => (
            <option key={type} value={type}>
              {PAINT_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </label>

      <label className="filter-field">
        <span>Acabado</span>
        <select value={values.finish} onChange={(event) => onChange('finish', event.target.value)}>
          <option value="">Todos</option>
          {FINISH_TYPES.map((finish) => (
            <option key={finish} value={finish}>
              {FINISH_LABELS[finish]}
            </option>
          ))}
        </select>
      </label>

      {hasFilters && (
        <button className="button button--ghost filter-clear" type="button" onClick={onClear}>
          Limpiar filtros
        </button>
      )}
    </div>
  )
}
