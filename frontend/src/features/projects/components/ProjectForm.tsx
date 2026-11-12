import { useState, type FormEvent } from 'react'

import { describeError } from '../../../lib/http'
import {
  PROJECT_STATUS_LABELS,
  SELECTABLE_PROJECT_STATUSES,
  type Project,
  type ProjectStatus,
} from '../types'

export interface ProjectFormValues {
  name: string
  description: string | null
  subject: string | null
  scale_mm: number | null
  status: ProjectStatus
}

interface ProjectFormProps {
  initial?: Project
  submitLabel: string
  isSubmitting: boolean
  error?: unknown
  showStatus?: boolean
  onSubmit: (values: ProjectFormValues) => void
  onCancel?: () => void
}

const NAME_MAX = 120
const SUBJECT_MAX = 120
const DESCRIPTION_MAX = 4000
const SCALE_MIN = 1
const SCALE_MAX = 2000

export function ProjectForm({
  initial,
  submitLabel,
  isSubmitting,
  error,
  showStatus = false,
  onSubmit,
  onCancel,
}: ProjectFormProps) {
  const [name, setName] = useState(initial?.name ?? '')
  const [subject, setSubject] = useState(initial?.subject ?? '')
  const [scale, setScale] = useState(initial?.scale_mm ? String(initial.scale_mm) : '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [status, setStatus] = useState<ProjectStatus>(initial?.status ?? 'draft')
  const [validationError, setValidationError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedName = name.trim()
    if (!trimmedName) {
      setValidationError('El nombre del proyecto es obligatorio')
      return
    }

    const trimmedSubject = subject.trim()
    const trimmedDescription = description.trim()

    let scaleValue: number | null = null
    if (scale.trim()) {
      const parsed = Number(scale)
      if (!Number.isInteger(parsed) || parsed < SCALE_MIN || parsed > SCALE_MAX) {
        setValidationError(
          `La escala debe ser un número entero entre ${SCALE_MIN} y ${SCALE_MAX} mm`,
        )
        return
      }
      scaleValue = parsed
    }

    setValidationError(null)
    onSubmit({
      name: trimmedName,
      subject: trimmedSubject || null,
      description: trimmedDescription || null,
      scale_mm: scaleValue,
      status,
    })
  }

  const displayedError = validationError ?? (error ? describeError(error) : null)

  return (
    <form className="form" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor="project-name">Nombre</label>
        <input
          id="project-name"
          name="project-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={NAME_MAX}
          required
        />
      </div>

      <div className="form-row">
        <div className="field">
          <label htmlFor="project-subject">Miniatura o tema</label>
          <input
            id="project-subject"
            name="project-subject"
            type="text"
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            maxLength={SUBJECT_MAX}
            placeholder="Orco, caballero, diorama…"
          />
        </div>

        <div className="field field--short">
          <label htmlFor="project-scale">Escala (mm)</label>
          <input
            id="project-scale"
            name="project-scale"
            type="number"
            value={scale}
            onChange={(event) => setScale(event.target.value)}
            min={SCALE_MIN}
            max={SCALE_MAX}
            step={1}
            inputMode="numeric"
            placeholder="32"
          />
        </div>
      </div>

      {showStatus && (
        <div className="field">
          <label htmlFor="project-status">Estado</label>
          <select
            id="project-status"
            name="project-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as ProjectStatus)}
          >
            {SELECTABLE_PROJECT_STATUSES.map((value) => (
              <option key={value} value={value}>
                {PROJECT_STATUS_LABELS[value]}
              </option>
            ))}
            {!SELECTABLE_PROJECT_STATUSES.includes(
              status as (typeof SELECTABLE_PROJECT_STATUSES)[number],
            ) && <option value={status}>{PROJECT_STATUS_LABELS[status]}</option>}
          </select>
        </div>
      )}

      <div className="field">
        <label htmlFor="project-description">Descripción</label>
        <textarea
          id="project-description"
          name="project-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={DESCRIPTION_MAX}
          rows={4}
          placeholder="Idea, referencias o notas del proyecto"
        />
      </div>

      {displayedError && (
        <p className="form-error" role="alert">
          {displayedError}
        </p>
      )}

      <div className="form-actions">
        <button className="button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Guardando…' : submitLabel}
        </button>
        {onCancel && (
          <button
            className="button button--ghost"
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
