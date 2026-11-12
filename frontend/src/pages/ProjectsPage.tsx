import { useDeferredValue, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ProjectCard } from '../features/projects/components/ProjectCard'
import { ProjectForm, type ProjectFormValues } from '../features/projects/components/ProjectForm'
import {
  PROJECT_STATUSES,
  PROJECT_STATUS_LABELS,
  type ProjectFilters,
  type ProjectStatus,
} from '../features/projects/types'
import { useCreateProject, useProjects } from '../features/projects/useProjects'
import { describeError } from '../lib/http'

const PAGE_SIZE = 12

export function ProjectsPage() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const deferredQuery = useDeferredValue(query)
  const navigate = useNavigate()

  const create = useCreateProject()

  const filters: ProjectFilters = {
    q: deferredQuery.trim() || undefined,
    status: status ? (status as ProjectStatus) : undefined,
    limit: PAGE_SIZE,
    offset,
  }

  const projects = useProjects(filters)

  const items = projects.data?.items ?? []
  const total = projects.data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1
  const hasFilters = Boolean(status || query)

  async function handleCreate(values: ProjectFormValues) {
    try {
      const project = await create.mutateAsync({
        name: values.name,
        description: values.description,
        subject: values.subject,
        scale_mm: values.scale_mm,
      })
      navigate(`/projects/${project.id}`)
    } catch {
      // El formulario muestra el error a partir del estado de la mutación.
    }
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Mis proyectos</h1>
          <p className="page-lead">
            Organiza tus miniaturas, define su esquema de color y guarda imágenes de origen y
            avance.
          </p>
        </div>
      </div>

      <div className="card project-create">
        <h2>Nuevo proyecto</h2>
        <ProjectForm
          submitLabel="Crear proyecto"
          isSubmitting={create.isPending}
          error={create.error}
          onSubmit={handleCreate}
        />
      </div>

      <div className="filters">
        <label className="filter-field filter-field--search">
          <span>Buscar</span>
          <input
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setOffset(0)
            }}
            placeholder="Nombre, tema o descripción"
          />
        </label>

        <label className="filter-field">
          <span>Estado</span>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setOffset(0)
            }}
          >
            <option value="">Todos</option>
            {PROJECT_STATUSES.map((value) => (
              <option key={value} value={value}>
                {PROJECT_STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </label>

        {hasFilters && (
          <button
            className="button button--ghost filter-clear"
            type="button"
            onClick={() => {
              setQuery('')
              setStatus('')
              setOffset(0)
            }}
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {projects.isPending ? (
        <p className="muted">Cargando proyectos…</p>
      ) : projects.error ? (
        <p className="form-error" role="alert">
          {describeError(projects.error)}
        </p>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p>
            {hasFilters
              ? 'No hay proyectos que coincidan con los filtros.'
              : 'Todavía no tienes proyectos. Crea el primero con el formulario de arriba.'}
          </p>
        </div>
      ) : (
        <>
          {projects.isFetching && <p className="muted">Actualizando…</p>}

          <div className="project-grid">
            {items.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>

          <nav className="pagination" aria-label="Paginación de proyectos">
            <button
              className="button button--ghost"
              type="button"
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
            >
              Anterior
            </button>
            <span className="muted">
              Página {currentPage} de {pageCount} · {total} proyectos
            </span>
            <button
              className="button button--ghost"
              type="button"
              onClick={() => setOffset(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
            >
              Siguiente
            </button>
          </nav>
        </>
      )}
    </section>
  )
}
