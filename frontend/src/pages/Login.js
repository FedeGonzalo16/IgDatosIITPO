import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, AlertCircle } from 'lucide-react';
import { studentService } from '../services/api';
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
      // Buscar estudiante por email
      let userData = null;
      try {
        const response = await studentService.getByEmail(email);
        if (response.data) {
          userData = response.data;
        }
      } catch (err) {
        // Si no existe, crear un nuevo estudiante
        if (err.response?.status === 404 || !err.response) {
          try {
            const createResponse = await studentService.create({
              legajo: `STU-${Date.now()}`,
              nombre: email.split('@')[0],
              apellido: 'Usuario',
              email: email,
              pais: 'AR'
            });
            userData = {
              _id: createResponse.data.id,
              nombre: email.split('@')[0],
              apellido: 'Usuario',
              email: email,
              legajo: `STU-${Date.now()}`,
              rol: email.includes('admin') ? 'admin' : 'student'
            };
          } catch (createErr) {
            console.error('Error creating student:', createErr);
            setError('Error al crear usuario. Intenta nuevamente.');
            return;
          }
        } else {
          throw err;
        }
      }

      if (!userData) {
        setError('No se pudo obtener información del usuario.');
        return;
      }

      // Asegurar que tenga _id o id
      if (!userData._id && !userData.id) {
        userData._id = userData._id || userData.id || `temp-${Date.now()}`;
      }

      // Agregar rol si no existe
      if (!userData.rol) {
        userData.rol = email.includes('admin') ? 'admin' : 'student';
      }

      const token = 'token-' + Date.now();
      onLogin(userData, token);
      navigate(userData.rol === 'admin' ? '/admin' : '/student');
    } catch (err) {
      console.error('Login error:', err);
      setError(err.response?.data?.error || 'Error de autenticación. Verifica tu email.');
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
