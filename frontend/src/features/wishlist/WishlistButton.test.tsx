import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { WishlistButton } from './WishlistButton'

const state = vi.hoisted(() => ({
  ids: [] as string[] | undefined,
  pending: false,
  error: null as Error | null,
  mutate: vi.fn(),
}))

vi.mock('./useWishlist', () => ({
  useWishlistIds: () => ({ data: state.ids, error: null, isFetching: false }),
  useToggleWishlist: () => ({ mutate: state.mutate, isPending: state.pending, error: state.error }),
}))

let container: HTMLDivElement
let root: Root
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  state.ids = []
  state.pending = false
  state.error = null
  state.mutate.mockClear()
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
})
afterEach(() => {
  act(() => root.unmount())
  container.remove()
})
function render() {
  act(() => root.render(<WishlistButton paintId="paint-1" name="Rojo" />))
  return container.querySelector('button')!
}

it('adds a wish with the heart and removes it when already selected', () => {
  const button = render()
  expect(button.getAttribute('aria-pressed')).toBe('false')
  act(() => button.click())
  expect(state.mutate).toHaveBeenLastCalledWith({ paintId: 'paint-1', wished: false })
  state.ids = ['paint-1']
  render()
  expect(button.getAttribute('aria-pressed')).toBe('true')
  expect(button.getAttribute('aria-label')).toContain('Quitar Rojo de deseados')
  act(() => button.click())
  expect(state.mutate).toHaveBeenLastCalledWith({ paintId: 'paint-1', wished: true })
})

it('blocks clicks during loading and mutation and shows errors', () => {
  state.ids = undefined
  expect(render().disabled).toBe(true)
  state.ids = []
  state.pending = true
  expect(render().disabled).toBe(true)
  state.pending = false
  state.error = new Error('No se pudo guardar')
  render()
  expect(container.querySelector('[role="alert"]')).not.toBeNull()
})
