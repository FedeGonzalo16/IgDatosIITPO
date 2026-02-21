import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Páginas
import Login from './pages/Login';
import Register from './pages/Register';
import StudentDashboard from './pages/StudentDashboard';
import AdminDashboard from './pages/AdminDashboard';
import ReportesPage from './pages/ReportesPage';
import ProfessorDashboard from './pages/ProfessorDashboard';

// Componentes
import ProtectedRoute from './components/ProtectedRoute';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restaurar usuario desde localStorage
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    
    if (savedUser && token) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (error) {
        console.error('Error restaurando usuario:', error);
        localStorage.removeItem('user');
        localStorage.removeItem('token');
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (userData, token) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    localStorage.setItem('token', token);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
  };

  if (loading) {
    return <div className="loading-spinner">Cargando...</div>;
  }

  return (
    <Router>
      <Routes>
        {/* Rutas públicas */}
        <Route 
          path="/login" 
          element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/" />} 
        />
        <Route 
          path="/register" 
          element={!user ? <Register onLogin={handleLogin} /> : <Navigate to="/" />} 
        />

        {/* Rutas protegidas Estudiante */}
        <Route
          path="/student"
          element={
            <ProtectedRoute user={user} onLogout={handleLogout} onUserUpdate={(u) => setUser(u)}>
              <StudentDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/student/subjects"
          element={<Navigate to="/student" state={{ openMenu: 'perfil' }} replace />}
        />

        {/* Rutas protegidas Administrador */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute user={user} role="admin" onLogout={handleLogout}>
              <AdminDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/reportes"
          element={
            <ProtectedRoute user={user} role="admin" onLogout={handleLogout}>
              <ReportesPage user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />

        {/* NUEVA: Rutas protegidas Profesor */}
        <Route
          path="/profesor"
          element={
            // Aquí validamos que el rol sea 'profesor' o 'docente' según lo tengas en BD
            <ProtectedRoute user={user} role={user?.rol} onLogout={handleLogout}>
              <ProfessorDashboard user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        />

        {/* Ruta raíz: login como primera pantalla si no hay usuario o redirección por rol */}
        <Route 
          path="/" 
          element={user ? (
            user.rol === 'admin' ? <Navigate to="/admin" /> : 
            (user.rol === 'profesor' || user.rol === 'docente') ? <Navigate to="/profesor" /> : 
            <Navigate to="/student" />
          ) : (
            <Login onLogin={handleLogin} />
          )} 
        />
      </Routes>
    </Router>
  );
}

export default App;