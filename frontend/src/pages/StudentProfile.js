import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import { ArrowLeft, Download, BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { reportService } from '../services/api';
import { descargarCertificadoAnalitico } from '../utils/certificadoAnalitico';
import './StudentProfile.css';

const StudentProfile = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [reportLoading, setReportLoading] = useState(false);
  const [subjects] = useState([
    {
      id: 1,
      codigo: 'MAT-001',
      nombre: 'Matemática',
      estado: 'cursando',
      nota: null,
      componentes: [
        { tipo: 'PARCIAL_1', valor: 8.0, peso: 30 },
        { tipo: 'PARCIAL_2', valor: 8.5, peso: 30 },
      ],
      fecha_inicio: '2024-03-01',
      profesor: 'Dr. García',
      horas_semanales: 4
    },
    {
      id: 3,
      codigo: 'FIS-001',
      nombre: 'Física',
      estado: 'aprobada',
      nota: 8.5,
      componentes: [
        { tipo: 'PARCIAL_1', valor: 8.0, peso: 30 },
        { tipo: 'PARCIAL_2', valor: 8.5, peso: 30 },
        { tipo: 'FINAL', valor: 8.7, peso: 40 },
      ],
      fecha_inicio: '2023-03-01',
      profesor: 'Ing. López',
      horas_semanales: 4
    },
    {
      id: 4,
      codigo: 'QUI-001',
      nombre: 'Química',
      estado: 'aprobada',
      nota: 7.5,
      componentes: [
        { tipo: 'PARCIAL_1', valor: 7.0, peso: 30 },
        { tipo: 'PARCIAL_2', valor: 7.8, peso: 30 },
        { tipo: 'FINAL', valor: 7.5, peso: 40 },
      ],
      fecha_inicio: '2023-03-01',
      profesor: 'Dra. Rodríguez',
      horas_semanales: 3
    },
  ]);

  const handleDescargarAnalitico = () => {
    descargarCertificadoAnalitico(reportService, user?._id || user?.id, user, setReportLoading);
  };

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
                <p>Legajo: {user?.legajo || 'STU20241001'}</p>
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
            
            {subjects.map(subject => (
              <div key={subject.id} className="subject-detail-card">
                <div className="subject-detail-header">
                  <div>
                    <h3>{subject.nombre}</h3>
                    <p className="code-label">{subject.codigo}</p>
                  </div>
                  <div className="subject-meta">
                    <span className={`status-label ${subject.estado}`}>{subject.estado.toUpperCase()}</span>
                    {subject.nota && <span className="grade-label">Nota: {subject.nota}</span>}
                  </div>
                </div>

                <div className="subject-detail-body">
                  <div className="info-row">
                    <span><strong>Profesor:</strong> {subject.profesor}</span>
                    <span><strong>Horas/Semana:</strong> {subject.horas_semanales}</span>
                    <span><strong>Desde:</strong> {new Date(subject.fecha_inicio).toLocaleDateString('es-ES')}</span>
                  </div>

                  {subject.componentes.length > 0 && (
                    <div className="components-section">
                      <h4>Calificaciones por Componente:</h4>
                      <div className="components-grid">
                        {subject.componentes.map((comp, idx) => (
                          <div key={idx} className="component-card">
                            <div className="component-type">{comp.tipo}</div>
                            <div className="component-grade">{comp.valor}</div>
                            <div className="component-weight">{comp.peso}%</div>
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
                <p className="stat-value">3</p>
              </div>
              <div className="stat-box">
                <BarChart3 size={28} />
                <h4>En Curso</h4>
                <p className="stat-value">3</p>
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
