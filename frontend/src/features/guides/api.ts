import { http } from '../../lib/http'

export interface GuideStep {
  id: string
  position: number
  title: string
  zone: string
  objective: string
  technique: string
  description: string
  continue_when: string
  source_ids: string[]
  paint_ids: string[]
  time_minutes: number | null
  is_optional: boolean
  completed: boolean
  progress_note: string | null
  minutes_spent: number
}
export interface Guide {
  id: string
  project_id: string
  target_image_id: string | null
  status: 'pending' | 'generating' | 'ready' | 'failed'
  stage: string
  summary: string | null
  limitations: string[]
  error_message: string | null
  cancel_requested: boolean
  unavailable_paint_ids: string[]
  created_at: string
  context: { inventory?: { id: string; name: string; brand: string; running_low: boolean }[] }
  sources: {
    id: string
    title: string
    content: string
    metadata: { location?: string; source?: string }
  }[]
  steps: GuideStep[]
}
export interface GuideList {
  items: Guide[]
  corpus_ready: boolean
}
export interface StepProgress {
  completed: boolean
  note: string | null
  minutes_spent: number
}
const path = (projectId: string) => `/projects/${encodeURIComponent(projectId)}/guides`
export const guidesApi = {
  list: (projectId: string, signal?: AbortSignal) => http.get<GuideList>(path(projectId), signal),
  create: (projectId: string, imageId: string) =>
    http.post<Guide>(path(projectId), { image_id: imageId }),
  cancel: (projectId: string, id: string) =>
    http.post<Guide>(`${path(projectId)}/${encodeURIComponent(id)}/cancel`),
  progress: (projectId: string, guideId: string, stepId: string, body: StepProgress) =>
    http.put<Guide>(
      `${path(projectId)}/${encodeURIComponent(guideId)}/steps/${encodeURIComponent(stepId)}/progress`,
      body,
    ),
}
