import { useRef, useState, type FormEvent } from 'react'

import { describeError } from '../../../lib/http'
import { formatBytes, formatDate } from '../format'
import {
  IMAGE_KIND_LABELS,
  UPLOAD_IMAGE_KINDS,
  type ProjectImage,
  type UploadImageKind,
} from '../types'
import { useDeleteProjectImage, useProjectImages, useUploadProjectImage } from '../useProjects'

interface ProjectImagesProps {
  projectId: string
}

const MAX_BYTES = 10 * 1024 * 1024
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/jpg', 'image/png', 'image/webp'])

export function ProjectImages({ projectId }: ProjectImagesProps) {
  const images = useProjectImages(projectId)
  const upload = useUploadProjectImage(projectId)
  const remove = useDeleteProjectImage(projectId)

  const fileInput = useRef<HTMLInputElement>(null)
  const [kind, setKind] = useState<UploadImageKind>('source')
  const [file, setFile] = useState<File | null>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)

  function handleFileChange(selected: File | null) {
    setClientError(null)
    setFile(selected)

    if (!selected) {
      return
    }
    if (selected.size > MAX_BYTES) {
      setClientError('La imagen supera el límite de 10 MB')
      setFile(null)
      return
    }
    if (selected.type && !ALLOWED_TYPES.has(selected.type)) {
      setClientError('Formato no permitido. Usa JPEG, PNG o WebP')
      setFile(null)
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!file) {
      setClientError('Selecciona una imagen antes de subirla')
      return
    }

    setClientError(null)
    try {
      await upload.mutateAsync({ kind, file })
      setFile(null)
      if (fileInput.current) {
        fileInput.current.value = ''
      }
    } catch {
      // El error se muestra a partir del estado de la mutación.
    }
  }

  function handleDelete(image: ProjectImage) {
    setConfirmId(null)
    remove.mutate(image.id)
  }

  const items = images.data?.items ?? []
  const displayedError =
    clientError ??
    (upload.error ? describeError(upload.error) : null) ??
    (remove.error ? describeError(remove.error) : null)

  return (
    <div className="project-images">
      <form className="image-upload" onSubmit={handleUpload}>
        <div className="form-row">
          <div className="field">
            <label htmlFor="image-kind">Tipo de imagen</label>
            <select
              id="image-kind"
              value={kind}
              onChange={(event) => setKind(event.target.value as UploadImageKind)}
            >
              {UPLOAD_IMAGE_KINDS.map((value) => (
                <option key={value} value={value}>
                  {IMAGE_KIND_LABELS[value]}
                </option>
              ))}
            </select>
          </div>

          <div className="field image-upload__file">
            <label htmlFor="image-file">Archivo</label>
            <input
              id="image-file"
              ref={fileInput}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
            />
          </div>
        </div>

        <p className="field-hint">
          JPEG, PNG o WebP · máximo 10 MB · hasta 4096 px por lado y 24 MP.
        </p>

        {displayedError && (
          <p className="form-error" role="alert">
            {displayedError}
          </p>
        )}

        {upload.isSuccess && !upload.error && (
          <p className="form-success" role="status">
            Imagen guardada correctamente.
          </p>
        )}

        <div className="form-actions">
          <button className="button" type="submit" disabled={upload.isPending}>
            {upload.isPending ? 'Subiendo…' : 'Subir imagen'}
          </button>
        </div>
      </form>

      {images.isPending ? (
        <p className="muted">Cargando imágenes…</p>
      ) : images.error ? (
        <p className="form-error" role="alert">
          {describeError(images.error)}
        </p>
      ) : items.length === 0 ? (
        <p className="empty-inline">Este proyecto todavía no tiene imágenes.</p>
      ) : (
        <ul className="image-grid">
          {items.map((image) => {
            const deleting = remove.isPending && remove.variables === image.id

            return (
              <li className="image-card" key={image.id}>
                <a className="image-card__frame" href={image.url} target="_blank" rel="noreferrer">
                  <img
                    src={image.url}
                    alt={`${IMAGE_KIND_LABELS[image.kind]} del proyecto`}
                    loading="lazy"
                    width={image.width}
                    height={image.height}
                  />
                </a>
                <div className="image-card__body">
                  <span className="badge">{IMAGE_KIND_LABELS[image.kind]}</span>
                  <span className="muted image-card__meta">
                    {image.width} × {image.height} px · {formatBytes(image.size_bytes)}
                  </span>
                  <span className="muted image-card__meta">{formatDate(image.created_at)}</span>

                  {confirmId === image.id ? (
                    <div className="image-card__actions">
                      <button
                        className="button button--danger"
                        type="button"
                        onClick={() => handleDelete(image)}
                        disabled={deleting}
                      >
                        {deleting ? 'Quitando…' : 'Confirmar'}
                      </button>
                      <button
                        className="button button--ghost"
                        type="button"
                        onClick={() => setConfirmId(null)}
                      >
                        Cancelar
                      </button>
                    </div>
                  ) : (
                    <button
                      className="button button--ghost"
                      type="button"
                      onClick={() => setConfirmId(image.id)}
                    >
                      Eliminar
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
