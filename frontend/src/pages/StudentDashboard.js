import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import StudentSidebar from '../components/StudentSidebar';
import {
  StudentProfile,
  StudentEnrollment,
  ChangeInstitution,
  ConvertGrades
} from '../components/StudentMenuContent';
import { BookOpen, CheckCircle, Target, TrendingUp } from 'lucide-react';
import './StudentDashboard.css';

const mockSubjects = [
  {
    id: 1,
    codigo: 'MAT-001',
    nombre: 'Matemática',
    estado: 'cursando',
    nota: null,
    fecha_inicio: '2024-03-01',
    profesor: 'Dr. García'
  },
  {
    id: 2,
    codigo: 'LEN-001',
    nombre: 'Lengua y Literatura',
    estado: 'cursando',
    nota: null,
    fecha_inicio: '2024-03-01',
    profesor: 'Dra. Martínez'
  },
  {
    id: 3,
    codigo: 'FIS-001',
    nombre: 'Física',
    estado: 'aprobada',
    nota: 8.5,
    fecha_inicio: '2023-03-01',
    profesor: 'Ing. López'
  },
  {
    id: 4,
    codigo: 'QUI-001',
    nombre: 'Química',
    estado: 'aprobada',
    nota: 7.5,
    fecha_inicio: '2023-03-01',
    profesor: 'Dra. Rodríguez'
  },
  {
    id: 5,
    codigo: 'HIS-001',
    nombre: 'Historia',
    estado: 'aprobada',
    nota: 9.0,
    fecha_inicio: '2023-03-01',
    profesor: 'Lic. Fernández'
  },
  {
    id: 6,
    codigo: 'BIO-001',
    nombre: 'Biología',
    estado: 'cursando',
    nota: null,
    fecha_inicio: '2024-03-01',
    profesor: 'Dra. González'
  }
];

const StudentDashboard = ({ user, onLogout }) => {
  const [stats, setStats] = useState({
    totalSubjects: 0,
    passedSubjects: 0,
    averageGrade: 0,
    inProgress: 0
  });
  const [activeMenu, setActiveMenu] = useState('inicio');
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    onLogout();
    navigate('/login');
  };

  useEffect(() => {
    const passedCount = mockSubjects.filter(s => s.estado === 'aprobada').length;
    const inProgressCount = mockSubjects.filter(s => s.estado === 'cursando').length;
    const grades = mockSubjects.filter(s => s.nota).map(s => s.nota);
    const average = grades.length > 0 ? (grades.reduce((a, b) => a + b) / grades.length).toFixed(2) : 0;

    setStats({
      totalSubjects: mockSubjects.length,
      passedSubjects: passedCount,
      averageGrade: average,
      inProgress: inProgressCount
    });
  }, []);

  const renderContent = () => {
    if (activeMenu === 'perfil') {
      return <StudentProfile user={user} onBack={() => setActiveMenu('inicio')} stats={stats} />;
    }
    if (activeMenu === 'inscribirse') {
      return <StudentEnrollment subjects={mockSubjects} onBack={() => setActiveMenu('inicio')} />;
    }
    if (activeMenu === 'institucion') {
      return <ChangeInstitution user={user} onBack={() => setActiveMenu('inicio')} />;
    }
    if (activeMenu === 'convertir') {
      return <ConvertGrades subjects={mockSubjects} onBack={() => setActiveMenu('inicio')} />;
    }

    return (
      <div className="dashboard-main">
        <div className="dashboard-header">
          <h1>📚 Mis Materias</h1>
          <p>Bienvenido, {user?.nombre || user?.email}</p>
        </div>

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

        <div className="subjects-section">
          <h2>Materias en Curso</h2>
          <div className="subjects-grid">
            {mockSubjects.filter(s => s.estado === 'cursando').map(subject => (
              <div key={subject.id} className="subject-card">
                <div className="subject-header">
                  <h3>{subject.nombre}</h3>
                  <span className="subject-code">{subject.codigo}</span>
                </div>
                <div className="subject-details">
                  <p><strong>Profesor:</strong> {subject.profesor}</p>
                  <p><strong>Inicio:</strong> {new Date(subject.fecha_inicio).toLocaleDateString('es-ES')}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="subjects-section">
          <h2>Materias Aprobadas</h2>
          <div className="subjects-grid">
            {mockSubjects.filter(s => s.estado === 'aprobada').map(subject => (
              <div key={subject.id} className="subject-card approved">
                <div className="subject-header">
                  <h3>{subject.nombre}</h3>
                  <span className="subject-code">{subject.codigo}</span>
                </div>
                <div className="subject-details">
                  <p><strong>Profesor:</strong> {subject.profesor}</p>
                  <div className="grade-badge">
                    <strong>Nota:</strong> {subject.nota}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
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
