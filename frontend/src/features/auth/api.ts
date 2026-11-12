import { ApiError, http } from '../../lib/http'
import type { LoginPayload, RegisterPayload, User } from './types'

export const authApi = {
  /** Devuelve el usuario de la sesión o `null` si no hay sesión válida. */
  async session(signal?: AbortSignal): Promise<User | null> {
    try {
      return await http.get<User>('/auth/me', signal)
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        return null
      }
      throw error
    }
  },

  login: (payload: LoginPayload): Promise<User> => http.post<User>('/auth/login', payload),

  register: (payload: RegisterPayload): Promise<User> => http.post<User>('/auth/register', payload),

  logout: (): Promise<void> => http.post<void>('/auth/logout'),
}
