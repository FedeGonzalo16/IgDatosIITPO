import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { User, Mail, Lock, AlertCircle } from 'lucide-react';
import './Auth.css';
import { authService, studentService } from '../services/api';

const Register = ({ onLogin }) => {
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    email: '',
    password: '',
    confirmPassword: '',
    legajo: '',
    documento: '',
    fecha_nacimiento: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validaciones
    if (formData.password !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden');
      return;
    }

    if (formData.password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres');
      return;
    }

    setLoading(true);

    try {
      // Preferir endpoint de autenticación si existe
      const payload = {
        nombre: formData.nombre,
        apellido: formData.apellido,
        email: formData.email,
        password: formData.password,
        legajo: formData.legajo,
        documento: formData.documento,
        fecha_nacimiento: formData.fecha_nacimiento
      };

      let res;
      try {
        res = await authService.register(payload);
      } catch (e) {
        // Fallback: si no hay endpoint de auth/register, crear estudiante y pedir login
        await studentService.create(payload);
        alert('Registro exitoso. Por favor inicia sesión.');
        navigate('/login');
        setLoading(false);
        return;
      }

      // Si el register devuelve token y usuario, iniciar sesión automáticamente
      const data = res.data || {};
      const token = data.token || data.access_token || data.accessToken;
      const userData = data.user || data.usuario || data;

      if (token) {
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(userData));
        if (onLogin) onLogin(userData, token);
        navigate(userData.rol === 'admin' ? '/admin' : '/student');
      } else {
        alert('Registro exitoso. Por favor inicia sesión.');
        navigate('/login');
      }
    } catch (err) {
      console.error('Register error:', err);
      setError(err.response?.data?.error || 'Error al registrar. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card auth-card-large">
        <div className="auth-header">
          <h1>🎓 EduGrade</h1>
          <p>Crear Nueva Cuenta</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <h2>Registro de Estudiante</h2>

          {error && (
            <div className="error-alert">
              <AlertCircle size={20} />
              {error}
            </div>
          )}

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="nombre">
                <User size={18} />
                Nombre
              </label>
              <input
                id="nombre"
                type="text"
                name="nombre"
                value={formData.nombre}
                onChange={handleChange}
                placeholder="Tu nombre"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="apellido">Apellido</label>
              <input
                id="apellido"
                type="text"
                name="apellido"
                value={formData.apellido}
                onChange={handleChange}
                placeholder="Tu apellido"
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="email">
              <Mail size={18} />
              Email
            </label>
            <input
              id="email"
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="tu@email.com"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="documento">Documento (DNI)</label>
            <input
              id="documento"
              type="text"
              name="documento"
              value={formData.documento}
              onChange={handleChange}
              placeholder="12345678"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="legajo">Legajo</label>
            <input
              id="legajo"
              type="text"
              name="legajo"
              value={formData.legajo}
              onChange={handleChange}
              placeholder="STU20241001"
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="fecha_nacimiento">Fecha de Nacimiento</label>
            <input
              id="fecha_nacimiento"
              type="date"
              name="fecha_nacimiento"
              value={formData.fecha_nacimiento}
              onChange={handleChange}
              required
              disabled={loading}
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="password">
                <Lock size={18} />
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirmar</label>
              <input
                id="confirmPassword"
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="••••••••"
                required
                disabled={loading}
              />
            </div>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Registrando...' : 'Crear Cuenta'}
          </button>

          <div className="auth-footer">
            <p>¿Ya tienes cuenta? <Link to="/login">Inicia sesión aquí</Link></p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Register;
