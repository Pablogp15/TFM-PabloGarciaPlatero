import { describe, expect, it } from 'vitest'

import { formatBytes, formatScale } from './format'

describe('formatScale', () => {
  it('indica la escala en milímetros', () => {
    expect(formatScale(32)).toBe('Escala 32 mm')
  })

  it('indica cuando no hay escala', () => {
    expect(formatScale(null)).toBe('Sin escala')
  })
})

describe('formatBytes', () => {
  it('usa bytes para tamaños pequeños', () => {
    expect(formatBytes(900)).toBe('900 B')
  })

  it('usa kilobytes y megabytes con un decimal', () => {
    expect(formatBytes(2048)).toBe('2.0 KB')
    expect(formatBytes(3 * 1024 * 1024)).toBe('3.0 MB')
  })
})
