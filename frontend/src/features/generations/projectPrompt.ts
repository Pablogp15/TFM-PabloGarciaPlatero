import { SCHEME_ROLE_LABELS, type Project, type SchemeColor } from '../projects/types'

export const PROJECT_PROMPT_LIMIT = 2000

/** Compone una propuesta local y editable, sin ejecutar otra inferencia. */
export function buildProjectPrompt(project: Project, colors: SchemeColor[]) {
  let shortened = false
  function compact(value: string | null, max: number) {
    const text = (value ?? '').replace(/\s+/g, ' ').trim()
    if (text.length > max) shortened = true
    if (max <= 1) return ''
    return text.length > max ? `${text.slice(0, max - 1)}…` : text
  }
  const details = [
    'Pinta la miniatura de la imagen conservando su forma, pose, detalles y encuadre.',
    `Proyecto: ${compact(project.name, 80)}.`,
    project.subject ? `Miniatura o tema: ${compact(project.subject, 120)}.` : '',
    project.scale_mm ? `Escala declarada de la miniatura: ${project.scale_mm} mm.` : '',
    project.description ? `Aspecto deseado: ${compact(project.description, 400)}.` : '',
  ]
    .filter(Boolean)
    .join('\n')
  const finish =
    '\nRepresenta un acabado de miniatura pintada. Los códigos de color son referencias visuales aproximadas. No añadas texto, etiquetas ni marcas de agua.'
  const palette = colors.map(
    (color) => `${SCHEME_ROLE_LABELS[color.role]} ${color.effective_hex.toUpperCase()}`,
  )
  const prefix = colors.length ? '\nEsquema de color (usa cada color según su rol):\n' : ''
  const available =
    PROJECT_PROMPT_LIMIT -
    details.length -
    finish.length -
    prefix.length -
    palette.join('; ').length
  const noteBudget = colors.length ? Math.max(0, Math.floor(available / colors.length) - 3) : 0
  const entries = colors.map((color, index) => {
    const note = compact(color.notes, Math.min(60, noteBudget))
    return palette[index] + (note && noteBudget > 1 ? ` (${note})` : '')
  })
  return { prompt: details + prefix + entries.join('; ') + finish, shortened }
}
