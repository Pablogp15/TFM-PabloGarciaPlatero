import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { paintsApi } from './api'
import type { PaintColorFilters, PaintFilters } from './types'

export function usePaints(filters: PaintFilters) {
  return useQuery({
    queryKey: ['paints', 'list', filters],
    queryFn: ({ signal }) => paintsApi.list(filters, signal),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePaintsByColor(filters: PaintColorFilters, enabled: boolean) {
  return useQuery({
    queryKey: ['paints', 'by-color', filters],
    queryFn: ({ signal }) => paintsApi.byColor(filters, signal),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60 * 1000,
  })
}

export function usePaintFacets() {
  return useQuery({
    queryKey: ['paints', 'facets'],
    queryFn: ({ signal }) => paintsApi.facets(signal),
    staleTime: 10 * 60 * 1000,
  })
}

export function useSimilarPaints(paintId: string) {
  return useQuery({
    queryKey: ['paints', 'similar', paintId],
    queryFn: ({ signal }) => paintsApi.similar(paintId, signal),
    staleTime: 5 * 60 * 1000,
  })
}
