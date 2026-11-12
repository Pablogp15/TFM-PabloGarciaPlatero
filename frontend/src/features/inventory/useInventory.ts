import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { inventoryApi } from './api'
import type { InventoryFilters, InventoryItemCreate, InventoryItemUpdate } from './types'

const inventoryKey = ['inventory'] as const

export function useInventory(filters: InventoryFilters) {
  return useQuery({
    queryKey: [...inventoryKey, 'list', filters],
    queryFn: ({ signal }) => inventoryApi.list(filters, signal),
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
  })
}

export function useInventoryStats() {
  return useQuery({
    queryKey: [...inventoryKey, 'stats'],
    queryFn: ({ signal }) => inventoryApi.stats(signal),
    staleTime: 30 * 1000,
  })
}

function useInvalidateInventory() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: inventoryKey })
}

export function useAddInventoryItem() {
  const invalidate = useInvalidateInventory()

  return useMutation({
    mutationFn: (payload: InventoryItemCreate) => inventoryApi.add(payload),
    onSuccess: () => invalidate(),
  })
}

export function useUpdateInventoryItem() {
  const invalidate = useInvalidateInventory()

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: InventoryItemUpdate }) =>
      inventoryApi.update(id, payload),
    onSuccess: () => invalidate(),
  })
}

export function useDeleteInventoryItem() {
  const invalidate = useInvalidateInventory()

  return useMutation({
    mutationFn: (id: string) => inventoryApi.remove(id),
    onSuccess: () => invalidate(),
  })
}
