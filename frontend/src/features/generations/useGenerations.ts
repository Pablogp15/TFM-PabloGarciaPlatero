import { useEffect, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { projectsQueryKey } from '../projects/useProjects'
import { generationsApi } from './api'
import { isGenerationActive } from './format'
import type { GenerationCreate, GenerationList } from './types'

export const generationsQueryKey = ['generations'] as const

function listKey(projectId: string) {
  return [...generationsQueryKey, 'list', projectId] as const
}

function projectKey(projectId: string) {
  return [...projectsQueryKey, 'detail', projectId] as const
}

function imagesKey(projectId: string) {
  return [...projectsQueryKey, 'images', projectId] as const
}

export function useGenerations(projectId: string) {
  return useQuery({
    queryKey: listKey(projectId),
    queryFn: ({ signal }) => generationsApi.list(projectId, signal),
    enabled: Boolean(projectId),
    // Mientras haya un trabajo activo se consulta el progreso periódicamente.
    refetchInterval: (query) => {
      const data = query.state.data as GenerationList | undefined
      return data?.items.some((item) => isGenerationActive(item.status)) ? 2000 : false
    },
  })
}

export function useCreateGeneration(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: GenerationCreate) => generationsApi.create(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listKey(projectId) })
      return queryClient.invalidateQueries({ queryKey: projectKey(projectId) })
    },
  })
}

export function useCancelGeneration(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (generationId: string) => generationsApi.cancel(generationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: listKey(projectId) })
      return queryClient.invalidateQueries({ queryKey: projectKey(projectId) })
    },
  })
}

/** Invalida las imágenes y el proyecto cuando una generación deja de estar activa. */
export function useGenerationCompletion(projectId: string, hasActive: boolean) {
  const queryClient = useQueryClient()
  const wasActive = useRef(false)

  useEffect(() => {
    if (wasActive.current && !hasActive) {
      void queryClient.invalidateQueries({ queryKey: imagesKey(projectId) })
      void queryClient.invalidateQueries({ queryKey: projectKey(projectId) })
    }
    wasActive.current = hasActive
  }, [hasActive, projectId, queryClient])
}
