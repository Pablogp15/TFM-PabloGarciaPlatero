import { http } from '../../lib/http'
import { buildQuery } from '../../lib/query'
import type { Generation, GenerationCreate, GenerationList } from './types'

function projectPath(projectId: string): string {
  return `/projects/${encodeURIComponent(projectId)}/generations`
}

export const generationsApi = {
  list(projectId: string, signal?: AbortSignal): Promise<GenerationList> {
    const query = buildQuery({ limit: 20, offset: 0 })
    return http.get<GenerationList>(`${projectPath(projectId)}${query}`, signal)
  },

  create(projectId: string, payload: GenerationCreate): Promise<Generation> {
    return http.post<Generation>(projectPath(projectId), payload)
  },

  cancel(generationId: string): Promise<Generation> {
    return http.post<Generation>(`/generations/${encodeURIComponent(generationId)}/cancel`)
  },
}
