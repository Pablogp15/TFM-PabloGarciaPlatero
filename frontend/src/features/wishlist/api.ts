import { http } from '../../lib/http'
import type { Paint } from '../paints/types'

export interface WishlistList {
  items: { paint: Paint; created_at: string }[]
  total: number
  limit: number
  offset: number
}

export const wishlistApi = {
  list: (offset: number, signal?: AbortSignal) =>
    http.get<WishlistList>(`/wishlist?limit=24&offset=${offset}`, signal),
  ids: (signal?: AbortSignal) => http.get<string[]>('/wishlist/paint-ids', signal),
  add: (paintId: string) => http.post<void>('/wishlist', { paint_id: paintId }),
  remove: (paintId: string) => http.delete<void>(`/wishlist/${encodeURIComponent(paintId)}`),
}
