import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Páginas
import Login from './pages/Login';
import Register from './pages/Register';
import StudentDashboard from './pages/StudentDashboard';
import AdminDashboard from './pages/AdminDashboard';
import StudentProfile from './pages/StudentProfile';
import ReportesPage from './pages/ReportesPage';

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
          element={!user ? <Register /> : <Navigate to="/" />} 
        />

        {/* Rutas protegidas */}
        <Route
          path="/student"
          element={
            <ProtectedRoute user={user} onLogout={handleLogout}>
              <StudentDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/student/subjects"
          element={
            <ProtectedRoute user={user} onLogout={handleLogout}>
              <StudentProfile />
            </ProtectedRoute>
          }
        />
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

        {/* Ruta raíz: login como primera pantalla si no hay usuario */}
        <Route 
          path="/" 
          element={user ? (
            user.rol === 'admin' ? <Navigate to="/admin" /> : <Navigate to="/student" />
          ) : (
            <Login onLogin={handleLogin} />
          )} 
        />
      </Routes>
    </Router>
  );
}

export default App;
