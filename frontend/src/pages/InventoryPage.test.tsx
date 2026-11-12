import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { InventoryPage } from './InventoryPage'

const state = vi.hoisted(() => ({
  low: false,
  mutate: vi.fn(),
  filters: vi.fn(),
}))
vi.mock('../features/inventory/useInventory', () => ({
  useInventory: (filters: unknown) => {
    state.filters(filters)
    return {
      data: {
        total: 1,
        items: [
          {
            id: 'owned-1',
            quantity: 2,
            running_low: state.low,
            notes: null,
            paint: {
              id: 'paint-1',
              name: 'Rojo',
              hex: '#ff0000',
              brand: 'Vallejo',
              range_name: 'Model',
            },
          },
        ],
      },
    }
  },
  useInventoryStats: () => ({
    data: { total_items: 1, total_quantity: 2, owned: 1, running_low: 0, brands: 1 },
  }),
  useUpdateInventoryItem: () => ({ mutate: state.mutate, isPending: false }),
  useDeleteInventoryItem: () => ({ isPending: false }),
}))
let container: HTMLDivElement
let root: Root
beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  state.low = false
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
  act(() =>
    root.render(
      <MemoryRouter>
        <InventoryPage />
      </MemoryRouter>,
    ),
  )
}
it('toggles low stock independently of quantity and has no wishlist status', () => {
  render()
  const button = container.querySelector<HTMLButtonElement>('[aria-pressed]')!
  act(() => button.click())
  expect(state.mutate).toHaveBeenLastCalledWith({ id: 'owned-1', payload: { running_low: true } })
  state.low = true
  render()
  act(() => button.click())
  expect(state.mutate).toHaveBeenLastCalledWith({ id: 'owned-1', payload: { running_low: false } })
  expect(container.textContent).not.toContain('Lista de deseos')
  expect(container.querySelectorAll('select')).toHaveLength(1)
})
it('filters only low-stock paints and clears that filter', () => {
  render()
  const select = container.querySelector('select')!
  act(() => {
    select.value = 'low'
    select.dispatchEvent(new Event('change', { bubbles: true }))
  })
  expect(state.filters).toHaveBeenLastCalledWith(
    expect.objectContaining({ running_low: true, offset: 0 }),
  )
  const clear = [...container.querySelectorAll('button')].find(
    (button) => button.textContent === 'Limpiar filtros',
  )!
  act(() => clear.click())
  expect(state.filters).toHaveBeenLastCalledWith(
    expect.objectContaining({ running_low: undefined }),
  )
})
