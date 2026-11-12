import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { authApi } from './api'
import type { LoginPayload, RegisterPayload } from './types'

export const sessionQueryKey = ['auth', 'session'] as const

/** Sesión actual. La resolución del usuario la hace siempre el backend. */
export function useSession() {
  return useQuery({
    queryKey: sessionQueryKey,
    queryFn: ({ signal }) => authApi.session(signal),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    onSuccess: (user) => {
      // Se descarta cualquier dato cacheado de una sesión anterior.
      queryClient.clear()
      queryClient.setQueryData(sessionQueryKey, user)
    },
  })
}

export function useRegister() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: RegisterPayload) => authApi.register(payload),
    onSuccess: (user) => {
      queryClient.clear()
      queryClient.setQueryData(sessionQueryKey, user)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: authApi.logout,
    // Aunque la petición falle, la sesión local deja de considerarse válida.
    onSettled: () => {
      queryClient.clear()
      queryClient.setQueryData(sessionQueryKey, null)
    },
  })
}
