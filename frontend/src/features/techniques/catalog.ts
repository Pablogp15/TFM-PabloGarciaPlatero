import data from './catalog.json'

export type Difficulty = 'beginner' | 'intermediate' | 'advanced'
export type ContentBlock =
  { type: 'paragraph'; text: string } | { type: 'ordered' | 'unordered'; items: string[] }
export interface Technique {
  id: string
  title: string
  summary: string
  difficulty: Difficulty
  blocks: ContentBlock[]
}

export const levels: { id: Difficulty; label: string; description: string }[] = [
  {
    id: 'beginner',
    label: 'Inicial',
    description: 'Prepara la miniatura y gana control con el pincel.',
  },
  {
    id: 'intermediate',
    label: 'Intermedio',
    description: 'Da volumen, textura y carácter a cada material.',
  },
  {
    id: 'advanced',
    label: 'Avanzado',
    description: 'Afina las transiciones y diseña reflejos con precisión.',
  },
]

// El exportador valida estructura y número de entradas a partir del manual.
export const techniques = data.techniques as Technique[]
export const manualVersion = data.version
