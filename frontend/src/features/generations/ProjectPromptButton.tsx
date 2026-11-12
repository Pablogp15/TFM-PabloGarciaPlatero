import { useState } from 'react'

import type { Project } from '../projects/types'
import { useSchemeColors } from '../projects/useProjects'
import { buildProjectPrompt } from './projectPrompt'

export function ProjectPromptButton({
  project,
  hasPrompt,
  disabled,
  onApply,
}: {
  project: Project
  hasPrompt: boolean
  disabled: boolean
  onApply: (prompt: string) => void
}) {
  const scheme = useSchemeColors(project.id)
  const [confirm, setConfirm] = useState(false)
  const [shortened, setShortened] = useState(false)
  function apply() {
    const result = buildProjectPrompt(project, scheme.data ?? [])
    onApply(result.prompt)
    setShortened(result.shortened)
    setConfirm(false)
  }
  return (
    <div>
      <button
        type="button"
        className="button button--ghost"
        disabled={disabled || scheme.isPending || Boolean(scheme.error)}
        onClick={() => (hasPrompt ? setConfirm(true) : apply())}
      >
        Crear prompt con el proyecto
      </button>
      {confirm && (
        <div className="form-actions">
          <p>El prompt ya tiene texto. ¿Quieres sustituirlo por la propuesta del proyecto?</p>
          <button
            type="button"
            className="button button--ghost"
            disabled={disabled}
            onClick={apply}
          >
            Sustituir prompt
          </button>
          <button type="button" className="button button--ghost" onClick={() => setConfirm(false)}>
            Conservar mi texto
          </button>
        </div>
      )}
      <p className="field-hint">
        Usa los datos y el esquema de color guardados. Revisa el prompt antes de generar; los
        cambios posteriores del proyecto no lo reescriben.
      </p>
      {scheme.error && (
        <p className="form-error" role="alert">
          No se pudo cargar el esquema. Intenta recargar la página antes de crear el prompt.
        </p>
      )}
      {shortened && (
        <p className="field-hint" role="status">
          Se han resumido los textos largos para respetar el límite de 2000 caracteres. Revisa la
          propuesta.
        </p>
      )}
    </div>
  )
}
