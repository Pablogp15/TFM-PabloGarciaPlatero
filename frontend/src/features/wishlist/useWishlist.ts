import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { wishlistApi } from './api'

export function useWishlist(offset: number) {
  return useQuery({
    queryKey: ['wishlist', 'list', offset],
    queryFn: ({ signal }) => wishlistApi.list(offset, signal),
  })
}

export function useWishlistIds() {
  return useQuery({
    queryKey: ['wishlist', 'ids'],
    queryFn: ({ signal }) => wishlistApi.ids(signal),
  })
}

export function useToggleWishlist() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ paintId, wished }: { paintId: string; wished: boolean }) =>
      wished ? wishlistApi.remove(paintId) : wishlistApi.add(paintId),
    onSuccess: () => client.invalidateQueries({ queryKey: ['wishlist'] }),
  })
}
