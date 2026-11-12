import { useState, type FormEvent } from 'react'

import { describeError } from '../../lib/http'
import { formatDate } from '../projects/format'
import { useProjectImages } from '../projects/useProjects'
import type { Project } from '../projects/types'
import { ProjectPromptButton } from './ProjectPromptButton'
import { PROJECT_PROMPT_LIMIT as PROMPT_MAX } from './projectPrompt'
import {
  describeGenerationParams,
  describeGenerationProgress,
  formatDuration,
  generationStatusLabel,
  isGenerationActive,
  qualityModeLabel,
} from './format'
import { QUALITY_MODES, type Generation, type GenerationCreate, type QualityMode } from './types'
import {
  useCancelGeneration,
  useCreateGeneration,
  useGenerationCompletion,
  useGenerations,
} from './useGenerations'

interface GenerationPanelProps {
  projectId: string
  project?: Project
}

const NEGATIVE_PROMPT_MAX = 1000

export function GenerationPanel({ projectId, project }: GenerationPanelProps) {
  const generations = useGenerations(projectId)
  const images = useProjectImages(projectId)
  const create = useCreateGeneration(projectId)
  const cancel = useCancelGeneration(projectId)

  const [sourceId, setSourceId] = useState('')
  const [prompt, setPrompt] = useState('')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [quality, setQuality] = useState<QualityMode>('draft')
  const [seed, setSeed] = useState('')
  const [clientError, setClientError] = useState<string | null>(null)

  const items = generations.data?.items ?? []
  const active = items.find((generation) => isGenerationActive(generation.status))
  const sourceImages = (images.data?.items ?? []).filter((image) => image.kind === 'source')
  const selectedSourceId = sourceId || sourceImages[0]?.id || ''

  useGenerationCompletion(projectId, Boolean(active))

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedPrompt = prompt.trim()
    if (!trimmedPrompt) {
      setClientError('Describe cómo quieres pintar la miniatura')
      return
    }
    if (!selectedSourceId) {
      setClientError('Sube primero una imagen de origen del proyecto')
      return
    }

    const payload: GenerationCreate = {
      source_image_id: selectedSourceId,
      prompt: trimmedPrompt,
      quality,
    }

    const trimmedNegative = negativePrompt.trim()
    if (trimmedNegative) {
      payload.negative_prompt = trimmedNegative
    }

    const trimmedSeed = seed.trim()
    if (trimmedSeed) {
      const parsed = Number(trimmedSeed)
      if (!Number.isInteger(parsed) || parsed < 0 || parsed > 2_147_483_647) {
        setClientError('La semilla debe ser un entero entre 0 y 2147483647')
        return
      }
      payload.seed = parsed
    }

    setClientError(null)
    try {
      await create.mutateAsync(payload)
      setPrompt('')
      setNegativePrompt('')
      setSeed('')
    } catch {
      // El error se muestra a partir del estado de la mutación.
    }
  }

  const displayedError =
    clientError ??
    (create.error ? describeError(create.error) : null) ??
    (cancel.error ? describeError(cancel.error) : null) ??
    (images.error ? describeError(images.error) : null)

  const formDisabled = Boolean(active) || sourceImages.length === 0

  return (
    <div className="generation-panel">
      <form className="generation-form" onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="field">
            <label htmlFor="generation-source">Imagen de origen</label>
            <select
              id="generation-source"
              value={selectedSourceId}
              onChange={(event) => setSourceId(event.target.value)}
              disabled={sourceImages.length === 0}
            >
              {sourceImages.length === 0 ? (
                <option value="">Sube primero una imagen de origen</option>
              ) : (
                sourceImages.map((image) => (
                  <option key={image.id} value={image.id}>
                    {image.width} × {image.height} px · {formatDate(image.created_at)}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="field">
            <label htmlFor="generation-quality">Calidad</label>
            <select
              id="generation-quality"
              value={quality}
              onChange={(event) => setQuality(event.target.value as QualityMode)}
            >
              {QUALITY_MODES.map((value) => (
                <option key={value} value={value}>
                  {qualityModeLabel(value)}
                </option>
              ))}
            </select>
          </div>

          <div className="field field--short">
            <label htmlFor="generation-seed">Semilla</label>
            <input
              id="generation-seed"
              type="number"
              min={0}
              max={2_147_483_647}
              step={1}
              value={seed}
              onChange={(event) => setSeed(event.target.value)}
              placeholder="Aleatoria"
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="generation-prompt">Prompt</label>
          {project && (
            <ProjectPromptButton
              project={project}
              hasPrompt={Boolean(prompt.trim())}
              disabled={Boolean(active) || create.isPending}
              onApply={(value) => {
                setPrompt(value)
                setClientError(null)
              }}
            />
          )}
          <textarea
            id="generation-prompt"
            rows={3}
            maxLength={PROMPT_MAX}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Describe el acabado, los colores y los detalles que quieres para la miniatura"
          />
          <p className="field-hint">
            {prompt.length}/{PROMPT_MAX} caracteres
          </p>
        </div>

        <div className="field">
          <label htmlFor="generation-negative">Prompt negativo (opcional)</label>
          <input
            id="generation-negative"
            type="text"
            maxLength={NEGATIVE_PROMPT_MAX}
            value={negativePrompt}
            onChange={(event) => setNegativePrompt(event.target.value)}
            placeholder="Elementos que quieres evitar"
          />
        </div>

        {displayedError && (
          <p className="form-error" role="alert">
            {displayedError}
          </p>
        )}

        {create.isSuccess && !create.error && (
          <p className="form-success" role="status">
            Generación enviada a la cola.
          </p>
        )}

        <div className="form-actions">
          <button className="button" type="submit" disabled={formDisabled || create.isPending}>
            {create.isPending ? 'Enviando…' : 'Generar imagen'}
          </button>
        </div>

        {sourceImages.length === 0 && (
          <p className="field-hint">
            Necesitas subir una imagen de origen en la sección «Imágenes» antes de generar.
          </p>
        )}
        {active && (
          <p className="field-hint">
            Ya hay una generación en curso. Espera a que termine o cancélala para enviar otra.
          </p>
        )}
      </form>

      {generations.isPending ? (
        <p className="muted">Cargando generaciones…</p>
      ) : generations.error ? (
        <p className="form-error" role="alert">
          {describeError(generations.error)}
        </p>
      ) : (
        <>
          {active && (
            <section className="generation-active" aria-live="polite">
              <div className="generation-active__header">
                <h3>Generación en curso</h3>
                <span className="badge">{generationStatusLabel(active.status)}</span>
              </div>
              <progress
                className="generation-progress"
                value={active.progress_percent}
                max={100}
                aria-label="Progreso de la generación"
              />
              <p className="muted generation-active__status">
                {describeGenerationProgress(active)}
              </p>
              <p className="generation-active__prompt">{active.prompt}</p>
              <button
                className="button button--ghost"
                type="button"
                onClick={() => cancel.mutate(active.id)}
                disabled={cancel.isPending}
              >
                {cancel.isPending ? 'Cancelando…' : 'Cancelar generación'}
              </button>
            </section>
          )}

          {items.length === 0 ? (
            <p className="empty-inline">
              Todavía no has generado ninguna imagen para este proyecto.
            </p>
          ) : (
            <ul className="generation-list">
              {items.map((generation) => (
                <GenerationItem key={generation.id} generation={generation} />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}

function GenerationItem({ generation }: { generation: Generation }) {
  return (
    <li className="generation-item">
      <div className="generation-item__header">
        <span className={`badge badge--generation-${generation.status}`}>
          {generationStatusLabel(generation.status)}
        </span>
        <span className="muted generation-item__meta">{formatDate(generation.created_at)}</span>
      </div>

      <p className="generation-item__prompt">{generation.prompt}</p>
      <p className="muted generation-item__meta">{describeGenerationParams(generation)}</p>

      {generation.status === 'succeeded' && generation.result_url && (
        <a
          className="generation-item__result"
          href={generation.result_url}
          target="_blank"
          rel="noreferrer"
        >
          <img
            src={generation.result_url}
            alt="Resultado de la generación"
            loading="lazy"
            width={generation.params.width}
            height={generation.params.height}
          />
        </a>
      )}

      {generation.status === 'failed' && (
        <p className="form-error" role="alert">
          {generation.error_message ?? 'La generación no se pudo completar'}
        </p>
      )}

      <p className="muted generation-item__meta">
        Inferencia: {formatDuration(generation.inference_ms)}
      </p>
    </li>
  )
}
