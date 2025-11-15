import { NavLink, Outlet } from 'react-router-dom'

import '../App.css'

const navItems = [
  { to: '/search', label: 'Submit Search' },
  { to: '/results', label: 'Job Queue' },
  { to: '/tutorial', label: 'Tutorial' },
]

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-dot" />
          <div>
            <p className="brand-label">Dara Local v2</p>
            <h1>Streamlined Phase Analysis</h1>
          </div>
        </div>
        <nav className="main-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }: { isActive: boolean }) =>
                isActive ? 'nav-link active' : 'nav-link'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}

export default AppLayout
