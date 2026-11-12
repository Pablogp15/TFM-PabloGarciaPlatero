const API_BASE = '/api/v1'
const CSRF_COOKIE = 'mp_csrf'
const CSRF_HEADER = 'X-CSRF-Token'
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

/** Error normalizado de la API. `status` 0 indica un fallo de red. */
export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  form?: FormData
  signal?: AbortSignal
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`
  for (const part of document.cookie.split(';')) {
    const entry = part.trim()
    if (entry.startsWith(prefix)) {
      const raw = entry.slice(prefix.length)
      try {
        return decodeURIComponent(raw)
      } catch {
        // Un valor manipulado no debe romper la aplicación.
        return raw
      }
    }
  }
  return null
}

let csrfRequest: Promise<string> | null = null

/** Garantiza que exista la cookie CSRF antes de una petición de escritura. */
async function ensureCsrfToken(): Promise<string> {
  const current = readCookie(CSRF_COOKIE)
  if (current) {
    return current
  }

  csrfRequest ??= fetch(`${API_BASE}/auth/csrf`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
    .then(() => readCookie(CSRF_COOKIE) ?? '')
    .finally(() => {
      csrfRequest = null
    })

  try {
    return await csrfRequest
  } catch {
    throw new ApiError(0, 'No se pudo conectar con el servidor')
  }
}

let refreshRequest: Promise<boolean> | null = null

/** Refresco con única ejecución concurrente: varias peticiones comparten el mismo. */
function refreshSession(): Promise<boolean> {
  refreshRequest ??= (async () => {
    try {
      const csrf = await ensureCsrfToken()
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { [CSRF_HEADER]: csrf },
      })
      return response.ok
    } catch {
      // Un fallo de red no debe ocultar el 401 original de la petición.
      return false
    }
  })().finally(() => {
    refreshRequest = null
  })

  return refreshRequest
}

function extractDetail(payload: unknown, fallback: string): string {
  if (typeof payload !== 'object' || payload === null || !('detail' in payload)) {
    return fallback
  }

  const detail = (payload as { detail: unknown }).detail

  if (typeof detail === 'string') {
    return detail
  }

  // FastAPI devuelve un array de errores de validación. No se expone su
  // contenido técnico: el formulario ya valida antes de enviar.
  if (Array.isArray(detail)) {
    return 'Los datos enviados no son válidos'
  }

  return fallback
}

async function toApiError(response: Response): Promise<ApiError> {
  const fallback = response.statusText || 'Error inesperado'
  try {
    const payload: unknown = await response.json()
    return new ApiError(response.status, extractDetail(payload, fallback))
  } catch {
    // La respuesta no era JSON: se conserva el texto del estado HTTP.
    return new ApiError(response.status, fallback)
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const mutating = MUTATING_METHODS.has(method)

  const send = async (): Promise<Response> => {
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (options.body !== undefined) {
      headers['Content-Type'] = 'application/json'
    }
    if (mutating) {
      headers[CSRF_HEADER] = await ensureCsrfToken()
    }

    // Con FormData no se fija Content-Type: el navegador debe añadir el
    // boundary del multipart. Hacerlo manualmente rompería la subida.
    const body =
      options.form ?? (options.body === undefined ? undefined : JSON.stringify(options.body))

    try {
      return await fetch(`${API_BASE}${path}`, {
        method,
        credentials: 'include',
        headers,
        body,
        signal: options.signal,
      })
    } catch {
      throw new ApiError(0, 'No se pudo conectar con el servidor')
    }
  }

  let response = await send()

  if (response.status === 401) {
    const refreshed = await refreshSession()
    if (refreshed) {
      response = await send()
    }
  }

  if (!response.ok) {
    throw await toApiError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const text = await response.text()
  if (!text) {
    return undefined as T
  }

  try {
    return JSON.parse(text) as T
  } catch {
    throw new ApiError(response.status, 'La respuesta del servidor no es válida')
  }
}

export const http = {
  get: <T>(path: string, signal?: AbortSignal): Promise<T> => request<T>(path, { signal }),
  post: <T>(path: string, body?: unknown): Promise<T> => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown): Promise<T> => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, { method: 'PATCH', body }),
  upload: <T>(path: string, form: FormData, signal?: AbortSignal): Promise<T> =>
    request<T>(path, { method: 'POST', form, signal }),
  delete: <T>(path: string): Promise<T> => request<T>(path, { method: 'DELETE' }),
}

/** Traduce un error desconocido a un mensaje apto para la interfaz. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return error.detail
  }
  return 'Ha ocurrido un error inesperado'
}
