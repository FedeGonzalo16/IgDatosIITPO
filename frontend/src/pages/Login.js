import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, AlertCircle } from 'lucide-react';
import { studentService, teacherService } from '../services/api'; 
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
      // 1. Unificamos la validación: TODO usuario entra con 123456 en desarrollo
      if (password !== '123456') {
        setError('Contraseña incorrecta. (Usa: 123456)');
        setLoading(false);
        return;
      }

      let userData = null;

      // 2. Búsqueda secuencial: Primero intentamos como Estudiante/Admin
      try {
        const response = await studentService.getByEmail(email);
        userData = response.data;
      } catch (err) {
        // Si arroja 404 (No encontrado), buscamos en la colección de Profesores
        if (err.response?.status === 404) {
          try {
            const resProf = await teacherService.getByEmail(email);
            userData = resProf.data;
          } catch (errProf) {
             console.error("Fallo buscando profesor:", errProf.response?.data || errProf);
          }
        }
      }

      if (!userData) {
        setError('Usuario no encontrado en la base de datos');
        setLoading(false);
        return;
      }

      // 3. Preparar los datos del usuario para el frontend
      if (!userData._id && !userData.id) {
        userData._id = userData._id || userData.id || `temp-${Date.now()}`;
      }

      // Asignar rol si no viene definido en el documento
      if (!userData.rol) {
        userData.rol = email.includes('admin') ? 'admin' : 'student';
      }

      // 4. Generar un token falso y guardar sesión
      const token = 'token-' + Date.now();
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      onLogin(userData, token);
      
      // 5. Redireccionamiento dinámico por rol
      if (userData.rol === 'admin') navigate('/admin');
      else if (userData.rol === 'profesor' || userData.rol === 'docente') navigate('/profesor');
      else navigate('/student');

    } catch (err) {
      console.error('Login error:', err);
      setError('Error de conexión con el servidor.');
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
              Credenciales de demostración (Clave unificada: 123456):
            </p>
            <small>
              <strong>Estudiante:</strong> fede@mail.com
              <br />
              <strong>Profesor:</strong> jorge@mail.com
              <br />
              <strong>Admin:</strong> admin@edugrade.com
            </small>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;