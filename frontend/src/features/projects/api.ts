import { http } from '../../lib/http'
import { buildQuery } from '../../lib/query'
import type {
  Project,
  ProjectCreate,
  ProjectFilters,
  ProjectImage,
  ProjectImageList,
  ProjectList,
  ProjectUpdate,
  SchemeColor,
  SchemeColorInput,
  UploadImageKind,
} from './types'

export const projectsApi = {
  list(filters: ProjectFilters, signal?: AbortSignal): Promise<ProjectList> {
    const query = buildQuery({
      status: filters.status,
      q: filters.q,
      limit: filters.limit,
      offset: filters.offset,
    })
    return http.get<ProjectList>(`/projects${query}`, signal)
  },

  get(projectId: string, signal?: AbortSignal): Promise<Project> {
    return http.get<Project>(`/projects/${encodeURIComponent(projectId)}`, signal)
  },

  create(payload: ProjectCreate): Promise<Project> {
    return http.post<Project>('/projects', payload)
  },

  update(projectId: string, payload: ProjectUpdate): Promise<Project> {
    return http.patch<Project>(`/projects/${encodeURIComponent(projectId)}`, payload)
  },

  remove(projectId: string): Promise<void> {
    return http.delete<void>(`/projects/${encodeURIComponent(projectId)}`)
  },

  schemeColors(projectId: string, signal?: AbortSignal): Promise<SchemeColor[]> {
    return http.get<SchemeColor[]>(
      `/projects/${encodeURIComponent(projectId)}/scheme-colors`,
      signal,
    )
  },

  replaceSchemeColors(projectId: string, colors: SchemeColorInput[]): Promise<SchemeColor[]> {
    return http.put<SchemeColor[]>(`/projects/${encodeURIComponent(projectId)}/scheme-colors`, {
      colors,
    })
  },

  images(projectId: string, signal?: AbortSignal): Promise<ProjectImageList> {
    return http.get<ProjectImageList>(
      `/projects/${encodeURIComponent(projectId)}/images?limit=100`,
      signal,
    )
  },

  uploadImage(projectId: string, kind: UploadImageKind, file: File): Promise<ProjectImage> {
    const form = new FormData()
    form.append('kind', kind)
    form.append('file', file, file.name)
    return http.upload<ProjectImage>(`/projects/${encodeURIComponent(projectId)}/images`, form)
  },

  removeImage(projectId: string, imageId: string): Promise<void> {
    return http.delete<void>(
      `/projects/${encodeURIComponent(projectId)}/images/${encodeURIComponent(imageId)}`,
    )
  },
}
