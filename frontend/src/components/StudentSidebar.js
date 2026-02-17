import React, { useState } from 'react';
import { User, BookOpen, Building2, Calculator, Menu, X } from 'lucide-react';
import './StudentSidebar.css';

const StudentSidebar = ({ user, onMenuSelect, activeMenu }) => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const handleMenuClick = (menu) => {
    onMenuSelect(menu);
    setIsMobileOpen(false);
  };

  const menuItems = [
    {
      id: 'perfil',
      label: 'Mi Perfil',
      icon: User,
      description: 'Ver información personal y académica'
    },
    {
      id: 'inscribirse',
      label: 'Inscribirse a Materias',
      icon: BookOpen,
      description: 'Registrarse en nuevas materias'
    },
    {
      id: 'institucion',
      label: 'Cambiar Institución',
      icon: Building2,
      description: 'Cambiar tu institución educativa'
    },
    {
      id: 'convertir',
      label: 'Convertir Notas',
      icon: Calculator,
      description: 'Convertir y comparar tus calificaciones'
    }
  ];

  return (
    <>
      {/* Botón hamburguesa para móvil */}
      <button className="sidebar-toggle" onClick={() => setIsMobileOpen(!isMobileOpen)}>
        {isMobileOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {/* Overlay para móvil */}
      {isMobileOpen && <div className="sidebar-overlay" onClick={() => setIsMobileOpen(false)} />}

      {/* Sidebar */}
      <aside className={`student-sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
        {/* Header del Sidebar */}
        <div className="sidebar-header">
          <div className="user-avatar">
            {user?.nombre?.charAt(0) || 'E'}
          </div>
          <div className="user-info">
            <p className="user-name">{user?.nombre || 'Estudiante'}</p>
            <p className="user-legajo">{user?.legajo || 'STU-2024'}</p>
          </div>
        </div>

        {/* Menu Items */}
        <nav className="sidebar-nav">
          {menuItems.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`sidebar-menu-item ${activeMenu === item.id ? 'active' : ''}`}
                onClick={() => handleMenuClick(item.id)}
                title={item.description}
              >
                <Icon size={20} />
                <span className="menu-label">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>
    </>
  );
};

export default StudentSidebar;
