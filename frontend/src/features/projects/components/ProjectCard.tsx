import { Link } from 'react-router-dom'

import { formatDate, formatScale } from '../format'
import { PROJECT_STATUS_LABELS, type Project } from '../types'

interface ProjectCardProps {
  project: Project
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <article className="project-card">
      <div className="project-card__header">
        <h2>
          <Link to={`/projects/${project.id}`}>{project.name}</Link>
        </h2>
        <span className={`status-badge status-badge--${project.status}`}>
          {PROJECT_STATUS_LABELS[project.status]}
        </span>
      </div>

      <p className="project-card__meta muted">
        {project.subject ?? 'Sin tema'} · {formatScale(project.scale_mm)}
      </p>

      {project.description && <p className="project-card__description">{project.description}</p>}

      <p className="project-card__date muted">Actualizado el {formatDate(project.updated_at)}</p>

      <Link className="button button--ghost" to={`/projects/${project.id}`}>
        Abrir proyecto
      </Link>
    </article>
  )
}
