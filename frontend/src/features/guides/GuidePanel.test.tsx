import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { GuidePanel } from './GuidePanel'
import type { Guide } from './api'

const state = vi.hoisted(() => ({
  ready: false,
  items: [] as Guide[],
  create: vi.fn(),
  progress: vi.fn(),
}))
vi.mock('../projects/useProjects', () => ({
  useProjectImages: () => ({
    data: { items: [{ id: 'image-1', kind: 'generated', created_at: '2026-11-09' }] },
  }),
}))
vi.mock('./useGuides', () => ({
  useGuides: () => ({ data: { corpus_ready: state.ready, items: state.items } }),
  useGuideActions: () => ({
    create: { mutate: state.create },
    cancel: { mutate: vi.fn() },
    progress: { mutate: state.progress },
  }),
}))
let root: Root
let container: HTMLDivElement
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  state.ready = false
  state.items = []
  state.create.mockClear()
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
})
function render() {
  act(() => root.render(<GuidePanel projectId="project-1" />))
}
it('requires a real corpus and an image before creating a guide', () => {
  render()
  expect(container.textContent).toContain('Importa tus documentos')
  expect(container.querySelector('button')?.disabled).toBe(true)
  state.ready = true
  render()
  expect(container.querySelector('button')?.disabled).toBe(true)
  act(() => {
    const select = container.querySelector('select')!
    select.value = 'image-1'
    select.dispatchEvent(new Event('change', { bubbles: true }))
  })
  act(() => container.querySelector('button')!.click())
  expect(state.create).toHaveBeenCalledWith('image-1')
})
it('shows cancellation and failure without suggesting a complete guide', () => {
  state.items = [
    {
      id: 'guide-1',
      status: 'failed',
      stage: 'cancelled',
      created_at: '2026-11-09',
      error_message: 'Generación cancelada',
      limitations: [],
      unavailable_paint_ids: [],
      steps: [],
    } as unknown as Guide,
  ]
  render()
  expect(container.textContent).toContain('Cancelada')
  expect(container.querySelector('[role="alert"]')?.textContent).toBe('Generación cancelada')
})
