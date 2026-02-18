import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import { ArrowLeft, Download, BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { reportService } from '../services/api';
import { descargarCertificadoAnalitico } from '../utils/certificadoAnalitico';
import './StudentProfile.css';
import { gradeService } from '../services/api';

const StudentProfile = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const downloadReport = () => {
    const reportContent = `REPORTE ACADÉMICO - ${user?.nombre || 'Estudiante'}\nLegajo: ${user?.legajo || 'N/A'}\nFecha: ${new Date().toLocaleDateString('es-ES')}\n\n` +
      subjects.map(s => `${s.nombre} (${s.codigo}) - Estado: ${s.estado || 'N/A'} - Nota Final: ${s.nota || 'En curso'}\n`).join('') +
      `\nEste reporte fue generado automáticamente desde el Sistema EduGrade.`;

    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(reportContent));
    element.setAttribute('download', `reporte_academico_${user?.legajo || 'estudiante'}.txt`);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  useEffect(() => {
    const loadData = async () => {
      if (!user) return;
      setLoading(true);
      setError('');
      try {
        const studentId = user._id || user.id || user.id_mongo || user.mongo_id;

        // Utilizamos el endpoint de historial 
        const gradesRes = await gradeService.getByStudent(studentId);
        const subjList = gradesRes.data || [];

        // Mapear materias según la nueva estructura del backend
        const mapped = subjList.map((s, idx) => {
          
          // Construir array de componentes leyendo del diccionario "notas"
          const comps = [];
          if (s.notas) {
            if (s.notas.primer_parcial !== null) comps.push({ tipo: 'Primer Parcial', valor: s.notas.primer_parcial });
            if (s.notas.segundo_parcial !== null) comps.push({ tipo: 'Segundo Parcial', valor: s.notas.segundo_parcial });
            if (s.notas.final !== null) comps.push({ tipo: 'Final', valor: s.notas.final });
            if (s.notas.previo !== null) comps.push({ tipo: 'Previo', valor: s.notas.previo });
          }

          // Determinar la nota final a mostrar
          let notaFinal = null;
          if (s.notas?.final !== null) notaFinal = s.notas.final;
          else if (s.notas?.previo !== null) notaFinal = s.notas.previo;
          else if (s.estado === 'APROBADO' || s.estado === 'REPROBADO') notaFinal = s.notas?.final || s.notas?.previo;

          return {
            materia_id: s.materia_id,
            id: idx,
            codigo: s.materia_codigo || 'N/A',
            nombre: s.materia_nombre || 'Materia Desconocida',
            estado: s.estado || 'CURSANDO',
            nota: notaFinal,
            componentes: comps,
            profesor: 'Sin asignar',
            horas_semanales: 4,
            anio: s.anio || "Sin fecha",
            fecha_cierre: s.fecha_cierre || null 
          };
        });

        setSubjects(mapped);
        
      } catch (err) {
        console.error('Error cargando datos del estudiante:', err);
        setError('No se pudieron cargar los datos académicos.');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [user]);

  return (
    <>
      <Navbar user={user} onLogout={onLogout} />
      <div className="student-profile">
        <div className="container">
          <button className="back-button" onClick={() => navigate('/student')}>
            <ArrowLeft size={20} />
            Volver
          </button>

          {/* Perfil Header */}
          <div className="profile-header">
            <div className="profile-info">
              <div className="avatar">
                {user?.nombre?.charAt(0) || 'E'}
              </div>
              <div className="profile-details">
                <h1>{user?.nombre || 'Estudiante'}</h1>
                <p>Legajo: {user?.legajo || 'Sin Legajo'}</p>
                <p>Email: {user?.email}</p>
              </div>
            </div>
            <button className="btn-download" onClick={handleDescargarAnalitico} disabled={reportLoading}>
              <Download size={20} />
              {reportLoading ? 'Generando...' : 'Descargar analítico'}
            </button>
          </div>

          {/* Materias Detalladas */}
          <div className="detailed-section">
            <h2>📚 Historial Académico Detallado</h2>
            
            {loading && <p>Cargando materias...</p>}
            {error && <p className="error-text">{error}</p>}
            
            {!loading && !error && subjects.length === 0 && (
              <p>No se encontraron materias registradas para este estudiante.</p>
            )}

            {!loading && subjects.map(subject => (
              <div key={subject.id} className="subject-detail-card">
                <div className="subject-detail-header">
                  <div>
                    <h3>{subject.nombre}</h3>
                    <p className="code-label">{subject.codigo}</p>
                  </div>
                  <div className="subject-meta">
                    <span className={`status-label ${(subject.estado || 'desconocido').toLowerCase()}`}>
                      {(subject.estado || 'Desconocido').toUpperCase()}
                    </span>
                    {subject.nota && <span className="grade-label">Nota: {subject.nota}</span>}
                  </div>
                </div>

                <div className="subject-detail-body">
                  <div className="info-row">
                    <span><strong>Profesor:</strong> {subject.profesor}</span>
                    {/* AQUI SE IMPLEMENTAN LOS CAMBIOS VISUALES DE LAS FECHAS */}
                    <span><strong>Desde:</strong> {subject.anio}</span>
                    <span><strong>Hasta:</strong> {subject.fecha_cierre ? new Date(subject.fecha_cierre).toLocaleDateString('es-ES') : '-'}</span>
                  </div>

                  {subject.componentes && subject.componentes.length > 0 && (
                    <div className="components-section">
                      <h4>Calificaciones por Componente:</h4>
                      <div className="components-grid">
                        {subject.componentes.map((comp, idx) => (
                          <div key={idx} className="component-card">
                            <div className="component-type">{comp.tipo}</div>
                            <div className="component-grade">{comp.valor}</div>
                            <div className="component-weight">-</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Estadísticas */}
          <div className="stats-section">
            <h2>📊 Estadísticas Académicas</h2>
            <div className="stats-cards">
              <div className="stat-box">
                <BarChart3 size={28} />
                <h4>Promedio General</h4>
                <p className="stat-value">8.33</p>
              </div>
              <div className="stat-box">
                <BarChart3 size={28} />
                <h4>Materias Aprobadas</h4>
                <p className="stat-value">{subjects.filter(s => s.estado?.toUpperCase() === 'APROBADO' || s.estado?.toUpperCase() === 'CURSÓ').length}</p>
              </div>
              <div className="stat-box">
                <BarChart3 size={28} />
                <h4>En Curso</h4>
                <p className="stat-value">{subjects.filter(s => s.estado?.toUpperCase() === 'EN_CURSO' || s.estado?.toUpperCase() === 'CURSANDO').length}</p>
              </div>
              <div className="stat-box">
                <BarChart3 size={28} />
                <h4>Tasa de Aprobación</h4>
                <p className="stat-value">100%</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default StudentProfile;