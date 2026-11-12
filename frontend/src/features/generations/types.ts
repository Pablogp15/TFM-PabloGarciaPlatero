export const GENERATION_STATUSES = [
  'queued',
  'running',
  'succeeded',
  'failed',
  'cancelled',
] as const

export type GenerationStatus = (typeof GENERATION_STATUSES)[number]

export const ACTIVE_GENERATION_STATUSES: readonly GenerationStatus[] = ['queued', 'running']

export const GENERATION_STAGES = ['queued', 'loading', 'inference', 'postprocess', 'done'] as const

export type GenerationStage = (typeof GENERATION_STAGES)[number]

export const GENERATION_STATUS_LABELS: Record<GenerationStatus, string> = {
  queued: 'En cola',
  running: 'Generando',
  succeeded: 'Completada',
  failed: 'Fallida',
  cancelled: 'Cancelada',
}

export const GENERATION_STAGE_LABELS: Record<GenerationStage, string> = {
  queued: 'En cola',
  loading: 'Cargando modelo',
  inference: 'Inferencia',
  postprocess: 'Procesando resultado',
  done: 'Terminada',
}

export const QUALITY_MODES = ['draft', 'final'] as const

export type QualityMode = (typeof QUALITY_MODES)[number]

export const QUALITY_MODE_LABELS: Record<QualityMode, string> = {
  draft: 'Borrador (rápida)',
  final: 'Final (mayor calidad)',
}

export interface GenerationParams {
  num_inference_steps: number
  width: number
  height: number
  seed: number | null
  quality: QualityMode
}

export interface Generation {
  id: string
  project_id: string
  source_image_id: string
  result_image_id: string | null
  provider: string
  model_name: string
  quality: QualityMode
  prompt: string
  negative_prompt: string | null
  params: GenerationParams
  status: GenerationStatus
  progress_stage: GenerationStage
  progress_percent: number
  job_id: string | null
  estimated_seconds: number | null
  model_load_ms: number | null
  inference_ms: number | null
  vram_peak_mb: number | null
  error_code: string | null
  error_message: string | null
  queued_at: string
  started_at: string | null
  finished_at: string | null
  created_at: string
  result_url: string | null
}

export interface GenerationList {
  items: Generation[]
  total: number
  limit: number
  offset: number
}

export interface GenerationCreate {
  source_image_id: string
  prompt: string
  negative_prompt?: string | null
  quality?: QualityMode
  num_inference_steps?: number
  width?: number
  height?: number
  seed?: number | null
}
