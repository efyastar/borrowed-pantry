import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useUser } from './UserContext';
import './Layout.css';

const NAV_ITEMS = [
  { to: '/stores', label: 'Stores' },
  { to: '/cook', label: 'Cook Something' },
  { to: '/chat', label: 'Chat' },
  { to: '/history', label: 'History' },
];

function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, logout } = useUser();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    navigate('/login');
  };

  return (
    <div className="layout">
      <header className="topbar">
        <button className="menu-button" onClick={() => setMenuOpen(true)} aria-label="Open menu">
          <span></span>
          <span></span>
          <span></span>
        </button>
        <span className="topbar-title">The Borrowed Pantry</span>
      </header>

      {menuOpen && <div className="drawer-backdrop" onClick={() => setMenuOpen(false)} />}

      <nav className={menuOpen ? 'drawer drawer-open' : 'drawer'}>
        <div className="drawer-header">
          <span className="drawer-title">Menu</span>
          <button className="drawer-close" onClick={() => setMenuOpen(false)} aria-label="Close menu">
            &times;
          </button>
        </div>
        {user && <p className="drawer-user">Signed in as {user.name || user.email}</p>}
        <div className="drawer-links">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => isActive ? 'drawer-link drawer-link-active' : 'drawer-link'}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
        <button className="drawer-logout" onClick={handleLogout}>Log out</button>
      </nav>

      <main className="layout-content">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;