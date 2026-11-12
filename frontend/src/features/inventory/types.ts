import type { Paint } from '../paints/types'

export interface InventoryItem {
  id: string
  paint: Paint
  quantity: number
  running_low: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface InventoryList {
  items: InventoryItem[]
  total: number
  limit: number
  offset: number
}

export interface InventoryStats {
  total_items: number
  total_quantity: number
  owned: number
  running_low: number
  brands: number
}

export interface InventoryFilters {
  running_low?: boolean
  brand?: string
  q?: string
  limit?: number
  offset?: number
}

export interface InventoryItemCreate {
  paint_id: string
  quantity?: number
  running_low?: boolean
  notes?: string | null
}

export interface InventoryItemUpdate {
  quantity?: number
  running_low?: boolean
  notes?: string | null
}
