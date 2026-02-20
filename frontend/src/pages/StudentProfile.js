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
  const [institutions, setInstitutions] = useState([]);
  const [selectedInstitution, setSelectedInstitution] = useState('');
  const [conversionRule, setConversionRule] = useState('AR_TO_US');
  const [localUser, setLocalUser] = useState(user || {});
  const [institutions, setInstitutions] = useState([]);
  const [selectedInstitution, setSelectedInstitution] = useState('');
  const [conversionRule, setConversionRule] = useState('AR_TO_US');
  const [localUser, setLocalUser] = useState(user || {});
  const [loading, setLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDescargarAnalitico = async () => {
    const studentId = user?._id || user?.id || user?.id_mongo || user?.mongo_id;
    await descargarCertificadoAnalitico(reportService, studentId, user, setReportLoading);
  };

  const downloadReport = () => {
    const reportContent = `REPORTE ACADÉMICO - ${user?.nombre || 'Estudiante'}\nLegajo: ${user?.legajo || 'N/A'}\nFecha: ${new Date().toLocaleDateString('es-ES')}\n\n` +
      subjects.map(s => `${s.nombre} (${s.codigo}) - Estado: ${s.estado || 'N/A'} - Nota Final: ${s.nota || 'En curso'}\n`).join('') +
      `\nEste reporte fue generado automáticamente desde el Sistema EduGrade.`;

    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(reportContent));
    element.setAttribute('download', `reporte_academico_${user?.legajo || 'estudiante'}.txt`);
    // Sincronizar prop `user` con copy local
    setLocalUser(user || {});

    // Cargar lista de instituciones para el selector
    const loadInstitutions = async () => {
      try {
        const res = await institutionService.getAll();
        setInstitutions(res.data || []);
      } catch (e) {
        console.warn('No se pudieron cargar instituciones:', e);
      }
    };
    loadInstitutions();

    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    // Sincronizar prop `user` con copy local
    setLocalUser(user || {});

    // Cargar lista de instituciones para el selector
    const loadInstitutions = async () => {
      try {
        const res = await institutionService.getAll();
        setInstitutions(res.data || []);
      } catch (e) {
        console.warn('No se pudieron cargar instituciones:', e);
      }
    };
    loadInstitutions();

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

          // Determinar la nota final a mostrar (incluye equivalencias)
          let notaFinal = null;
          if (s.notas?.final !== null && s.notas?.final !== undefined) notaFinal = s.notas.final;
          else if (s.notas?.previo !== null && s.notas?.previo !== undefined) notaFinal = s.notas.previo;
          else if ((s.estado && s.estado.toString().startsWith('APROBADO')) || s.estado === 'REPROBADO') notaFinal = s.notas?.final || s.notas?.previo;

        // Set selectedInstitution to current if existe
        setSelectedInstitution(user?.institucion_id || user?.institucion || '');
        
          return {
            materia_id: s.materia_id,
            id: idx,
            codigo: s.materia_codigo || 'N/A',
            nombre: s.materia_nombre || 'Materia Desconocida',
            estado: s.estado || 'CURSANDO',
            nota: notaFinal,
            es_equivalencia: s.es_equivalencia || (s.estado && s.estado.toString().includes('EQUIVALENCIA')),
            nota_original: s.nota_original,
            materia_origen_nombre: s.materia_origen_nombre,
  const handleChangeInstitution = async () => {
    const studentId = user?._id || user?.id || user?.id_mongo || user?.mongo_id;
    if (!selectedInstitution) return alert('Seleccione una institución destino.');
    try {
      const result = await studentService.cambiarInstitucion(studentId, selectedInstitution, conversionRule);
      const res = await studentService.getById(studentId);
      const updatedUser = { ...user, ...res.data, institucion_id: selectedInstitution };
      const inst = (institutions || []).find(i => String(i._id) === String(selectedInstitution));
      if (inst) updatedUser.institucion = inst.nombre;
      setLocalUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
      if (onUserUpdate) onUserUpdate(updatedUser);
      const homologadas = result.data?.total_homologadas ?? result.data?.materias_homologadas?.length ?? 0;
      alert(homologadas > 0
        ? `Institución cambiada. ${homologadas} materia(s) aprobada(s) por equivalencia.`
        : 'Institución cambiada correctamente');
    } catch (err) {
      console.error('Error al cambiar institución:', err);
      alert('Error al cambiar institución: ' + (err.response?.data?.error || err.message));
    }
  };

            metodo_conversion: s.metodo_conversion,
            fecha_conversion: s.fecha_conversion,
            componentes: comps,
            profesor: 'Sin asignar',
            horas_semanales: 4,
            anio: s.anio || "Sin fecha",
            fecha_cierre: s.fecha_cierre || null 
          };
        // Set selectedInstitution to current if existe
        setSelectedInstitution(user?.institucion_id || user?.institucion || '');
        
        });

        setSubjects(mapped);
      } catch (err) {
        console.error('Error cargando datos del estudiante:', err);
        setError('No se pudieron cargar los datos académicos.');
      } finally {
        setLoading(false);
      }
    };
  const handleChangeInstitution = async () => {
    const studentId = user?._id || user?.id || user?.id_mongo || user?.mongo_id;
    if (!selectedInstitution) return alert('Seleccione una institución destino.');
    try {
      const result = await studentService.cambiarInstitucion(studentId, selectedInstitution, conversionRule);
      const res = await studentService.getById(studentId);
      const updatedUser = { ...user, ...res.data, institucion_id: selectedInstitution };
      const inst = (institutions || []).find(i => String(i._id) === String(selectedInstitution));
      if (inst) updatedUser.institucion = inst.nombre;
      setLocalUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
      if (onUserUpdate) onUserUpdate(updatedUser);
      const homologadas = result.data?.total_homologadas ?? result.data?.materias_homologadas?.length ?? 0;
      alert(homologadas > 0
        ? `Institución cambiada. ${homologadas} materia(s) aprobada(s) por equivalencia.`
        : 'Institución cambiada correctamente');
    } catch (err) {
      console.error('Error al cambiar institución:', err);
      alert('Error al cambiar institución: ' + (err.response?.data?.error || err.message));
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
                <p><strong>Institución:</strong> {user?.institucion_nombre || user?.institucion || 'Sin asignar'}</p>
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
                    <span className={`status-label ${subject.es_equivalencia ? 'aprobado-equivalencia' : (subject.estado || 'desconocido').toLowerCase().replace(/\s+/g, '-').replace(/[()]/g, '')}`}>
                      {subject.es_equivalencia ? 'APROBADO (EQUIVALENCIA)' : (subject.estado || 'Desconocido').toUpperCase()}
                    </span>
                    {subject.es_equivalencia && subject.nota_original != null && (
                      <span className="equivalencia-original" title="Nota original antes de conversión">Orig: {subject.nota_original}</span>
                    )}
                    {subject.es_equivalencia && subject.materia_origen_nombre && (
                      <span className="equivalencia-origen" title="Materia de origen">← {subject.materia_origen_nombre}</span>
                    )}
                    {subject.es_equivalencia && subject.metodo_conversion && (
                      <span className="equivalencia-metodo" title="Método de conversión">Regla: {subject.metodo_conversion}</span>
                    )}
                    {subject.es_equivalencia && subject.fecha_conversion && (
                      <span className="equivalencia-fecha" title="Fecha de conversión">
                        {new Date(subject.fecha_conversion).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </span>
                    )}
                    {subject.nota != null && <span className="grade-label">Nota: {subject.nota}</span>}
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
              {(() => {
                const normalize = (str) => (str || '').toString().toUpperCase().normalize('NFD').replace(/\p{Diacritic}/gu, '').replace(/\s+/g, '_');

                const total = subjects.length;
                const approvedCount = subjects.filter(s => normalize(s.estado).includes('APROB')).length;
                const inProgressCount = subjects.filter(s => {
                  const ns = normalize(s.estado);
                  return ns.includes('CURS') || ns.includes('EN_CURSO') || ns.includes('CURSANDO') || ns.includes('ENCURSO');
                }).length;
                const gradeNumbers = subjects.map(s => parseFloat(s.nota)).filter(n => !isNaN(n));
                const average = gradeNumbers.length ? (gradeNumbers.reduce((a, b) => a + b, 0) / gradeNumbers.length) : null;
                const finishedCount = Math.max(0, total - inProgressCount);
                const approvalRate = finishedCount > 0 ? (approvedCount / finishedCount) * 100 : 0;

                return (
                  <>
                    <div className="stat-box">
                      <BarChart3 size={28} />
                      <h4>Promedio General</h4>
                      <p className="stat-value">{average !== null ? average.toFixed(2) : 'N/A'}</p>
                    </div>
                    <div className="stat-box">
                      <BarChart3 size={28} />
                      <h4>Materias Aprobadas</h4>
                      <p className="stat-value">{approvedCount}</p>
                    </div>
                    <div className="stat-box">
                      <BarChart3 size={28} />
                      <h4>En Curso</h4>
                      <p className="stat-value">{inProgressCount}</p>
                    </div>
                    <div className="stat-box">
                      <BarChart3 size={28} />
                      <h4>Tasa de Aprobación</h4>
                      <p className="stat-value">{finishedCount > 0 ? `${approvalRate.toFixed(1)}%` : 'N/A'}</p>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default StudentProfile;