import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { techniques } from '../features/techniques/catalog'
import { GuidesPage } from './GuidesPage'

let container: HTMLDivElement
let root: Root
const originalShowModal = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const originalClose = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: vi.fn(function (this: HTMLDialogElement) {
      this.open = true
    }),
  })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value: vi.fn(function (this: HTMLDialogElement) {
      this.open = false
    }),
  })
  container = document.createElement('div')
  document.body.append(container)
  root = createRoot(container)
  act(() => root.render(<GuidesPage />))
})

afterEach(() => {
  act(() => root.unmount())
  container.remove()
  vi.restoreAllMocks()
  for (const [name, descriptor] of [
    ['showModal', originalShowModal],
    ['close', originalClose],
  ] as const) {
    if (descriptor) Object.defineProperty(HTMLDialogElement.prototype, name, descriptor)
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name)
  }
})

it('shows the whole manual in difficulty order and places glazing in advanced', () => {
  const sections = container.querySelectorAll('.technique-section')
  expect([...sections].map((section) => section.querySelector('h2')?.textContent)).toEqual([
    'Inicial',
    'Intermedio',
    'Avanzado',
  ])
  expect(container.querySelectorAll('.technique-card')).toHaveLength(22)
  expect(sections[2].textContent).toContain('Veladuras o glazing')
  expect(sections[0].textContent).not.toContain('Veladuras')
  expect(sections[1].textContent).not.toContain('Veladuras')
  expect(techniques.find((technique) => technique.id === '15')?.difficulty).toBe('advanced')
  expect(container.querySelectorAll('.technique-card svg[aria-label]')).toHaveLength(22)
})

it('opens readable content and restores focus and scrolling when closed', () => {
  const trigger = [...container.querySelectorAll<HTMLButtonElement>('.technique-card')].find(
    (button) => button.textContent?.includes('Veladuras'),
  )!
  trigger.focus()
  act(() => trigger.click())
  const dialog = container.querySelector('dialog')!
  expect(dialog.open).toBe(true)
  expect(dialog.querySelector('h2')?.textContent).toBe('Veladuras o glazing')
  expect(dialog.textContent).toContain('Dejar secar antes de valorar y repetir')
  expect(dialog.textContent).not.toContain('**Objetivo:**')
  expect(dialog.querySelectorAll('ol li')).toHaveLength(4)
  expect(dialog.querySelector('a')?.href).toMatch(/^https:\/\//)
  expect(document.body.style.overflow).toBe('hidden')
  act(() => dialog.querySelector<HTMLButtonElement>('button')!.click())
  expect(container.querySelector('dialog')).toBeNull()
  expect(document.activeElement).toBe(trigger)
  expect(document.body.style.overflow).toBe('')
})

it('dismisses on the native Escape cancel event and backdrop click', () => {
  const trigger = container.querySelector<HTMLButtonElement>('.technique-card')!
  act(() => trigger.click())
  act(() =>
    container
      .querySelector('dialog')!
      .dispatchEvent(new Event('cancel', { bubbles: false, cancelable: true })),
  )
  expect(container.querySelector('dialog')).toBeNull()
  act(() => trigger.click())
  act(() => container.querySelector('dialog')!.click())
  expect(container.querySelector('dialog')).toBeNull()
})
