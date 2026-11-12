import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { guidesApi, type StepProgress } from './api'

export function useGuides(projectId: string) {
  return useQuery({
    queryKey: ['guides', projectId],
    queryFn: ({ signal }) => guidesApi.list(projectId, signal),
    refetchInterval: (query) =>
      query.state.data?.items.some((guide) => ['pending', 'generating'].includes(guide.status))
        ? 2000
        : false,
  })
}
export function useGuideActions(projectId: string) {
  const client = useQueryClient()
  const invalidate = () => client.invalidateQueries({ queryKey: ['guides', projectId] })
  const create = useMutation({
    mutationFn: (imageId: string) => guidesApi.create(projectId, imageId),
    onSuccess: invalidate,
  })
  const cancel = useMutation({
    mutationFn: (id: string) => guidesApi.cancel(projectId, id),
    onSuccess: invalidate,
  })
  const progress = useMutation({
    mutationFn: ({
      guideId,
      stepId,
      body,
    }: {
      guideId: string
      stepId: string
      body: StepProgress
    }) => guidesApi.progress(projectId, guideId, stepId, body),
    onSuccess: invalidate,
  })
  return { create, cancel, progress }
}
