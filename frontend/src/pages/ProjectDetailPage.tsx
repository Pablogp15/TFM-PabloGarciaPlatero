import { GuidePanel } from '../features/guides/GuidePanel'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { GenerationPanel } from '../features/generations/GenerationPanel'
import { ProjectForm, type ProjectFormValues } from '../features/projects/components/ProjectForm'
import { ProjectImages } from '../features/projects/components/ProjectImages'
import { SchemeEditor } from '../features/projects/components/SchemeEditor'
import { formatDate, formatScale } from '../features/projects/format'
import {
  PROJECT_STATUS_LABELS,
  SELECTABLE_PROJECT_STATUSES,
  type ProjectUpdate,
  type SelectableProjectStatus,
} from '../features/projects/types'
import { useDeleteProject, useProject, useUpdateProject } from '../features/projects/useProjects'
import { ApiError, describeError } from '../lib/http'

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const project = useProject(projectId)
  const update = useUpdateProject(projectId ?? '')
  const remove = useDeleteProject()
  const [confirmDelete, setConfirmDelete] = useState(false)

  async function handleUpdate(values: ProjectFormValues) {
    const payload: ProjectUpdate = {
      name: values.name,
      description: values.description,
      subject: values.subject,
      scale_mm: values.scale_mm,
    }

    if (SELECTABLE_PROJECT_STATUSES.includes(values.status as SelectableProjectStatus)) {
      payload.status = values.status as SelectableProjectStatus
    }

    try {
      await update.mutateAsync(payload)
    } catch {
      // El formulario muestra el error a partir del estado de la mutación.
    }
  }

  async function handleDelete() {
    if (!projectId) {
      return
    }
    setConfirmDelete(false)
    try {
      await remove.mutateAsync(projectId)
      navigate('/projects', { replace: true })
    } catch {
      // El error se muestra a partir del estado de la mutación.
    }
  }

  if (!projectId) {
    return <ProjectNotFound />
  }

  if (project.isPending) {
    return <p className="muted">Cargando proyecto…</p>
  }

  if (project.error) {
    if (project.error instanceof ApiError && project.error.status === 404) {
      return <ProjectNotFound />
    }
    return (
      <p className="form-error" role="alert">
        {describeError(project.error)}
      </p>
    )
  }

  if (!project.data) {
    return <ProjectNotFound />
  }

  const data = project.data

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="breadcrumb">
            <Link to="/projects">Mis proyectos</Link> / {data.name}
          </p>
          <h1>{data.name}</h1>
          <p className="page-lead">
            {data.subject ?? 'Sin tema'} · {formatScale(data.scale_mm)} · Creado el{' '}
            {formatDate(data.created_at)}
          </p>
        </div>
        <span className={`status-badge status-badge--${data.status}`}>
          {PROJECT_STATUS_LABELS[data.status]}
        </span>
      </div>

      <div className="card">
        <h2>Datos del proyecto</h2>
        <ProjectForm
          key={`${data.id}-${data.updated_at}`}
          initial={data}
          submitLabel="Guardar cambios"
          isSubmitting={update.isPending}
          error={update.error}
          showStatus
          onSubmit={handleUpdate}
        />
      </div>

      <div className="card">
        <h2>Esquema de color</h2>
        <SchemeEditor key={data.id} projectId={data.id} />
      </div>

      <div className="card">
        <h2>Imágenes</h2>
        <ProjectImages key={data.id} projectId={data.id} />
      </div>

      <div className="card">
        <h2>Generar con IA</h2>
        <GenerationPanel key={data.id} projectId={data.id} project={data} />
      </div>

      <div className="card">
        <h2>Guías de pintado</h2>
        <GuidePanel projectId={data.id} />
      </div>

      <div className="card card--danger">
        <h2>Eliminar proyecto</h2>
        <p className="muted">
          Se eliminarán el proyecto, su esquema de color y todas sus imágenes. Esta acción no se
          puede deshacer.
        </p>
        {remove.error && (
          <p className="form-error" role="alert">
            {describeError(remove.error)}
          </p>
        )}
        {confirmDelete ? (
          <div className="form-actions">
            <button
              className="button button--danger"
              type="button"
              onClick={handleDelete}
              disabled={remove.isPending}
            >
              {remove.isPending ? 'Eliminando…' : 'Confirmar eliminación'}
            </button>
            <button
              className="button button--ghost"
              type="button"
              onClick={() => setConfirmDelete(false)}
              disabled={remove.isPending}
            >
              Cancelar
            </button>
          </div>
        ) : (
          <button
            className="button button--danger"
            type="button"
            onClick={() => setConfirmDelete(true)}
          >
            Eliminar proyecto
          </button>
        )}
      </div>
    </section>
  )
}

function ProjectNotFound() {
  return (
    <section className="page">
      <div className="empty-state">
        <p>El proyecto no existe o no tienes acceso a él.</p>
        <Link className="button" to="/projects">
          Volver a mis proyectos
        </Link>
      </div>
    </section>
  )
}
