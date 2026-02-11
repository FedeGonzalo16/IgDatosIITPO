import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, AlertCircle } from 'lucide-react';
import './Auth.css';

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // Simulamos la autenticación - en producción usarías el servicio API
      // const response = await authService.login(email, password);
      
      // Por ahora, vamos a simular un login exitoso
      // Nota: Necesitas implementar un endpoint de autenticación en tu backend
      
      const mockUser = {
        id: '1',
        nombre: 'Estudiante',
        email: email,
        rol: email.includes('admin') ? 'admin' : 'student',
        legajo: 'STU20241001'
      };

      const mockToken = 'mock-token-' + Date.now();

      onLogin(mockUser, mockToken);
      navigate(email.includes('admin') ? '/admin' : '/student');
    } catch (err) {
      setError('Error de autenticación. Verifica tu email y contraseña.');
      console.error('Login error:', err);
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
