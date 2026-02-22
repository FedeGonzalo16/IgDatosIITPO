import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import Navbar from '../components/Navbar';
import StudentSidebar from '../components/StudentSidebar';
import {
  StudentProfile,
  StudentEnrollment,
  ChangeInstitution
} from '../components/StudentMenuContent';
import { BookOpen, CheckCircle, Target, TrendingUp } from 'lucide-react';
import { gradeService } from '../services/api';
import './StudentDashboard.css';

const StudentDashboard = ({ user, onLogout, onUserUpdate }) => {
  const [stats, setStats] = useState({
    totalSubjects: 0,
    passedSubjects: 0,
    averageGrade: 0,
    inProgress: 0
  });
  const [historial, setHistorial] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeMenu, setActiveMenu] = useState('inicio');
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    onLogout();
    navigate('/login');
  };

  useEffect(() => {
    if (location.state?.openMenu === 'perfil') {
      setActiveMenu('perfil');
    }
  }, [location.state?.openMenu]);

  useEffect(() => {
    // Intentar cargar datos cuando el componente se monta
    const loadData = async () => {
      // Si no hay user pero hay datos en localStorage, intentar cargarlos
      if (!user) {
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
          try {
            const parsedUser = JSON.parse(savedUser);
            if (parsedUser._id || parsedUser.id) {
              // Recargar datos con el usuario de localStorage
              await loadStudentData(parsedUser);
              return;
            }
          } catch (e) {
            console.error('Error parsing user from localStorage:', e);
          }
        }
        setLoading(false);
        return;
      }
      
      if (user?._id || user?.id) {
        await loadStudentData();
      } else {
        console.warn('No user ID available. User object:', user);
        setLoading(false);
      }
    };
    
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const loadStudentData = async (userData = null) => {
    setLoading(true);
    try {
      const currentUser = userData || user;
      const studentId = currentUser?._id || currentUser?.id;
      if (!studentId) {
        console.warn('No student ID found. User:', currentUser);
        setLoading(false);
        return;
      }

      console.log('Loading data for student:', studentId);

      // Cargar historial de calificaciones
      let historialData = [];
      try {
        const historialRes = await gradeService.getByStudent(studentId);
        historialData = historialRes.data || [];
        console.log('Historial loaded:', historialData);
      } catch (error) {
        console.error('Error loading historial:', error);
        // Si no hay historial, continuar con array vacío
        historialData = [];
      }
      
      setHistorial(historialData);

      // Calcular estadísticas
      const materiasEnCurso = historialData.filter(h => h.estado === 'CURSANDO' || h.estado === 'EN_CURSO' || !h.fecha_cierre);
      const materiasAprobadas = historialData.filter(h => 
        h.estado === 'APROBADO' || h.estado === 'APROBADO (EQUIVALENCIA)' || (h.estado && h.estado.toString().startsWith('APROBADO'))
      );
      const reprobadasMap = new Map();
      historialData.filter(h => h.estado === 'REPROBADO').forEach(h => {
        const key = h.materia_id || h.materia_nombre;
        reprobadasMap.set(key, h);
      });
      const materiasReprobadas = Array.from(reprobadasMap.values()).filter(
        h => !historialData.some(a => (a.materia_id || a.materia_nombre) === (h.materia_id || h.materia_nombre) && (a.estado === 'APROBADO' || (a.estado && a.estado.toString().startsWith('APROBADO'))))
      );
      
      // Calcular promedio de notas finales
      const notasFinales = historialData
        .filter(h => (h.notas?.final != null && h.notas?.final !== '') || (h.notas?.previo != null && h.notas?.previo !== ''))
        .map(h => parseFloat(h.notas?.final ?? h.notas?.previo))
        .filter(n => !isNaN(n));
      
      const promedio = notasFinales.length > 0
        ? (notasFinales.reduce((a, b) => a + b, 0) / notasFinales.length).toFixed(2)
        : 0;

      setStats({
        totalSubjects: historialData.length,
        passedSubjects: materiasAprobadas.length,
        averageGrade: promedio,
        inProgress: materiasEnCurso.length
      });
      setError(null);
    } catch (error) {
      console.error('Error loading student data:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      
      // Mostrar error al usuario
      if (error.response?.status === 404) {
        setError('No se encontraron datos. Esto es normal si es tu primera vez. Puedes inscribirte a materias.');
      } else if (error.response?.status >= 500) {
        setError('Error del servidor. Por favor, intenta más tarde.');
      } else if (error.message.includes('Network')) {
        setError('Error de conexión. Verifica que el backend esté corriendo en http://localhost:5000');
      } else {
        setError(`Error: ${error.response?.data?.error || error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUserUpdate = (updatedUser) => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        const parsed = JSON.parse(savedUser);
        const merged = { ...parsed, ...updatedUser };
        localStorage.setItem('user', JSON.stringify(merged));
        if (onUserUpdate) onUserUpdate(merged);
        loadStudentData(merged);
      } catch (e) {
        console.error('Error updating user:', e);
      }
    }
  };

  const renderContent = () => {
    if (activeMenu === 'perfil') {
      return <StudentProfile user={user} onBack={() => setActiveMenu('inicio')} stats={stats} onUpdate={handleUserUpdate} />;
    }
    if (activeMenu === 'inscribirse') {
      return <StudentEnrollment user={user} onBack={() => setActiveMenu('inicio')} onEnroll={loadStudentData} />;
    }
    if (activeMenu === 'institucion') {
      return <ChangeInstitution user={user} onBack={() => setActiveMenu('inicio')} onUpdate={handleUserUpdate} />;
    }


    const materiasEnCurso = historial.filter(h => h.estado === 'CURSANDO' || h.estado === 'EN_CURSO' || !h.fecha_cierre);
    const materiasAprobadas = historial.filter(h => 
      h.estado === 'APROBADO' || h.estado === 'APROBADO (EQUIVALENCIA)' || (h.estado && h.estado.toString().startsWith('APROBADO'))
    );
    const reprobadasMap = new Map();
    historial.filter(h => h.estado === 'REPROBADO').forEach(h => {
      const key = h.materia_id || h.materia_nombre;
      reprobadasMap.set(key, h);
    });
    const materiasReprobadas = Array.from(reprobadasMap.values()).filter(
      h => !historial.some(a => (a.materia_id || a.materia_nombre) === (h.materia_id || h.materia_nombre) && (a.estado === 'APROBADO' || (a.estado && a.estado.toString().startsWith('APROBADO'))))
    );

    return (
      <div className="dashboard-main">
        <div className="dashboard-header">
          <h1>📚 Mis Materias</h1>
          <p>Bienvenido, {user?.nombre || user?.email}</p>
        </div>

        {loading ? (
          <div className="loading-container">Cargando datos...</div>
        ) : error ? (
          <div className="error-container">
            <div className="error-message">
              <strong>⚠️ {error}</strong>
              <p>Si es tu primera vez, puedes crear materias e inscribirte desde el menú lateral.</p>
              <button 
                className="btn-enroll" 
                onClick={() => setActiveMenu('inscribirse')}
                style={{ marginTop: '15px' }}
              >
                Ir a Inscripciones
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon">
                  <BookOpen size={32} />
                </div>
                <div className="stat-content">
                  <h3>{stats.totalSubjects}</h3>
                  <p>Total de Materias</p>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">
                  <CheckCircle size={32} />
                </div>
                <div className="stat-content">
                  <h3>{stats.passedSubjects}</h3>
                  <p>Aprobadas</p>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">
                  <TrendingUp size={32} />
                </div>
                <div className="stat-content">
                  <h3>{stats.averageGrade}</h3>
                  <p>Promedio General</p>
                </div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">
                  <Target size={32} />
                </div>
                <div className="stat-content">
                  <h3>{stats.inProgress}</h3>
                  <p>En Curso</p>
                </div>
              </div>
            </div>

            {materiasEnCurso.length > 0 && (
              <div className="subjects-section">
                <h2>Materias en Curso</h2>
                <div className="subjects-grid">
                  {materiasEnCurso.map((materia, idx) => (
                    <div key={idx} className="subject-card">
                      <div className="subject-header">
                        <h3>{materia.materia_nombre || 'Materia'}</h3>
                        <span className="subject-code">{materia.materia_codigo || ''}</span>
                      </div>
                      <div className="subject-details">
                        <p><strong>Año:</strong> {materia.anio || 'N/A'}</p>
                        {materia.notas && (
                          <div className="notas-preview">
                            {materia.notas.primer_parcial && <span>P1: {materia.notas.primer_parcial}</span>}
                            {materia.notas.segundo_parcial && <span>P2: {materia.notas.segundo_parcial}</span>}
                            {materia.notas.final && <span>Final: {materia.notas.final}</span>}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {materiasAprobadas.length > 0 && (
              <div className="subjects-section">
                <h2>Materias Aprobadas</h2>
                <div className="subjects-grid">
                  {materiasAprobadas.map((materia, idx) => (
                    <div key={idx} className="subject-card approved">
                      <div className="subject-header">
                        <h3>{materia.materia_nombre || 'Materia'}</h3>
                        <span className="subject-code">{materia.materia_codigo || ''}</span>
                        {materia.es_equivalencia && <span className="equivalencia-badge" title="Aprobada por equivalencia">Equivalencia</span>}
                      </div>
                      <div className="subject-details">
                        {(materia.notas?.final != null || materia.notas?.previo != null) && (
                          <div className="grade-badge">
                            <strong>Nota Final:</strong> {materia.notas?.final ?? materia.notas?.previo}
                            {materia.es_equivalencia && materia.nota_original != null && (
                              <span> (orig: {materia.nota_original})</span>
                            )}
                          </div>
                        )}
                        {materia.es_equivalencia && materia.materia_origen_nombre && (
                          <p><small>Origen: {materia.materia_origen_nombre}</small></p>
                        )}
                        {materia.es_equivalencia && materia.metodo_conversion && (
                          <p><small>Método: {materia.metodo_conversion}</small></p>
                        )}
                        {(materia.fecha_cierre || materia.fecha_conversion) && (
                          <p><small>Fecha: {new Date(materia.fecha_conversion || materia.fecha_cierre).toLocaleDateString('es-ES')}</small></p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {materiasReprobadas.length > 0 && (
              <div className="subjects-section">
                <h2>Materias Reprobadas</h2>
                <div className="subjects-grid">
                  {materiasReprobadas.map((materia, idx) => (
                    <div key={idx} className="subject-card reprobada">
                      <div className="subject-header">
                        <h3>{materia.materia_nombre || 'Materia'}</h3>
                        <span className="subject-code">{materia.materia_codigo || ''}</span>
                      </div>
                      <div className="subject-details">
                        {materia.notas?.final && (
                          <div className="grade-badge">
                            <strong>Nota Final:</strong> {materia.notas.final}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {historial.length === 0 && !loading && (
              <div className="no-data">
                <p>No tienes materias registradas aún.</p>
                <button 
                  className="btn-enroll" 
                  onClick={() => setActiveMenu('inscribirse')}
                  style={{ marginTop: '15px' }}
                >
                  Inscribirse a Materias
                </button>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <>
      <Navbar user={user} onLogout={onLogout} />
      <div className="student-dashboard-layout">
        <StudentSidebar
          user={user}
          onLogout={handleLogout}
          onMenuSelect={setActiveMenu}
          activeMenu={activeMenu}
        />
        <main className="dashboard-content">
          {renderContent()}
        </main>
      </div>
    </>
  );
};

export default StudentDashboard;
