import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, AlertCircle } from 'lucide-react';
import { authService, studentService } from '../services/api';
import './Auth.css';

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');       // Limpiamos errores previos
    setLoading(true);   // Activamos el botón de "Iniciando sesión..."

    try {
      // Llamar al endpoint de autenticación
      const res = await authService.login(email, password);
      const data = res.data || {};

      // Soporta dos formas de respuesta: { token, user } o { access_token, user }
      const token = data.token || data.access_token || data.accessToken;
      const userData = data.user || data.usuario || data;

      if (!token) {
        // Si el endpoint no devuelve token, intentar buscar usuario por email
        const r = await studentService.getByEmail(email);
        const fallbackUser = r.data;
        
        if (!fallbackUser) {
          setError('Usuario no encontrado');
          setLoading(false);
          return;
        }
        
        const fallbackToken = 'token-' + Date.now();
        onLogin(fallbackUser, fallbackToken);
        navigate(fallbackUser.rol === 'admin' ? '/admin' : '/student');
        return;
      }

      // Guardar en localStorage y actualizar estado
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userData));
      onLogin(userData, token);
      navigate((userData.rol || (email.includes('admin') ? 'admin' : 'student')) === 'admin' ? '/admin' : '/student');

      // SE ELIMINARON LAS LÍNEAS DUPLICADAS QUE CAUSABAN EL ERROR DE COMPILACIÓN AQUÍ

    } catch (err) {
      console.error('Login error:', err);
      
      if (err.response?.status === 401) {
        setError('Credenciales incorrectas');
      } else if (err.response?.status === 404) {
        setError('Usuario no encontrado');
      } else {
        setError(err.response?.data?.error || 'Error de conexión con el servidor.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h1>🎓 EduGrade</h1>
          <p>Sistema de Gestión Educativa</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <h2>Iniciar Sesión</h2>

          {error && (
            <div className="error-alert">
              <AlertCircle size={20} />
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">
              <Mail size={18} />
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="tu@email.com"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">
              <Lock size={18} />
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
            />
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>

          <div className="auth-footer">
            <p>¿No tienes cuenta? <Link to="/register">Regístrate aquí</Link></p>
          </div>

          <hr style={{ opacity: 0.2, margin: '20px 0' }} />

          <div className="demo-credentials">
            <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '8px' }}>
              Credenciales de demostración:
            </p>
            <small>
              <strong>Estudiante:</strong> student@example.com | 123456
              <br />
              <strong>Admin:</strong> admin@example.com | 123456
            </small>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
