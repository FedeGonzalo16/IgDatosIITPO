import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { Users, BarChart3, Search, Filter } from 'lucide-react';
import './AdminDashboard.css';

const AdminDashboard = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState('students');
  const [searchTerm, setSearchTerm] = useState('');
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    estado: 'todos',
    institucion: 'todas'
  });
  const navigate = useNavigate();

  // Cargar datos iniciales
  useEffect(() => {
    loadData();
  }, [activeTab, filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      let mockData = [];

      if (activeTab === 'students') {
        mockData = [
          { id: 1, legajo: 'STU20241001', nombre: 'Juan González', email: 'juan@example.com', estado: 'ACTIVO', institucion: 'Colegio San Martín', fecha_inscripcion: '2024-03-01', promedio: 8.2 },
          { id: 2, legajo: 'STU20241002', nombre: 'María López', email: 'maria@example.com', estado: 'ACTIVO', institucion: 'Colegio San Martín', fecha_inscripcion: '2024-03-01', promedio: 9.1 },
          { id: 3, legajo: 'STU20241003', nombre: 'Carlos Martínez', email: 'carlos@example.com', estado: 'ACTIVO', institucion: 'Escuela Técnica', fecha_inscripcion: '2024-03-15', promedio: 7.5 },
          { id: 4, legajo: 'STU20241004', nombre: 'Ana Rodríguez', email: 'ana@example.com', estado: 'INACTIVO', institucion: 'Colegio San Martín', fecha_inscripcion: '2023-03-01', promedio: 8.0 },
        ];
      } else if (activeTab === 'subjects') {
        mockData = [
          { id: 1, codigo: 'MAT-001', nombre: 'Matemática', nivel: 'SECUNDARIO', institucion: 'Colegio San Martín', estudiantes_inscritos: 45, aprobados: 40, reprobados: 5 },
          { id: 2, codigo: 'LEN-001', nombre: 'Lengua y Literatura', nivel: 'SECUNDARIO', institucion: 'Colegio San Martín', estudiantes_inscritos: 45, aprobados: 42, reprobados: 3 },
          { id: 3, codigo: 'FIS-001', nombre: 'Física', nivel: 'SECUNDARIO', institucion: 'Escuela Técnica', estudiantes_inscritos: 30, aprobados: 25, reprobados: 5 },
          { id: 4, codigo: 'QUI-001', nombre: 'Química', nivel: 'SECUNDARIO', institucion: 'Escuela Técnica', estudiantes_inscritos: 30, aprobados: 27, reprobados: 3 },
        ];
      } else if (activeTab === 'grades') {
        mockData = [
          { id: 1, estudiante: 'Juan González', materia: 'Matemática', nota_original: 8.5, tipo: 'FINAL', fecha: '2024-06-15', profesor: 'Dr. García' },
          { id: 2, estudiante: 'María López', materia: 'Lengua', nota_original: 9.0, tipo: 'FINAL', fecha: '2024-06-15', profesor: 'Dra. Martínez' },
          { id: 3, estudiante: 'Carlos Martínez', materia: 'Física', nota_original: 6.5, tipo: 'FINAL', fecha: '2024-06-20', profesor: 'Ing. López' },
          { id: 4, estudiante: 'Ana Rodríguez', materia: 'Química', nota_original: 8.0, tipo: 'FINAL', fecha: '2024-06-20', profesor: 'Dra. Rodríguez' },
        ];
      } else if (activeTab === 'institutions') {
        mockData = [
          { id: 1, codigo: 'INST-001', nombre: 'Colegio San Martín', nivel_educativo: 'SECUNDARIO', ubicacion: 'CABA', estudiantes: 450, materias: 12 },
          { id: 2, codigo: 'INST-002', nombre: 'Escuela Técnica', nivel_educativo: 'SECUNDARIO', ubicacion: 'Buenos Aires', estudiantes: 320, materias: 10 },
          { id: 3, codigo: 'INST-003', nombre: 'Instituto Privado', nivel_educativo: 'PRIMARIO', ubicacion: 'CABA', estudiantes: 280, materias: 8 },
        ];
      }

      // Aplicar filtros
      if (filters.estado !== 'todos' && activeTab === 'students') {
        mockData = mockData.filter(item => item.estado === filters.estado);
      }
      if (filters.institucion !== 'todas') {
        mockData = mockData.filter(item => item.institucion === filters.institucion);
      }

      // Aplicar búsqueda
      if (searchTerm) {
        mockData = mockData.filter(item => 
          Object.values(item).some(val => 
            String(val).toLowerCase().includes(searchTerm.toLowerCase())
          )
        );
      }

      setData(mockData);
      setLoading(false);
    } catch (error) {
      console.error('Error loading data:', error);
      setLoading(false);
    }
  };

  const renderStudentsTable = () => (
    <div className="table-container">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Legajo</th>
            <th>Nombre</th>
            <th>Email</th>
            <th>Estado</th>
            <th>Institución</th>
            <th>Promedio</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {data.map(student => (
            <tr key={student.id}>
              <td><strong>{student.legajo}</strong></td>
              <td>{student.nombre}</td>
              <td>{student.email}</td>
              <td><span className={`status-badge ${student.estado.toLowerCase()}`}>{student.estado}</span></td>
              <td>{student.institucion}</td>
              <td><strong>{student.promedio}</strong></td>
              <td className="action-buttons">
                <button className="btn-view">Ver</button>
                <button className="btn-edit">Editar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderSubjectsTable = () => (
    <div className="table-container">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Código</th>
            <th>Nombre</th>
            <th>Nivel</th>
            <th>Institución</th>
            <th>Inscritos</th>
            <th>Aprobados</th>
            <th>Reprobados</th>
            <th>% Aprobación</th>
          </tr>
        </thead>
        <tbody>
          {data.map(subject => {
            const approvalRate = ((subject.aprobados / subject.estudiantes_inscritos) * 100).toFixed(1);
            return (
              <tr key={subject.id}>
                <td><strong>{subject.codigo}</strong></td>
                <td>{subject.nombre}</td>
                <td>{subject.nivel}</td>
                <td>{subject.institucion}</td>
                <td>{subject.estudiantes_inscritos}</td>
                <td className="success">{subject.aprobados}</td>
                <td className="danger">{subject.reprobados}</td>
                <td><strong>{approvalRate}%</strong></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  const renderGradesTable = () => (
    <div className="table-container">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Estudiante</th>
            <th>Materia</th>
            <th>Nota</th>
            <th>Tipo</th>
            <th>Profesor</th>
            <th>Fecha</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {data.map(grade => (
            <tr key={grade.id}>
              <td>{grade.estudiante}</td>
              <td>{grade.materia}</td>
              <td><strong>{grade.nota_original}</strong></td>
              <td>{grade.tipo}</td>
              <td>{grade.profesor}</td>
              <td>{new Date(grade.fecha).toLocaleDateString('es-ES')}</td>
              <td className="action-buttons">
                <button className="btn-view">Ver</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderInstitutionsTable = () => (
    <div className="table-container">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Código</th>
            <th>Nombre</th>
            <th>Nivel</th>
            <th>Ubicación</th>
            <th>Estudiantes</th>
            <th>Materias</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {data.map(inst => (
            <tr key={inst.id}>
              <td><strong>{inst.codigo}</strong></td>
              <td>{inst.nombre}</td>
              <td>{inst.nivel_educativo}</td>
              <td>{inst.ubicacion}</td>
              <td>{inst.estudiantes}</td>
              <td>{inst.materias}</td>
              <td className="action-buttons">
                <button className="btn-view">Ver</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const getTabContent = () => {
    switch (activeTab) {
      case 'students':
        return renderStudentsTable();
      case 'subjects':
        return renderSubjectsTable();
      case 'grades':
        return renderGradesTable();
      case 'institutions':
        return renderInstitutionsTable();
      default:
        return null;
    }
  };

  return (
    <>
      <Navbar user={user} onLogout={onLogout} />
      <div className="admin-dashboard">
        <div className="container">
          <div className="dashboard-header">
            <h1>🔧 Panel Administrativo</h1>
            <p>Gestión y consultas administrativas del sistema educativo</p>
          </div>

          {/* Tabs */}
          <div className="tabs-container">
            <button
              className={`tab-button ${activeTab === 'students' ? 'active' : ''}`}
              onClick={() => setActiveTab('students')}
            >
              <Users size={20} />
              Estudiantes
            </button>
            <button
              className={`tab-button ${activeTab === 'subjects' ? 'active' : ''}`}
              onClick={() => setActiveTab('subjects')}
            >
              <BarChart3 size={20} />
              Materias
            </button>
            <button
              className={`tab-button ${activeTab === 'grades' ? 'active' : ''}`}
              onClick={() => setActiveTab('grades')}
            >
              <BarChart3 size={20} />
              Calificaciones
            </button>
            <button
              className={`tab-button ${activeTab === 'institutions' ? 'active' : ''}`}
              onClick={() => setActiveTab('institutions')}
            >
              <BarChart3 size={20} />
              Instituciones
            </button>
          </div>

          {/* Search and Filters */}
          <div className="controls-section">
            <div className="search-box">
              <Search size={20} />
              <input
                type="text"
                placeholder="Buscar..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {activeTab === 'students' && (
              <div className="filter-group">
                <select 
                  value={filters.estado}
                  onChange={(e) => setFilters({...filters, estado: e.target.value})}
                  className="filter-select"
                >
                  <option value="todos">Todos los estados</option>
                  <option value="ACTIVO">Activo</option>
                  <option value="INACTIVO">Inactivo</option>
                </select>
              </div>
            )}
          </div>

          {/* Table */}
          {loading ? (
            <div className="loading-container">Cargando datos...</div>
          ) : (
            getTabContent()
          )}

          {data.length === 0 && !loading && (
            <div className="no-data">
              <p>No se encontraron resultados</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default AdminDashboard;
