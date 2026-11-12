import { http } from '../../lib/http'
import { buildQuery } from '../../lib/query'
import type {
  InventoryFilters,
  InventoryItem,
  InventoryItemCreate,
  InventoryItemUpdate,
  InventoryList,
  InventoryStats,
} from './types'

export const inventoryApi = {
  list(filters: InventoryFilters, signal?: AbortSignal): Promise<InventoryList> {
    const query = buildQuery({
      running_low: filters.running_low,
      brand: filters.brand,
      q: filters.q,
      limit: filters.limit,
      offset: filters.offset,
    })
    return http.get<InventoryList>(`/inventory${query}`, signal)
  },

  stats(signal?: AbortSignal): Promise<InventoryStats> {
    return http.get<InventoryStats>('/inventory/stats', signal)
  },

  add(payload: InventoryItemCreate): Promise<InventoryItem> {
    return http.post<InventoryItem>('/inventory', payload)
  },

  update(id: string, payload: InventoryItemUpdate): Promise<InventoryItem> {
    return http.patch<InventoryItem>(`/inventory/${encodeURIComponent(id)}`, payload)
  },

  remove(id: string): Promise<void> {
    return http.delete<void>(`/inventory/${encodeURIComponent(id)}`)
  },
}
