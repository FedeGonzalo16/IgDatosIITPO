import React from 'react';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, user, role, onLogout }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (role && user.rol !== role) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        textAlign: 'center'
      }}>
        <div>
          <h2>Acceso Denegado</h2>
          <p>No tienes permisos para acceder a esta página.</p>
        </div>
      </div>
    );
  }

  // Pasar props user y onLogout al componente hijo
  return React.cloneElement(children, { user, onLogout });
};

export default ProtectedRoute;
