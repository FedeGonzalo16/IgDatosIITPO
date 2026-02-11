import React from 'react';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, user, role, onLogout }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Verificar rol si se especifica
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

  return children;
};

export default ProtectedRoute;
