import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="page">
      <h1>Página no encontrada</h1>
      <p className="page-lead">La dirección solicitada no existe.</p>
      <Link className="button" to="/">
        Volver al inicio
      </Link>
    </section>
  )
}
