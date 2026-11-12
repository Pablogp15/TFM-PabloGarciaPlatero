import { expect, it } from 'vitest'

import type { Project, SchemeColor } from '../projects/types'
import { buildProjectPrompt } from './projectPrompt'

const project: Project = {
  id: 'p1',
  name: 'Orco',
  subject: 'guerrero orco',
  description: 'Armadura roja y piel verde',
  scale_mm: 32,
  status: 'draft',
  created_at: '',
  updated_at: '',
  completed_at: null,
}
function color(notes: string | null = 'Armadura'): SchemeColor {
  return {
    id: 'c1',
    position: 0,
    role: 'primary',
    paint: null,
    hex_override: '#9c1c1c',
    effective_hex: '#9c1c1c',
    notes,
  }
}
it('uses the saved subject, description, scale, palette role and note', () => {
  const result = buildProjectPrompt(project, [color()])
  expect(result.prompt).toContain('guerrero orco')
  expect(result.prompt).toContain('Armadura roja y piel verde')
  expect(result.prompt).toContain('32 mm')
  expect(result.prompt).toContain('Principal #9C1C1C (Armadura)')
  expect(result.shortened).toBe(false)
})
it('keeps all 32 palette colors and the complete closing instructions within 2000 characters', () => {
  const colors = Array.from({ length: 32 }, (_, i) => ({
    ...color('Nota muy larga '.repeat(20)),
    role: 'base_rim' as const,
    effective_hex: `#${i.toString(16).padStart(6, '0')}`,
  }))
  const result = buildProjectPrompt(
    {
      ...project,
      name: 'Nombre '.repeat(30),
      subject: 'Tema '.repeat(100),
      description: 'Descripción '.repeat(500),
    },
    colors,
  )
  expect(result.prompt.length).toBeLessThanOrEqual(2000)
  for (const item of colors) expect(result.prompt).toContain(item.effective_hex.toUpperCase())
  expect(result.prompt.endsWith('No añadas texto, etiquetas ni marcas de agua.')).toBe(true)
  expect(result.shortened).toBe(true)
})
it('handles an empty palette and missing optional project fields', () => {
  const result = buildProjectPrompt(
    { ...project, description: null, subject: null, scale_mm: null },
    [],
  )
  expect(result.prompt).not.toContain('null')
  expect(result.prompt).not.toContain('Esquema de color')
  expect(result.prompt).not.toContain('Escala declarada')
})
