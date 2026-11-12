import { http } from '../../lib/http'
import { buildQuery } from '../../lib/query'
import type {
  PaintColorFilters,
  PaintColorSearch,
  PaintFacets,
  PaintFilters,
  PaintList,
  SimilarPaint,
} from './types'

export const paintsApi = {
  list(filters: PaintFilters, signal?: AbortSignal): Promise<PaintList> {
    const query = buildQuery({
      q: filters.q,
      brand: filters.brand,
      range_name: filters.range_name,
      paint_type: filters.paint_type,
      finish: filters.finish,
      limit: filters.limit,
      offset: filters.offset,
    })
    return http.get<PaintList>(`/paints${query}`, signal)
  },

  byColor(filters: PaintColorFilters, signal?: AbortSignal): Promise<PaintColorSearch> {
    const query = buildQuery({
      hex_color: filters.hex_color,
      q: filters.q,
      brand: filters.brand,
      range_name: filters.range_name,
      paint_type: filters.paint_type,
      finish: filters.finish,
      limit: filters.limit,
      offset: filters.offset,
    })
    return http.get<PaintColorSearch>(`/paints/by-color${query}`, signal)
  },

  facets(signal?: AbortSignal): Promise<PaintFacets> {
    return http.get<PaintFacets>('/paints/facets', signal)
  },

  similar(paintId: string, signal?: AbortSignal): Promise<SimilarPaint[]> {
    return http.get<SimilarPaint[]>(
      `/paints/${encodeURIComponent(paintId)}/similar?limit=6`,
      signal,
    )
  },
}
