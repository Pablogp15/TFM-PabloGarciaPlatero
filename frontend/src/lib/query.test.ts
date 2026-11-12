import { describe, expect, it } from 'vitest'

import { buildQuery } from './query'

describe('buildQuery', () => {
  it('omite valores indefinidos, nulos y cadenas vacías', () => {
    expect(buildQuery({ q: '', brand: undefined, finish: null, limit: 24 })).toBe('?limit=24')
  })

  it('codifica los valores y conserva cero y false', () => {
    expect(buildQuery({ q: 'rojo oscuro', offset: 0, activo: false })).toBe(
      '?q=rojo+oscuro&offset=0&activo=false',
    )
  })

  it('devuelve una cadena vacía cuando no hay parámetros', () => {
    expect(buildQuery({})).toBe('')
  })
})
