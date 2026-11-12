import { useState } from 'react'

import { levels, manualVersion, techniques, type Technique } from '../features/techniques/catalog'
import { TechniqueDialog } from '../features/techniques/TechniqueDialog'
import { TechniqueIllustration } from '../features/techniques/TechniqueIllustration'

export function GuidesPage() {
  const [selected, setSelected] = useState<Technique | null>(null)

  return (
    <section className="page guides-library">
      <header className="guides-library__header">
        <span className="guides-library__eyebrow">Aprende a pintar</span>
        <h1>Guías de técnicas</h1>
        <p className="page-lead">
          Desde preparar tu primera miniatura hasta dominar luces y reflejos. Elige una tarjeta para
          ver cómo hacerlo, qué evitar y cuándo continuar.
        </p>
        <p className="muted">
          {techniques.length} técnicas · De inicial a avanzado · Ilustraciones orientativas
        </p>
      </header>

      {levels.map((level, index) => (
        <section className="technique-section" key={level.id} aria-labelledby={`level-${level.id}`}>
          <div className="technique-section__heading">
            <span className="technique-section__number" aria-hidden="true">
              0{index + 1}
            </span>
            <div>
              <h2 id={`level-${level.id}`}>{level.label}</h2>
              <p className="muted">{level.description}</p>
            </div>
          </div>
          <div className="technique-grid">
            {techniques
              .filter((technique) => technique.difficulty === level.id)
              .map((technique) => (
                <button
                  type="button"
                  className="technique-card"
                  key={technique.id}
                  aria-haspopup="dialog"
                  onClick={() => setSelected(technique)}
                >
                  <TechniqueIllustration technique={technique} />
                  <span className="technique-card__body">
                    <span className={`technique-level technique-level--${level.id}`}>
                      {level.label}
                    </span>
                    <span className="technique-card__title">{technique.title}</span>
                    <span className="technique-card__summary">{technique.summary}</span>
                    <span className="technique-card__action">
                      Leer técnica <span aria-hidden="true">↗</span>
                    </span>
                  </span>
                </button>
              ))}
          </div>
        </section>
      ))}

      <p className="technique-review">
        Manual v{manualVersion}, elaborado con asistencia de IA. Contenido pendiente de revisión
        práctica por expertos; respeta las instrucciones de cada herramienta y producto.
      </p>
      {selected && <TechniqueDialog technique={selected} onClose={() => setSelected(null)} />}
    </section>
  )
}
