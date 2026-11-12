import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

import { ApiError, describeError, http } from './http'

type FetchCall = [input: RequestInfo | URL, init?: RequestInit]

let fetchMock: Mock<typeof fetch>

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function setCookie(name: string, value: string): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/`
}

function clearCookies(): void {
  for (const entry of document.cookie.split(';')) {
    const name = entry.split('=')[0]?.trim()
    if (name) {
      document.cookie = `${name}=; path=/; max-age=0`
    }
  }
}

function call(index: number): FetchCall {
  return fetchMock.mock.calls[index] as FetchCall
}

function headersOf(index: number): Record<string, string> {
  return (call(index)[1]?.headers ?? {}) as Record<string, string>
}

function urls(): string[] {
  return fetchMock.mock.calls.map(([input]) => String(input))
}

beforeEach(() => {
  clearCookies()
  fetchMock = vi.fn<typeof fetch>()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('http', () => {
  it('envía las credenciales en las lecturas y no añade CSRF', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: 'ok' }))

    const result = await http.get<{ status: string }>('/health')

    expect(result).toEqual({ status: 'ok' })
    expect(call(0)[0]).toBe('/api/v1/health')
    expect(call(0)[1]?.credentials).toBe('include')
    expect(headersOf(0)['X-CSRF-Token']).toBeUndefined()
  })

  it('añade la cabecera CSRF y serializa el cuerpo en las escrituras', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { id: 'u1' }))

    await http.post('/auth/login', { email: 'pintor@example.com' })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(headersOf(0)['X-CSRF-Token']).toBe('aleatorio.firma')
    expect(headersOf(0)['Content-Type']).toBe('application/json')
    expect(call(0)[1]?.body).toBe('{"email":"pintor@example.com"}')
  })

  it('solicita el token CSRF cuando todavía no existe la cookie', async () => {
    fetchMock.mockImplementationOnce(async () => {
      setCookie('mp_csrf', 'nuevo.firma')
      return jsonResponse(200, { csrf_token: 'nuevo.firma' })
    })
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await http.post('/auth/logout')

    expect(urls()).toEqual(['/api/v1/auth/csrf', '/api/v1/auth/logout'])
    expect(headersOf(1)['X-CSRF-Token']).toBe('nuevo.firma')
  })

  it('renueva la sesión y reintenta una sola vez tras un 401', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'No autenticado' }))
      .mockResolvedValueOnce(jsonResponse(200, { id: 'u1' }))
      .mockResolvedValueOnce(jsonResponse(200, { email: 'pintor@example.com' }))

    const user = await http.get<{ email: string }>('/auth/me')

    expect(user).toEqual({ email: 'pintor@example.com' })
    expect(urls()).toEqual(['/api/v1/auth/me', '/api/v1/auth/refresh', '/api/v1/auth/me'])
  })

  it('comparte un único refresco entre peticiones concurrentes', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    let meCalls = 0

    fetchMock.mockImplementation(async (input) => {
      const url = String(input)
      if (url.endsWith('/auth/refresh')) {
        return jsonResponse(200, { id: 'u1' })
      }
      meCalls += 1
      return meCalls <= 2
        ? jsonResponse(401, { detail: 'No autenticado' })
        : jsonResponse(200, { id: 'u1' })
    })

    const [first, second] = await Promise.all([
      http.get<{ id: string }>('/auth/me'),
      http.get<{ id: string }>('/auth/me'),
    ])

    expect(first).toEqual({ id: 'u1' })
    expect(second).toEqual({ id: 'u1' })
    expect(urls().filter((url) => url.endsWith('/auth/refresh'))).toHaveLength(1)
  })

  it('propaga el 401 cuando el refresco también falla', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'No autenticado' }))
      .mockResolvedValueOnce(jsonResponse(401, { detail: 'Sesión caducada' }))

    await expect(http.get('/auth/me')).rejects.toMatchObject({ status: 401 })
    expect(urls()).toEqual(['/api/v1/auth/me', '/api/v1/auth/refresh'])
  })

  it('devuelve undefined en las respuestas 204', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await expect(http.post('/auth/logout')).resolves.toBeUndefined()
  })

  it('añade CSRF y serializa el cuerpo en PATCH, y no envía cuerpo en DELETE', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { id: 'p1' }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))

    await http.patch('/inventory/p1', { quantity: 2 })
    await http.delete('/inventory/p1')

    expect(headersOf(0)['X-CSRF-Token']).toBe('aleatorio.firma')
    expect(headersOf(0)['Content-Type']).toBe('application/json')
    expect(call(0)[1]?.body).toBe('{"quantity":2}')
    expect(headersOf(1)['X-CSRF-Token']).toBe('aleatorio.firma')
    expect(headersOf(1)['Content-Type']).toBeUndefined()
    expect(call(1)[1]?.body).toBeUndefined()
  })

  it('envía FormData con CSRF y sin fijar Content-Type', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock.mockResolvedValueOnce(jsonResponse(201, { id: 'img1' }))

    const form = new FormData()
    form.append('kind', 'source')
    form.append('file', new Blob(['contenido'], { type: 'image/png' }), 'origen.png')

    const result = await http.upload<{ id: string }>('/projects/p1/images', form)

    expect(result).toEqual({ id: 'img1' })
    expect(call(0)[0]).toBe('/api/v1/projects/p1/images')
    expect(call(0)[1]?.method).toBe('POST')
    expect(call(0)[1]?.credentials).toBe('include')
    expect(call(0)[1]?.body).toBe(form)
    expect(headersOf(0)['X-CSRF-Token']).toBe('aleatorio.firma')
    expect(headersOf(0)['Content-Type']).toBeUndefined()
  })

  it('añade CSRF y serializa el cuerpo en PUT', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock.mockResolvedValueOnce(jsonResponse(200, []))

    await http.put('/projects/p1/scheme-colors', { colors: [] })

    expect(call(0)[1]?.method).toBe('PUT')
    expect(headersOf(0)['X-CSRF-Token']).toBe('aleatorio.firma')
    expect(headersOf(0)['Content-Type']).toBe('application/json')
    expect(call(0)[1]?.body).toBe('{"colors":[]}')
  })

  it('traduce los errores de validación de FastAPI sin exponer detalles', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock.mockResolvedValueOnce(
      jsonResponse(422, { detail: [{ loc: ['body', 'password'], msg: 'too short' }] }),
    )

    const error = await http.post('/auth/register', {}).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 422,
      detail: 'Los datos enviados no son válidos',
    })
  })

  it('conserva el mensaje de error del servidor', async () => {
    setCookie('mp_csrf', 'aleatorio.firma')
    fetchMock.mockResolvedValueOnce(
      jsonResponse(409, { detail: 'Ya existe una cuenta con ese correo' }),
    )

    await expect(http.post('/auth/register', {})).rejects.toMatchObject({
      status: 409,
      detail: 'Ya existe una cuenta con ese correo',
    })
  })

  it('convierte un fallo de red en un error de estado 0', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    const error = await http.get('/auth/me').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 0 })
  })
})

describe('describeError', () => {
  it('usa el detalle del ApiError', () => {
    expect(describeError(new ApiError(400, 'Petición inválida'))).toBe('Petición inválida')
  })

  it('oculta los errores que no vienen de la API', () => {
    expect(describeError(new Error('boom'))).toBe('Ha ocurrido un error inesperado')
  })
})
