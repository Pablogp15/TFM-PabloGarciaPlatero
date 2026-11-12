import { useState, type FormEvent } from 'react'

import { describeError } from '../../../lib/http'
import {
  SCHEME_ROLES,
  SCHEME_ROLE_LABELS,
  type SchemeColor,
  type SchemeColorInput,
  type SchemeRole,
} from '../types'
import { useReplaceSchemeColors, useSchemeColors } from '../useProjects'

interface SchemeEditorProps {
  projectId: string
}

interface SchemeRow {
  key: string
  role: SchemeRole
  hex: string
  notes: string
  paintId: string | null
}

const MAX_COLORS = 32
const HEX_PATTERN = /^#[0-9a-fA-F]{6}$/

let rowCounter = 0

function newKey(): string {
  rowCounter += 1
  return `scheme-row-${rowCounter}`
}

function toRow(color: SchemeColor): SchemeRow {
  return {
    key: newKey(),
    role: color.role,
    hex: (color.hex_override ?? color.effective_hex).toUpperCase(),
    notes: color.notes ?? '',
    paintId: color.paint?.id ?? null,
  }
}

function emptyRow(): SchemeRow {
  return {
    key: newKey(),
    role: 'primary',
    hex: '#808080',
    notes: '',
    paintId: null,
  }
}

export function SchemeEditor({ projectId }: SchemeEditorProps) {
  const colors = useSchemeColors(projectId)

  if (colors.isPending) {
    return <p className="muted">Cargando esquema de color…</p>
  }

  if (colors.error) {
    return (
      <p className="form-error" role="alert">
        {describeError(colors.error)}
      </p>
    )
  }

  return <SchemeEditorForm key={projectId} projectId={projectId} initial={colors.data ?? []} />
}

interface SchemeEditorFormProps {
  projectId: string
  initial: SchemeColor[]
}

function SchemeEditorForm({ projectId, initial }: SchemeEditorFormProps) {
  const replace = useReplaceSchemeColors(projectId)
  const [rows, setRows] = useState<SchemeRow[]>(() => initial.map(toRow))
  const [validationError, setValidationError] = useState<string | null>(null)

  function updateRow(key: string, changes: Partial<SchemeRow>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...changes } : row)))
  }

  function handleColorChange(row: SchemeRow, value: string) {
    // Al elegir un color nuevo se desvincula la pintura original del catálogo.
    updateRow(row.key, { hex: value, paintId: null })
  }

  function handleAdd() {
    if (rows.length >= MAX_COLORS) {
      return
    }
    setRows((current) => [
      ...current,
      { ...emptyRow(), role: current.length === 0 ? 'primary' : 'other' },
    ])
  }

  function handleRemove(key: string) {
    setRows((current) => current.filter((row) => row.key !== key))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    for (const row of rows) {
      if (!HEX_PATTERN.test(row.hex)) {
        setValidationError('Cada color debe tener un valor hexadecimal válido')
        return
      }
    }

    setValidationError(null)
    const payload: SchemeColorInput[] = rows.map((row) => ({
      role: row.role,
      hex_override: row.hex.toUpperCase(),
      notes: row.notes.trim() || null,
      ...(row.paintId ? { paint_id: row.paintId } : {}),
    }))
    replace.mutate(payload)
  }

  const displayedError = validationError ?? (replace.error ? describeError(replace.error) : null)

  return (
    <form className="scheme-editor" onSubmit={handleSubmit}>
      <p className="muted">
        Define los colores principales del proyecto. Cada color se guarda con su rol y una nota
        opcional. Guarda el esquema y usa «Crear prompt con el proyecto» en «Generar con IA» para
        incluirlos en la propuesta. Los colores orientan el resultado; no garantizan una
        reproducción exacta de una pintura física.
      </p>

      {rows.length === 0 ? (
        <p className="empty-inline">Todavía no hay colores en el esquema.</p>
      ) : (
        <ul className="scheme-list">
          {rows.map((row, index) => (
            <li className="scheme-row" key={row.key}>
              <div className="field">
                <label htmlFor={`scheme-role-${row.key}`}>Rol</label>
                <select
                  id={`scheme-role-${row.key}`}
                  value={row.role}
                  onChange={(event) =>
                    updateRow(row.key, { role: event.target.value as SchemeRole })
                  }
                >
                  {SCHEME_ROLES.map((value) => (
                    <option key={value} value={value}>
                      {SCHEME_ROLE_LABELS[value]}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field field--color">
                <label htmlFor={`scheme-color-${row.key}`}>Color</label>
                <div className="color-input">
                  <input
                    id={`scheme-color-${row.key}`}
                    type="color"
                    value={row.hex}
                    onChange={(event) => handleColorChange(row, event.target.value)}
                  />
                  <span>{row.hex.toUpperCase()}</span>
                </div>
              </div>

              <div className="field scheme-row__notes">
                <label htmlFor={`scheme-notes-${row.key}`}>Nota</label>
                <input
                  id={`scheme-notes-${row.key}`}
                  type="text"
                  value={row.notes}
                  onChange={(event) => updateRow(row.key, { notes: event.target.value })}
                  maxLength={255}
                  placeholder="Zona o técnica"
                />
              </div>

              <button
                className="button button--ghost scheme-row__remove"
                type="button"
                onClick={() => handleRemove(row.key)}
                aria-label={`Quitar color ${index + 1}`}
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}

      {displayedError && (
        <p className="form-error" role="alert">
          {displayedError}
        </p>
      )}

      {replace.isSuccess && (
        <p className="form-success" role="status">
          Esquema guardado con {replace.data.length}{' '}
          {replace.data.length === 1 ? 'color' : 'colores'}.
        </p>
      )}

      <div className="form-actions">
        <button
          className="button button--ghost"
          type="button"
          onClick={handleAdd}
          disabled={rows.length >= MAX_COLORS}
        >
          Añadir color
        </button>
        <button className="button" type="submit" disabled={replace.isPending}>
          {replace.isPending ? 'Guardando…' : 'Guardar esquema'}
        </button>
      </div>
    </form>
  )
}
