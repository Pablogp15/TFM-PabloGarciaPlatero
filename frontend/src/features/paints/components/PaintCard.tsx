import { WishlistButton } from '../../wishlist/WishlistButton'
import { useState } from 'react'

import { FINISH_LABELS, PAINT_TYPE_LABELS, type Paint } from '../types'
import { SimilarPaints } from './SimilarPaints'

interface PaintCardProps {
  paint: Paint
  distance?: number
  isAdding: boolean
  onAdd: (paint: Paint) => void
}

export function PaintCard({ paint, distance, isAdding, onAdd }: PaintCardProps) {
  const [showSimilar, setShowSimilar] = useState(false)

  return (
    <article className="paint-card">
      <div
        className="paint-card__swatch"
        style={{ backgroundColor: paint.hex }}
        aria-hidden="true"
      />

      <div className="paint-card__body">
        <div>
          <h2>{paint.name}</h2>
          <p className="paint-card__meta muted">
            {paint.brand} · {paint.range_name}
            {paint.code ? ` · ${paint.code}` : ''}
          </p>
        </div>

        <div className="badges">
          <span className="badge">{PAINT_TYPE_LABELS[paint.paint_type]}</span>
          <span className="badge">{FINISH_LABELS[paint.finish]}</span>
          {distance !== undefined && (
            <span className="badge" title="Distancia perceptual respecto al color elegido">
              Parecido ΔE {distance.toFixed(1)}
            </span>
          )}
        </div>

        <div className="paint-card__actions">
          <WishlistButton paintId={paint.id} name={paint.name} />
          <button className="button" type="button" onClick={() => onAdd(paint)} disabled={isAdding}>
            {isAdding ? 'Añadiendo…' : 'Añadir al inventario'}
          </button>
          <button
            className="button button--ghost"
            type="button"
            onClick={() => setShowSimilar((current) => !current)}
            aria-expanded={showSimilar}
          >
            {showSimilar ? 'Ocultar similares' : 'Similares'}
          </button>
        </div>

        {showSimilar && <SimilarPaints paintId={paint.id} />}
      </div>
    </article>
  )
}
