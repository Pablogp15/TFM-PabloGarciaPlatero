import { useState, type FormEvent } from 'react'
import { useProjectImages } from '../projects/useProjects'
import { describeError } from '../../lib/http'
import type { Guide, GuideStep, StepProgress } from './api'
import { useGuideActions, useGuides } from './useGuides'

const STAGES: Record<string, string> = {
  queued: 'En cola',
  analysis: 'Analizando imagen',
  retrieval: 'Buscando información',
  writing: 'Redactando guía',
  validation: 'Validando guía',
  done: 'Borrador de guía disponible',
  failed: 'No se pudo completar',
  cancelled: 'Cancelada',
}

export function GuidePanel({ projectId }: { projectId: string }) {
  const [imageId, setImageId] = useState('')
  const query = useGuides(projectId)
  const images = useProjectImages(projectId)
  const actions = useGuideActions(projectId)
  const active = query.data?.items.some((guide) => ['pending', 'generating'].includes(guide.status))
  const error =
    query.error ??
    images.error ??
    actions.create.error ??
    actions.cancel.error ??
    actions.progress.error
  return (
    <div className="guide-panel">
      <p>Guías basadas en tus documentos y las pinturas disponibles en tu inventario.</p>
      {query.isPending && <p className="muted">Cargando guías…</p>}
      {query.data && !query.data.corpus_ready && (
        <p role="status">
          Falta preparar el conocimiento de pintado. Importa tus documentos antes de generar guías.
        </p>
      )}
      {error && (
        <p className="form-error" role="alert">
          {describeError(error)}
        </p>
      )}
      <label className="field">
        <span>Imagen objetivo para la guía</span>
        <select value={imageId} onChange={(event) => setImageId(event.target.value)}>
          <option value="">Selecciona una imagen del proyecto</option>
          {images.data?.items.map((image) => (
            <option key={image.id} value={image.id}>
              {image.kind === 'generated'
                ? 'Propuesta generada'
                : image.kind === 'source'
                  ? 'Imagen de origen'
                  : 'Imagen de avance'}{' '}
              · {new Date(image.created_at).toLocaleString()}
            </option>
          ))}
        </select>
      </label>
      <button
        className="button"
        type="button"
        disabled={!imageId || !query.data?.corpus_ready || active || actions.create.isPending}
        onClick={() => actions.create.mutate(imageId)}
      >
        {actions.create.isPending ? 'Enviando…' : 'Generar guía'}
      </button>
      {query.data?.items.map((guide) => (
        <article className="card" key={guide.id}>
          <h3>{STAGES[guide.stage] ?? 'Preparando guía'}</h3>
          <p className="muted">{new Date(guide.created_at).toLocaleString()}</p>
          {['pending', 'generating'].includes(guide.status) && (
            <button
              className="button button--ghost"
              disabled={guide.cancel_requested || actions.cancel.isPending}
              onClick={() => actions.cancel.mutate(guide.id)}
            >
              {guide.cancel_requested ? 'Cancelación solicitada…' : 'Cancelar guía'}
            </button>
          )}
          {guide.error_message && <p role="alert">{guide.error_message}</p>}
          {guide.summary && <p>{guide.summary}</p>}
          {guide.status === 'ready' && (
            <p className="field-hint">
              Propuesta generada automáticamente. Revisa las pinturas, sus acabados y las fuentes de
              cada paso antes de aplicarlo: puede contener errores y no garantiza reproducir los
              colores de la imagen.
            </p>
          )}
          {guide.limitations.length > 0 && (
            <div>
              <strong>Limitaciones</strong>
              <ul>
                {guide.limitations.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {guide.unavailable_paint_ids.length > 0 && (
            <p role="status">
              Algunas pinturas utilizadas ya no están disponibles en tu inventario. Revisa los pasos
              antes de continuar.
            </p>
          )}
          {guide.steps.map((step) => (
            <Step
              key={step.id}
              guide={guide}
              step={step}
              pending={actions.progress.isPending}
              save={(body) => actions.progress.mutate({ guideId: guide.id, stepId: step.id, body })}
            />
          ))}
        </article>
      ))}
    </div>
  )
}

function Step({
  guide,
  step,
  pending,
  save,
}: {
  guide: Guide
  step: GuideStep
  pending: boolean
  save: (body: StepProgress) => void
}) {
  const [completed, setCompleted] = useState(step.completed)
  const [note, setNote] = useState(step.progress_note ?? '')
  const [minutes, setMinutes] = useState(step.minutes_spent)
  function submit(event: FormEvent) {
    event.preventDefault()
    save({ completed, note: note.trim() || null, minutes_spent: minutes })
  }
  return (
    <details className="guide-step">
      <summary>
        {step.completed ? '✓ ' : ''}
        {step.position}. {step.title}
        {step.is_optional ? ' (opcional)' : ''}
      </summary>
      <p>
        <strong>{step.zone}:</strong> {step.objective}
      </p>
      <p>{step.description}</p>
      <p>
        <strong>Continúa cuando:</strong> {step.continue_when}
      </p>
      {step.time_minutes !== null && <p>Tiempo estimado de trabajo: {step.time_minutes} min.</p>}
      <ul>
        {step.paint_ids.map((id) => {
          const paint = guide.context.inventory?.find((paint) => paint.id === id)
          return (
            <li key={id}>
              {paint ? `${paint.brand} · ${paint.name}` : 'Pintura de la guía'}
              {paint?.running_low ? ' · Queda poco' : ''}
              {guide.unavailable_paint_ids.includes(id) ? ' · Ya no disponible' : ''}
            </li>
          )
        })}
      </ul>
      <details>
        <summary>Fuentes de este paso</summary>
        {guide.sources
          .filter((source) => step.source_ids.includes(source.id))
          .map((source) => (
            <blockquote key={source.id}>
              <strong>
                {source.title} · {source.metadata.location}
              </strong>
              <p>{source.content}</p>
              <p className="muted">{source.metadata.source}</p>
            </blockquote>
          ))}
      </details>
      <form onSubmit={submit}>
        <label>
          <input
            type="checkbox"
            checked={completed}
            onChange={(event) => setCompleted(event.target.checked)}
          />{' '}
          Paso completado
        </label>
        <label className="field">
          <span>Notas del paso</span>
          <textarea
            maxLength={2000}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>
        <label className="field">
          <span>Minutos dedicados</span>
          <input
            type="number"
            min={0}
            max={32767}
            required
            value={minutes}
            onChange={(event) => setMinutes(event.target.valueAsNumber)}
          />
        </label>
        <button className="button button--ghost" disabled={pending} type="submit">
          {pending ? 'Guardando…' : 'Guardar progreso'}
        </button>
      </form>
    </details>
  )
}
