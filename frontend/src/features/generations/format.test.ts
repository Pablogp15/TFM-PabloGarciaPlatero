import { describe, expect, it } from 'vitest'

import {
  describeGenerationParams,
  describeGenerationProgress,
  formatDuration,
  generationStageLabel,
  generationStatusLabel,
  isGenerationActive,
} from './format'
import type { Generation } from './types'

function generation(overrides: Partial<Generation> = {}): Generation {
  return {
    id: 'generation-1',
    project_id: 'project-1',
    source_image_id: 'image-1',
    result_image_id: null,
    provider: 'stub',
    model_name: 'Qwen-Image-Edit-2511',
    quality: 'draft',
    prompt: 'Pinta la miniatura',
    negative_prompt: null,
    params: {
      num_inference_steps: 20,
      width: 768,
      height: 768,
      seed: null,
      quality: 'draft',
    },
    status: 'queued',
    progress_stage: 'queued',
    progress_percent: 0,
    job_id: null,
    estimated_seconds: 180,
    model_load_ms: null,
    inference_ms: null,
    vram_peak_mb: null,
    error_code: null,
    error_message: null,
    queued_at: '2026-01-01T10:00:00Z',
    started_at: null,
    finished_at: null,
    created_at: '2026-01-01T10:00:00Z',
    result_url: null,
    ...overrides,
  }
}

describe('isGenerationActive', () => {
  it('considera activas solo las generaciones en cola o en ejecución', () => {
    expect(isGenerationActive('queued')).toBe(true)
    expect(isGenerationActive('running')).toBe(true)
    expect(isGenerationActive('succeeded')).toBe(false)
    expect(isGenerationActive('failed')).toBe(false)
    expect(isGenerationActive('cancelled')).toBe(false)
  })
})

describe('describeGenerationProgress', () => {
  it('describe la cola y el progreso de la inferencia', () => {
    expect(describeGenerationProgress(generation())).toBe('En cola de espera')
    expect(
      describeGenerationProgress(
        generation({ status: 'running', progress_stage: 'inference', progress_percent: 55 }),
      ),
    ).toBe('Inferencia · 55%')
  })

  it('usa la etiqueta del estado cuando la generación termina', () => {
    expect(describeGenerationProgress(generation({ status: 'succeeded' }))).toBe('Completada')
  })
})

describe('etiquetas', () => {
  it('traduce estados y etapas', () => {
    expect(generationStatusLabel('failed')).toBe('Fallida')
    expect(generationStageLabel('loading')).toBe('Cargando modelo')
  })
})

describe('describeGenerationParams', () => {
  it('resume tamaño, pasos y calidad', () => {
    expect(describeGenerationParams(generation())).toBe(
      '768 × 768 px · 20 pasos · Borrador (rápida)',
    )
  })

  it('incluye la semilla cuando está definida', () => {
    const seeded = generation({
      params: {
        num_inference_steps: 30,
        width: 1024,
        height: 1024,
        seed: 42,
        quality: 'final',
      },
    })
    expect(describeGenerationParams(seeded)).toContain('semilla 42')
  })
})

describe('formatDuration', () => {
  it('formatea milisegundos, segundos y minutos', () => {
    expect(formatDuration(null)).toBe('—')
    expect(formatDuration(800)).toBe('800 ms')
    expect(formatDuration(12_300)).toBe('12.3 s')
    expect(formatDuration(125_000)).toBe('2 min 5 s')
  })
})
