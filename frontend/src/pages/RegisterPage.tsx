import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'

import { FormField } from '../components/FormField'
import { useRegister, useSession } from '../features/auth/useAuth'
import { describeError } from '../lib/http'

const MIN_PASSWORD_LENGTH = 12

export function RegisterPage() {
  const navigate = useNavigate()
  const session = useSession()
  const register = useRegister()

  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)

  if (session.isPending) {
    return <p className="muted">Comprobando sesión…</p>
  }

  if (session.data) {
    return <Navigate to="/" replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (password.length < MIN_PASSWORD_LENGTH) {
      setValidationError(`La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`)
      return
    }

    setValidationError(null)
    try {
      await register.mutateAsync({ email, password, display_name: displayName })
      navigate('/', { replace: true })
    } catch {
      // El mensaje de error se muestra a partir de `register.error`.
    }
  }

  const errorMessage = validationError ?? (register.error ? describeError(register.error) : null)

  return (
    <section className="page auth-page">
      <h1>Crear cuenta</h1>
      <p className="page-lead">
        Registra tu cuenta para guardar el inventario de pinturas y tus proyectos.
      </p>

      <form className="card form" onSubmit={handleSubmit}>
        <FormField
          id="display_name"
          label="Nombre"
          value={displayName}
          onChange={setDisplayName}
          autoComplete="nickname"
          required
        />
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
          autoComplete="new-password"
          required
          minLength={MIN_PASSWORD_LENGTH}
          hint={`Mínimo ${MIN_PASSWORD_LENGTH} caracteres.`}
        />

        {errorMessage && (
          <p className="form-error" role="alert">
            {errorMessage}
          </p>
        )}

        <button className="button" type="submit" disabled={register.isPending}>
          {register.isPending ? 'Creando cuenta…' : 'Crear cuenta'}
        </button>
      </form>

      <p className="auth-alt">
        ¿Ya tienes cuenta? <Link to="/login">Iniciar sesión</Link>
      </p>
    </section>
  )
}
