import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import {
  reportService,
  studentService,
  institutionService,
} from '../services/api';
import {
  FileText,
  User,
  Shield,
  Building2,
  BarChart3,
  ArrowLeft,
  Loader2,
} from 'lucide-react';
import './ReportesPage.css';

const ReportesPage = ({ user, onLogout }) => {
  const [students, setStudents] = useState([]);
  const [institutions, setInstitutions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);

  // Reporte estudiante
  const [reportEstId, setReportEstId] = useState('');
  const [reportEstResult, setReportEstResult] = useState(null);
  const [reportEstLoading, setReportEstLoading] = useState(false);

  // Auditoría
  const [auditEstId, setAuditEstId] = useState('');
  const [auditResult, setAuditResult] = useState(null);
  const [auditLoading, setAuditLoading] = useState(false);

  // Reporte institución
  const [reportInstId, setReportInstId] = useState('');
  const [reportInstResult, setReportInstResult] = useState(null);
  const [reportInstLoading, setReportInstLoading] = useState(false);

  // Estadísticas globales
  const [statsApproval, setStatsApproval] = useState(null);
  const [statsGrades, setStatsGrades] = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoadingData(true);
      try {
        const [st, inst] = await Promise.all([
          studentService.getAll().then((r) => r.data || []).catch(() => []),
          institutionService.getAll().then((r) => r.data || []).catch(() => []),
        ]);
        setStudents(Array.isArray(st) ? st : []);
        setInstitutions(Array.isArray(inst) ? inst : []);
        const [approval, grades] = await Promise.all([
          reportService.getApprovalStats().then((r) => r.data).catch(() => null),
          reportService.getGradeStats().then((r) => r.data).catch(() => null),
        ]);
        setStatsApproval(approval);
        setStatsGrades(grades);
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingData(false);
      }
    };
    load();
  }, []);

  const handleReporteEstudiante = async () => {
    if (!reportEstId) {
      alert('Selecciona un estudiante.');
      return;
    }
    setReportEstLoading(true);
    setReportEstResult(null);
    try {
      const res = await reportService.getStudentReport(reportEstId);
      setReportEstResult(res.data);
    } catch (err) {
      setReportEstResult({ error: err.response?.data?.error || err.message });
    } finally {
      setReportEstLoading(false);
    }
  };

  const handleAuditoria = async () => {
    if (!auditEstId) {
      alert('Selecciona un estudiante.');
      return;
    }
    setAuditLoading(true);
    setAuditResult(null);
    try {
      const res = await reportService.getAuditoria(auditEstId);
      setAuditResult(res.data);
    } catch (err) {
      setAuditResult({ error: err.response?.data?.error || err.message });
    } finally {
      setAuditLoading(false);
    }
  };

  const handleReporteInstitucion = async () => {
    if (!reportInstId) {
      alert('Selecciona una institución.');
      return;
    }
    setReportInstLoading(true);
    setReportInstResult(null);
    try {
      const res = await reportService.getInstitutionReport(reportInstId);
      setReportInstResult(res.data);
    } catch (err) {
      setReportInstResult({ error: err.response?.data?.error || err.message });
    } finally {
      setReportInstLoading(false);
    }
  };

  if (user?.rol !== 'admin') {
    return (
      <div className="reportes-forbidden">
        <Navbar user={user} onLogout={onLogout} />
        <p>Acceso restringido a administradores.</p>
        <Link to="/">Volver</Link>
      </div>
    );
  }

  return (
    <>
      <Navbar user={user} onLogout={onLogout} />
      <div className="reportes-page">
        <div className="reportes-container">
          <header className="reportes-header">
            <Link to="/admin" className="reportes-back">
              <ArrowLeft size={20} /> Panel Admin
            </Link>
            <h1><FileText size={28} /> Reportes</h1>
            <p>Certificado analítico, reportes por estudiante e institución, auditoría y estadísticas globales.</p>
          </header>

          {loadingData ? (
            <div className="reportes-loading"><Loader2 size={32} className="spin" /> Cargando datos...</div>
          ) : (
            <>
              {/* Reporte completo estudiante */}
              <section className="reportes-section">
                <h2><User size={22} /> Reporte completo por estudiante</h2>
                <p className="section-desc">Datos del estudiante, calificaciones y estadísticas (materias en curso, aprobadas, reprobadas, promedio).</p>
                <div className="reportes-form">
                  <select value={reportEstId} onChange={(e) => setReportEstId(e.target.value)}>
                    <option value="">Seleccionar estudiante</option>
                    {students.map((s) => (
                      <option key={s._id} value={s._id}>{s.nombre} {s.apellido}</option>
                    ))}
                  </select>
                  <button type="button" onClick={handleReporteEstudiante} disabled={reportEstLoading}>
                    {reportEstLoading ? <Loader2 size={18} className="spin" /> : 'Obtener reporte'}
                  </button>
                </div>
                {reportEstResult && (
                  <div className="reportes-result">
                    {reportEstResult.error ? (
                      <p className="result-error">{reportEstResult.error}</p>
                    ) : (
                      <>
                        <div className="report-est-stats">
                          {reportEstResult.estadisticas && (
                            <>
                              <span>En curso: <strong>{reportEstResult.estadisticas.materias_en_curso}</strong></span>
                              <span>Aprobadas: <strong className="success">{reportEstResult.estadisticas.materias_aprobadas}</strong></span>
                              <span>Reprobadas: <strong className="danger">{reportEstResult.estadisticas.materias_reprobadas}</strong></span>
                              <span>Promedio: <strong>{Number(reportEstResult.estadisticas.promedio_general).toFixed(2)}</strong></span>
                            </>
                          )}
                        </div>
                        <details className="certificado-raw">
                          <summary>Ver reporte completo</summary>
                          <pre>{JSON.stringify(reportEstResult, null, 2)}</pre>
                        </details>
                      </>
                    )}
                  </div>
                )}
              </section>

              {/* Auditoría */}
              <section className="reportes-section">
                <h2><Shield size={22} /> Auditoría por estudiante</h2>
                <p className="section-desc">Historial de auditoría del estudiante.</p>
                <div className="reportes-form">
                  <select value={auditEstId} onChange={(e) => setAuditEstId(e.target.value)}>
                    <option value="">Seleccionar estudiante</option>
                    {students.map((s) => (
                      <option key={s._id} value={s._id}>{s.nombre} {s.apellido}</option>
                    ))}
                  </select>
                  <button type="button" onClick={handleAuditoria} disabled={auditLoading}>
                    {auditLoading ? <Loader2 size={18} className="spin" /> : 'Ver auditoría'}
                  </button>
                </div>
                {auditResult && (
                  <div className="reportes-result">
                    {auditResult.error ? (
                      <p className="result-error">{auditResult.error}</p>
                    ) : (
                      <pre className="audit-pre">{JSON.stringify(auditResult, null, 2)}</pre>
                    )}
                  </div>
                )}
              </section>

              {/* Reporte institución */}
              <section className="reportes-section">
                <h2><Building2 size={22} /> Reporte por institución</h2>
                <p className="section-desc">Datos de la institución, materias y estadísticas.</p>
                <div className="reportes-form">
                  <select value={reportInstId} onChange={(e) => setReportInstId(e.target.value)}>
                    <option value="">Seleccionar institución</option>
                    {institutions.map((i) => (
                      <option key={i._id} value={i._id}>{i.nombre}</option>
                    ))}
                  </select>
                  <button type="button" onClick={handleReporteInstitucion} disabled={reportInstLoading}>
                    {reportInstLoading ? <Loader2 size={18} className="spin" /> : 'Obtener reporte'}
                  </button>
                </div>
                {reportInstResult && (
                  <div className="reportes-result">
                    {reportInstResult.error ? (
                      <p className="result-error">{reportInstResult.error}</p>
                    ) : (
                      <>
                        {reportInstResult.estadisticas && (
                          <div className="report-est-stats">
                            <span>Total materias: <strong>{reportInstResult.estadisticas.total_materias}</strong></span>
                            <span>Estudiantes vinculados: <strong>{reportInstResult.estadisticas.total_estudiantes}</strong></span>
                          </div>
                        )}
                        <details className="certificado-raw">
                          <summary>Ver reporte completo</summary>
                          <pre>{JSON.stringify(reportInstResult, null, 2)}</pre>
                        </details>
                      </>
                    )}
                  </div>
                )}
              </section>

              {/* Estadísticas globales */}
              <section className="reportes-section reportes-stats">
                <h2><BarChart3 size={22} /> Estadísticas globales</h2>
                <div className="stats-grid">
                  {statsApproval && (
                    <div className="stats-card">
                      <h3>Aprobación</h3>
                      <div className="stat-item"><span>Tasa aprobación</span><strong>{Number(statsApproval.tasa_aprobacion || 0).toFixed(2)}%</strong></div>
                      <div className="stat-item"><span>Aprobadas</span><strong className="success">{statsApproval.aprobadas ?? 0}</strong></div>
                      <div className="stat-item"><span>Reprobadas</span><strong className="danger">{statsApproval.reprobadas ?? 0}</strong></div>
                      <div className="stat-item"><span>Total cursadas</span><strong>{statsApproval.total_cursadas ?? 0}</strong></div>
                    </div>
                  )}
                  {statsGrades && (
                    <div className="stats-card">
                      <h3>Calificaciones</h3>
                      <div className="stat-item"><span>Promedio</span><strong>{Number(statsGrades.promedio || 0).toFixed(2)}</strong></div>
                      <div className="stat-item"><span>Mínima</span><strong>{statsGrades.minima ?? 0}</strong></div>
                      <div className="stat-item"><span>Máxima</span><strong>{statsGrades.maxima ?? 0}</strong></div>
                      <div className="stat-item"><span>Total</span><strong>{statsGrades.total ?? 0}</strong></div>
                    </div>
                  )}
                  {!statsApproval && !statsGrades && !loadingData && (
                    <p className="no-stats">No hay estadísticas disponibles.</p>
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </>
  );
};

export default ReportesPage;
