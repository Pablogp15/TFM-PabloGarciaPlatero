import type { Paint } from '../paints/types'

export const PROJECT_STATUSES = [
  'draft',
  'generating',
  'ready',
  'painting',
  'completed',
  'archived',
] as const

export type ProjectStatus = (typeof PROJECT_STATUSES)[number]

/** Estados que el usuario puede asignar. `generating` es exclusivo del sistema. */
export const SELECTABLE_PROJECT_STATUSES = [
  'draft',
  'ready',
  'painting',
  'completed',
  'archived',
] as const

export type SelectableProjectStatus = (typeof SELECTABLE_PROJECT_STATUSES)[number]

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  draft: 'Borrador',
  generating: 'Generando',
  ready: 'Listo para pintar',
  painting: 'Pintando',
  completed: 'Completado',
  archived: 'Archivado',
}

export interface Project {
  id: string
  name: string
  description: string | null
  subject: string | null
  scale_mm: number | null
  status: ProjectStatus
  created_at: string
  updated_at: string
  completed_at: string | null
}

export interface ProjectList {
  items: Project[]
  total: number
  limit: number
  offset: number
}

export interface ProjectFilters {
  status?: ProjectStatus
  q?: string
  limit?: number
  offset?: number
}

export interface ProjectCreate {
  name: string
  description?: string | null
  subject?: string | null
  scale_mm?: number | null
}

export interface ProjectUpdate {
  name?: string
  description?: string | null
  subject?: string | null
  scale_mm?: number | null
  status?: SelectableProjectStatus
}

export const SCHEME_ROLES = [
  'primary',
  'secondary',
  'accent',
  'skin',
  'metal',
  'wash',
  'highlight',
  'base_rim',
  'other',
] as const

export type SchemeRole = (typeof SCHEME_ROLES)[number]

export const SCHEME_ROLE_LABELS: Record<SchemeRole, string> = {
  primary: 'Principal',
  secondary: 'Secundario',
  accent: 'Acento',
  skin: 'Piel',
  metal: 'Metal',
  wash: 'Lavado',
  highlight: 'Luz',
  base_rim: 'Borde de peana',
  other: 'Otro',
}

export interface SchemeColor {
  id: string
  position: number
  role: SchemeRole
  paint: Paint | null
  hex_override: string | null
  effective_hex: string
  notes: string | null
}

export interface SchemeColorInput {
  role: SchemeRole
  paint_id?: string | null
  hex_override?: string | null
  notes?: string | null
}

export const IMAGE_KINDS = ['source', 'progress', 'generated'] as const

export type ImageKind = (typeof IMAGE_KINDS)[number]

/** Solo estas clases se pueden subir desde la interfaz; `generated` es del sistema. */
export const UPLOAD_IMAGE_KINDS = ['source', 'progress'] as const

export type UploadImageKind = (typeof UPLOAD_IMAGE_KINDS)[number]

export const IMAGE_KIND_LABELS: Record<ImageKind, string> = {
  source: 'Imagen de origen',
  progress: 'Avance',
  generated: 'Generada por IA',
}

export interface ProjectImage {
  id: string
  project_id: string
  kind: ImageKind
  mime_type: string
  width: number
  height: number
  size_bytes: number
  checksum: string
  created_at: string
  url: string
}

export interface ProjectImageList {
  items: ProjectImage[]
  total: number
  limit: number
  offset: number
}
