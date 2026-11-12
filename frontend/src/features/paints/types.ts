export const PAINT_TYPES = [
  'base',
  'layer',
  'wash',
  'contrast',
  'metallic',
  'technical',
  'ink',
  'pigment',
] as const

export type PaintType = (typeof PAINT_TYPES)[number]

export const PAINT_TYPE_LABELS: Record<PaintType, string> = {
  base: 'Base',
  layer: 'Capa',
  wash: 'Lavado',
  contrast: 'Contraste',
  metallic: 'Metálico',
  technical: 'Técnica',
  ink: 'Tinta',
  pigment: 'Pigmento',
}

export const FINISH_TYPES = ['matte', 'satin', 'gloss'] as const

export type FinishType = (typeof FINISH_TYPES)[number]

export const FINISH_LABELS: Record<FinishType, string> = {
  matte: 'Mate',
  satin: 'Satén',
  gloss: 'Brillo',
}

export interface Paint {
  id: string
  brand: string
  range_name: string
  name: string
  code: string | null
  hex: string
  paint_type: PaintType
  finish: FinishType
  is_active: boolean
}

export interface PaintFilters {
  q?: string
  brand?: string
  range_name?: string
  paint_type?: PaintType
  finish?: FinishType
  limit?: number
  offset?: number
}

export interface PaintColorFilters {
  hex_color: string
  q?: string
  brand?: string
  range_name?: string
  paint_type?: PaintType
  finish?: FinishType
  limit?: number
  offset?: number
}

export interface PaintList {
  items: Paint[]
  total: number
  limit: number
  offset: number
}

export interface PaintRangeFacet {
  brand: string
  range_name: string
}

export interface PaintFacets {
  brands: string[]
  ranges: PaintRangeFacet[]
  paint_types: PaintType[]
  finishes: FinishType[]
}

export interface SimilarPaint {
  paint: Paint
  distance: number
}

export type PaintColorSearch = Omit<PaintList, 'items'> & {
  items: SimilarPaint[]
}
