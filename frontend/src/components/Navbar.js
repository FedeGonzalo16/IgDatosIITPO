import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, X, LogOut, Home, BarChart3 } from 'lucide-react';
import './Navbar.css';

const Navbar = ({ user, onLogout }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo">
          <span className="logo-icon">🎓</span>
          EduGrade
        </Link>

        <div className="menu-icon" onClick={() => setIsMenuOpen(!isMenuOpen)}>
          {isMenuOpen ? <X size={28} /> : <Menu size={28} />}
        </div>

        <ul className={isMenuOpen ? 'nav-menu active' : 'nav-menu'}>
          {user && (
            <>
              {user.rol === 'admin' ? (
                <>
                  <li className="nav-item">
                    <Link to="/admin" className="nav-links">
                      <BarChart3 size={18} />
                      Panel Admin
                    </Link>
                  </li>
                  <li className="nav-item">
                    <Link to="/admin/reportes" className="nav-links">
                      <BarChart3 size={18} />
                      Reportes
                    </Link>
                  </li>
                </>
              ) : (
                <>
                  <li className="nav-item">
                    <Link to="/student" className="nav-links">
                      <Home size={18} />
                      Mis Materias
                    </Link>
                  </li>
                  <li className="nav-item">
                    <Link to="/student/subjects" className="nav-links">
                      <BarChart3 size={18} />
                      Mi Perfil
                    </Link>
                  </li>
                </>
              )}

              <li className="nav-item user-info">
                <span className="user-name">{user.nombre || user.email}</span>
              </li>

              <li className="nav-item">
                <button onClick={handleLogout} className="logout-btn">
                  <LogOut size={18} />
                  Cerrar Sesión
                </button>
              </li>
            </>
          )}
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
