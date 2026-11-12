import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectsApi } from './api'
import type {
  ProjectCreate,
  ProjectFilters,
  ProjectUpdate,
  SchemeColorInput,
  UploadImageKind,
} from './types'

export const projectsQueryKey = ['projects'] as const

function projectKey(projectId: string) {
  return [...projectsQueryKey, 'detail', projectId] as const
}

function schemeKey(projectId: string) {
  return [...projectsQueryKey, 'scheme', projectId] as const
}

function imagesKey(projectId: string) {
  return [...projectsQueryKey, 'images', projectId] as const
}

export function useProjects(filters: ProjectFilters) {
  return useQuery({
    queryKey: [...projectsQueryKey, 'list', filters],
    queryFn: ({ signal }) => projectsApi.list(filters, signal),
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
  })
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: projectKey(projectId ?? ''),
    queryFn: ({ signal }) => projectsApi.get(projectId as string, signal),
    enabled: Boolean(projectId),
    staleTime: 30 * 1000,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ProjectCreate) => projectsApi.create(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: projectsQueryKey }),
  })
}

export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ProjectUpdate) => projectsApi.update(projectId, payload),
    onSuccess: (project) => {
      queryClient.setQueryData(projectKey(projectId), project)
      return queryClient.invalidateQueries({ queryKey: projectsQueryKey })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (projectId: string) => projectsApi.remove(projectId),
    onSuccess: (_result, projectId) => {
      queryClient.removeQueries({ queryKey: projectKey(projectId) })
      return queryClient.invalidateQueries({ queryKey: projectsQueryKey })
    },
  })
}

export function useSchemeColors(projectId: string) {
  return useQuery({
    queryKey: schemeKey(projectId),
    queryFn: ({ signal }) => projectsApi.schemeColors(projectId, signal),
    staleTime: 30 * 1000,
  })
}

export function useReplaceSchemeColors(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (colors: SchemeColorInput[]) => projectsApi.replaceSchemeColors(projectId, colors),
    onSuccess: (colors) => {
      queryClient.setQueryData(schemeKey(projectId), colors)
      return queryClient.invalidateQueries({ queryKey: projectKey(projectId) })
    },
  })
}

export function useProjectImages(projectId: string) {
  return useQuery({
    queryKey: imagesKey(projectId),
    queryFn: ({ signal }) => projectsApi.images(projectId, signal),
    staleTime: 15 * 1000,
  })
}

export function useUploadProjectImage(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ kind, file }: { kind: UploadImageKind; file: File }) =>
      projectsApi.uploadImage(projectId, kind, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: imagesKey(projectId) })
      return queryClient.invalidateQueries({ queryKey: projectKey(projectId) })
    },
  })
}

export function useDeleteProjectImage(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (imageId: string) => projectsApi.removeImage(projectId, imageId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: imagesKey(projectId) })
      return queryClient.invalidateQueries({ queryKey: projectKey(projectId) })
    },
  })
}
