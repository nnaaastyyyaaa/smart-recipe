import '@fontsource-variable/nunito'
import { Outlet } from 'react-router-dom'
import Header from './header/Header.jsx'
import './Layout.css'

export default function Layout() {
  return (
    <div className="layout">
      <Header />

      <main className="layout__main">
        <Outlet />
      </main>
    </div>
  )
}
