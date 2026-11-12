export interface User {
  id: string
  email: string
  display_name: string
  is_active: boolean
  created_at: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  display_name: string
}
