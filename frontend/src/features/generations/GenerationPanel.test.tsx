import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { GenerationPanel } from './GenerationPanel'
import type { Generation } from './types'

const state = vi.hoisted(() => ({
  hasSource: true,
  items: [] as Generation[],
  submit: vi.fn().mockResolvedValue({}),
  error: null as Error | null,
}))

vi.mock('../projects/useProjects', () => ({
  useProjectImages: () => ({
    data: {
      items: state.hasSource
        ? [{ id: 'source-1', kind: 'source', width: 768, height: 768, created_at: '2026-11-08' }]
        : [],
    },
  }),
}))

vi.mock('./useGenerations', () => ({
  useGenerations: () => ({ data: { items: state.items }, isPending: false }),
  useCreateGeneration: () => ({ mutateAsync: state.submit, error: state.error }),
  useCancelGeneration: () => ({}),
  useGenerationCompletion: () => undefined,
}))

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  state.hasSource = true
  state.items = []
  state.error = null
  state.submit.mockClear()
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
})

function render() {
  act(() => root.render(<GenerationPanel projectId="project-1" />))
}

function change(selector: string, value: string) {
  const element = container.querySelector(selector)
  if (!(element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement)) {
    throw new Error(`Missing input ${selector}`)
  }
  const prototype =
    element instanceof HTMLInputElement ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype
  Object.getOwnPropertyDescriptor(prototype, 'value')?.set?.call(element, value)
  element.dispatchEvent(new Event('input', { bubbles: true }))
}

function generation(status: Generation['status']): Generation {
  return {
    id: 'generation-1',
    project_id: 'project-1',
    source_image_id: 'source-1',
    result_image_id: 'result-1',
    provider: 'qwen-local',
    model_name: 'Qwen-Image-Edit-2511',
    quality: 'draft',
    prompt: 'paint red',
    negative_prompt: null,
    params: { width: 768, height: 768, num_inference_steps: 20, seed: 42, quality: 'draft' },
    status,
    progress_stage: 'inference',
    progress_percent: 50,
    job_id: 'job-1',
    estimated_seconds: null,
    model_load_ms: 0,
    inference_ms: 1000,
    vram_peak_mb: 1024,
    error_code: null,
    error_message: null,
    queued_at: '2026-11-08',
    started_at: null,
    finished_at: null,
    created_at: '2026-11-08',
    result_url: '/api/v1/projects/project-1/images/result-1',
  }
}

it('requires a source image and prevents submission while a job is active', () => {
  state.hasSource = false
  render()
  expect(container.querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBe(true)
  state.hasSource = true
  state.items = [generation('running')]
  render()
  expect(container.querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBe(true)
  expect(container.querySelector('progress')?.value).toBe(50)
})

it('sends the selected source, trimmed prompt and seed to the backend', async () => {
  render()
  act(() => {
    change('#generation-prompt', '  paint red  ')
    change('#generation-seed', '42')
  })
  await act(async () =>
    container.querySelector<HTMLButtonElement>('button[type="submit"]')?.click(),
  )
  expect(state.submit).toHaveBeenCalledExactlyOnceWith({
    source_image_id: 'source-1',
    prompt: 'paint red',
    seed: 42,
    quality: 'draft',
  })
})

it('rejects an empty prompt and displays the generated result', async () => {
  render()
  await act(async () =>
    container.querySelector<HTMLButtonElement>('button[type="submit"]')?.click(),
  )
  expect(state.submit).not.toHaveBeenCalled()
  expect(container.querySelector('[role="alert"]')?.textContent).toContain('Describe')
  state.items = [generation('succeeded')]
  render()
  expect(container.querySelector('img')?.getAttribute('src')).toBe(state.items[0].result_url)
})

it('displays a controlled inference error', () => {
  state.items = [{ ...generation('failed'), error_message: 'La inferencia falló' }]
  render()
  expect(container.querySelector('[role="alert"]')?.textContent).toBe('La inferencia falló')
})
