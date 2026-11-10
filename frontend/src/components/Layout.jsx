import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import { ROUTES } from '../routes.js'
import './Layout.css'

export default function Layout() {
  const { status } = useAuth()

  return (
    <div className="layout">
      <header className="layout__header">
        <Link to={ROUTES.home} className="layout__logo">
          SmartRecipe
        </Link>

        {status === 'authenticated' && (
          <nav className="layout__nav">
            <NavLink to={ROUTES.profile}>Профіль</NavLink>
          </nav>
        )}
      </header>

      <main className="layout__main">
        <Outlet />
      </main>
    </div>
  )
}
