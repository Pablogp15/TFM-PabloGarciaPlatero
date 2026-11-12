import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { FormField } from '../components/FormField'
import { useLogin, useSession } from '../features/auth/useAuth'
import { describeError } from '../lib/http'

interface LocationState {
  from?: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const session = useSession()
  const login = useLogin()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  if (session.isPending) {
    return <p className="muted">Comprobando sesión…</p>
  }

  if (session.data) {
    return <Navigate to="/" replace />
  }

  const redirectTo = (location.state as LocationState | null)?.from ?? '/'

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    try {
      await login.mutateAsync({ email, password })
      navigate(redirectTo, { replace: true })
    } catch {
      // El mensaje de error se muestra a partir de `login.error`.
    }
  }

  return (
    <section className="page auth-page">
      <h1>Iniciar sesión</h1>
      <p className="page-lead">Accede para gestionar tus pinturas y proyectos.</p>

      <form className="card form" onSubmit={handleSubmit}>
        <FormField
          id="email"
          label="Correo electrónico"
          type="email"
          value={email}
          onChange={setEmail}
          autoComplete="email"
          required
        />
        <FormField
          id="password"
          label="Contraseña"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          required
        />

        {login.error && (
          <p className="form-error" role="alert">
            {describeError(login.error)}
          </p>
        )}

        <button className="button" type="submit" disabled={login.isPending}>
          {login.isPending ? 'Entrando…' : 'Entrar'}
        </button>
      </form>

      <p className="auth-alt">
        ¿No tienes cuenta? <Link to="/register">Crear una cuenta</Link>
      </p>
    </section>
  )
}
