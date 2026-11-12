import { describeError } from '../../../lib/http'
import { useSimilarPaints } from '../usePaints'

interface SimilarPaintsProps {
  paintId: string
}

export function SimilarPaints({ paintId }: SimilarPaintsProps) {
  const query = useSimilarPaints(paintId)

  if (query.isPending) {
    return <p className="similar-status muted">Buscando colores parecidos…</p>
  }

  if (query.error) {
    return (
      <p className="form-error" role="alert">
        {describeError(query.error)}
      </p>
    )
  }

  if (!query.data?.length) {
    return <p className="similar-status muted">No hay otros colores en el catálogo.</p>
  }

  return (
    <div className="similar">
      <p className="similar-title">Colores parecidos</p>
      <ul className="similar-list">
        {query.data.map(({ paint, distance }) => (
          <li className="similar-item" key={paint.id}>
            <span
              className="similar-swatch"
              style={{ backgroundColor: paint.hex }}
              aria-hidden="true"
            />
            <span className="similar-name">{paint.name}</span>
            <span className="similar-meta muted">
              {paint.brand} · ΔE {distance.toFixed(1)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
