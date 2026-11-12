import {
  GENERATION_STAGE_LABELS,
  GENERATION_STATUS_LABELS,
  type Generation,
  type GenerationStage,
  type GenerationStatus,
  type QualityMode,
  QUALITY_MODE_LABELS,
} from './types'

/** Una generación está activa mientras la cola o el trabajador la atienden. */
export function isGenerationActive(status: GenerationStatus): boolean {
  return status === 'queued' || status === 'running'
}

export function generationStatusLabel(status: GenerationStatus): string {
  return GENERATION_STATUS_LABELS[status]
}

export function generationStageLabel(stage: GenerationStage): string {
  return GENERATION_STAGE_LABELS[stage]
}

export function qualityModeLabel(quality: QualityMode): string {
  return QUALITY_MODE_LABELS[quality]
}

/** Texto corto que resume el estado y el progreso de una generación. */
export function describeGenerationProgress(generation: Generation): string {
  if (generation.status === 'queued') {
    return 'En cola de espera'
  }
  if (generation.status === 'running') {
    return `${generationStageLabel(generation.progress_stage)} · ${generation.progress_percent}%`
  }
  return generationStatusLabel(generation.status)
}

/** Duración legible de la inferencia, o un guion si todavía no se conoce. */
export function formatDuration(milliseconds: number | null): string {
  if (milliseconds === null || milliseconds < 0) {
    return '—'
  }
  if (milliseconds < 1000) {
    return `${milliseconds} ms`
  }

  const seconds = milliseconds / 1000
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`
  }

  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes} min ${rest} s`
}

/** Resumen de los parámetros efectivos que aplicó el backend. */
export function describeGenerationParams(generation: Generation): string {
  const { width, height, num_inference_steps: steps, seed } = generation.params
  const parts = [`${width} × ${height} px`, `${steps} pasos`, qualityModeLabel(generation.quality)]
  if (seed !== null) {
    parts.push(`semilla ${seed}`)
  }
  return parts.join(' · ')
}
