import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { PaintColorSearch } from './PaintColorSearch'

function changeInput(input: HTMLInputElement, value: string) {
  const setValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
  setValue?.call(input, value)
  input.dispatchEvent(new Event('input', { bubbles: true }))
  input.dispatchEvent(new Event('change', { bubbles: true }))
}

describe('PaintColorSearch', () => {
  let container: HTMLDivElement
  let root: Root
  let searchCalls: (string | undefined)[]
  let onSearch: (hex: string | undefined) => void

  beforeEach(() => {
    Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
    container = document.createElement('div')
    document.body.append(container)
    root = createRoot(container)
    searchCalls = []
    onSearch = (hex) => searchCalls.push(hex)
  })

  afterEach(() => {
    act(() => root.unmount())
    container.remove()
  })

  it('normalizes and submits a hexadecimal color', () => {
    act(() => root.render(<PaintColorSearch value="" onSearch={onSearch} />))
    const input = container.querySelector<HTMLInputElement>('#paint-color-hex')
    expect(input).not.toBeNull()
    if (!input) return

    act(() => {
      changeInput(input, 'a34f28')
    })
    act(() => {
      container.querySelector<HTMLButtonElement>('.button')?.click()
    })

    expect(searchCalls).toEqual(['#A34F28'])
  })

  it('requires a valid hexadecimal color before searching', () => {
    act(() => root.render(<PaintColorSearch value="" onSearch={onSearch} />))
    const input = container.querySelector<HTMLInputElement>('#paint-color-hex')
    expect(input).not.toBeNull()
    if (!input) return

    act(() => {
      changeInput(input, '#12GG00')
    })
    act(() => {
      container.querySelector<HTMLButtonElement>('.button')?.click()
    })

    expect(searchCalls).toEqual([])
    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      'color hexadecimal válido',
    )
  })

  it('keeps HEX synchronized when adjusting the shade', () => {
    act(() => root.render(<PaintColorSearch value="#FF0000" onSearch={onSearch} />))
    const lightness = container.querySelector<HTMLInputElement>('#paint-color-lightness')
    expect(lightness).not.toBeNull()
    if (!lightness) return

    act(() => {
      changeInput(lightness, '25')
    })
    act(() => {
      container.querySelector<HTMLButtonElement>('.button')?.click()
    })

    expect(searchCalls).toEqual(['#800000'])
  })
})
