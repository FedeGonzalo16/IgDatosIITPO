import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { Users, BarChart3, Search, Filter, UserCheck, FileText, Plus, X } from 'lucide-react';
import { studentService, subjectService, gradeService, institutionService, teacherService, reportService } from '../services/api';
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
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createFormData, setCreateFormData] = useState({});
  const [institutions, setInstitutions] = useState([]);
  const navigate = useNavigate();

  // Cargar datos iniciales
  useEffect(() => {
    loadData();
    if (activeTab === 'subjects' || activeTab === 'institutions') {
      loadInstitutions();
    }
  }, [activeTab, filters]);

  const loadInstitutions = async () => {
    try {
      const res = await institutionService.getAll();
      setInstitutions(res.data || []);
    } catch (error) {
      console.error('Error loading institutions:', error);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      let responseData = [];

      if (activeTab === 'students') {
        const response = await studentService.getAll();
        responseData = response.data.map(s => ({
          id: s._id,
          legajo: s.legajo,
          nombre: `${s.nombre} ${s.apellido}`,
          email: s.email,
          estado: s.metadata?.estado || 'ACTIVO',
          institucion: 'N/A',
          promedio: 0
        }));
      } else if (activeTab === 'subjects') {
        const response = await subjectService.getAll();
        responseData = response.data.map(m => ({
          id: m._id,
          codigo: m.codigo,
          nombre: m.nombre,
          nivel: m.nivel,
          institucion: m.institucion_id || 'N/A',
          estudiantes_inscritos: 0,
          aprobados: 0,
          reprobados: 0
        }));
      } else if (activeTab === 'grades') {
        const response = await gradeService.getAll();
        responseData = response.data.map(g => ({
          id: g._id,
          estudiante_id: g.estudiante_id,
          materia_id: g.materia_id,
          nota_original: g.valor_original?.nota || 'N/A',
          tipo: g.valor_original?.tipo || 'N/A',
          fecha: g.created_at ? new Date(g.created_at).toISOString().split('T')[0] : 'N/A',
          estudiante: 'Cargando...',
          materia: 'Cargando...'
        }));
        
        // Enriquecer con datos de estudiantes y materias
        for (let grade of responseData) {
          try {
            const [studentRes, subjectRes] = await Promise.all([
              studentService.getById(grade.estudiante_id).catch(() => null),
              subjectService.getById(grade.materia_id).catch(() => null)
            ]);
            if (studentRes?.data) {
              grade.estudiante = `${studentRes.data.nombre} ${studentRes.data.apellido}`;
            }
            if (subjectRes?.data) {
              grade.materia = subjectRes.data.nombre;
            }
          } catch (e) {
            console.error('Error loading details:', e);
          }
        }
      } else if (activeTab === 'institutions') {
        const response = await institutionService.getAll();
        responseData = response.data.map(i => ({
          id: i._id,
          codigo: i.codigo,
          nombre: i.nombre,
          nivel_educativo: 'N/A',
          ubicacion: i.pais,
          estudiantes: 0,
          materias: 0
        }));
      } else if (activeTab === 'teachers') {
        const response = await teacherService.getAll();
        responseData = response.data.map(t => ({
          id: t._id,
          legajo: t.legajo_docente,
          nombre: `${t.nombre} ${t.apellido}`,
          especialidad: t.especialidad || 'N/A'
        }));
      } else if (activeTab === 'reports') {
        // Cargar estadísticas generales
        try {
          const [approvalRes, gradeStatsRes] = await Promise.all([
            reportService.getApprovalStats(),
            reportService.getGradeStats()
          ]);
          responseData = [{
            tipo: 'Aprobación',
            tasa_aprobacion: approvalRes.data?.tasa_aprobacion || 0,
            aprobadas: approvalRes.data?.aprobadas || 0,
            reprobadas: approvalRes.data?.reprobadas || 0,
            total: approvalRes.data?.total_cursadas || 0
          }, {
            tipo: 'Calificaciones',
            promedio: gradeStatsRes.data?.promedio || 0,
            minima: gradeStatsRes.data?.minima || 0,
            maxima: gradeStatsRes.data?.maxima || 0,
            total: gradeStatsRes.data?.total || 0
          }];
        } catch (error) {
          console.error('Error loading reports:', error);
          responseData = [];
        }
      }

      // Aplicar filtros
      if (filters.estado !== 'todos' && activeTab === 'students') {
        responseData = responseData.filter(item => item.estado === filters.estado);
      }
      if (filters.institucion !== 'todas') {
        responseData = responseData.filter(item => item.institucion === filters.institucion);
      }

      // Aplicar búsqueda
      if (searchTerm) {
        responseData = responseData.filter(item => 
          Object.values(item).some(val => 
            String(val).toLowerCase().includes(searchTerm.toLowerCase())
          )
        );
      }

      setData(responseData);
      setLoading(false);
    } catch (error) {
      console.error('Error loading data:', error);
      setData([]);
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

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    try {
      await subjectService.create(createFormData);
      setShowCreateModal(false);
      setCreateFormData({});
      loadData();
      alert('Materia creada exitosamente');
    } catch (error) {
      alert('Error al crear materia: ' + (error.response?.data?.error || error.message));
    }
  };

  const handleCreateInstitution = async (e) => {
    e.preventDefault();
    try {
      await institutionService.create(createFormData);
      setShowCreateModal(false);
      setCreateFormData({});
      loadData();
      loadInstitutions();
      alert('Institución creada exitosamente');
    } catch (error) {
      alert('Error al crear institución: ' + (error.response?.data?.error || error.message));
    }
  };

  const renderSubjectsTable = () => (
    <div className="table-container">
      <div className="table-header">
        <h3>Materias</h3>
        <button className="btn-add" onClick={() => {
          setCreateFormData({ codigo: '', nombre: '', nivel: 'GRADO', institucion_id: '' });
          setShowCreateModal(true);
        }}>
          <Plus size={16} /> Agregar Materia
        </button>
      </div>
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
      <div className="table-header">
        <h3>Instituciones</h3>
        <button className="btn-add" onClick={() => {
          setCreateFormData({ codigo: '', nombre: '', pais: 'AR' });
          setShowCreateModal(true);
        }}>
          <Plus size={16} /> Agregar Institución
        </button>
      </div>
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
                <button className="btn-view" onClick={() => {/* TODO: Ver detalles */}}>Ver</button>
                <button className="btn-edit" onClick={() => {/* TODO: Editar */}}>Editar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderTeachersTable = () => (
    <div className="table-container">
      <div className="table-header">
        <h3>Profesores</h3>
        <button className="btn-add" onClick={() => {/* TODO: Abrir modal crear */}}>
          <Plus size={16} /> Agregar
        </button>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Legajo</th>
            <th>Nombre</th>
            <th>Especialidad</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {data.map(teacher => (
            <tr key={teacher.id}>
              <td><strong>{teacher.legajo}</strong></td>
              <td>{teacher.nombre}</td>
              <td>{teacher.especialidad}</td>
              <td className="action-buttons">
                <button className="btn-view" onClick={() => {/* TODO: Ver detalles */}}>Ver</button>
                <button className="btn-edit" onClick={() => {/* TODO: Editar */}}>Editar</button>
                <button className="btn-delete" onClick={() => {/* TODO: Eliminar */}}>Eliminar</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderReportsView = () => (
    <div className="reports-container">
      <h3>Reportes y Estadísticas</h3>
      <div className="reports-grid">
        {data.map((report, idx) => (
          <div key={idx} className="report-card">
            <h4>{report.tipo}</h4>
            {report.tasa_aprobacion !== undefined && (
              <>
                <div className="stat-item">
                  <span>Tasa de Aprobación:</span>
                  <strong>{report.tasa_aprobacion.toFixed(2)}%</strong>
                </div>
                <div className="stat-item">
                  <span>Aprobadas:</span>
                  <strong className="success">{report.aprobadas}</strong>
                </div>
                <div className="stat-item">
                  <span>Reprobadas:</span>
                  <strong className="danger">{report.reprobadas}</strong>
                </div>
                <div className="stat-item">
                  <span>Total:</span>
                  <strong>{report.total}</strong>
                </div>
              </>
            )}
            {report.promedio !== undefined && (
              <>
                <div className="stat-item">
                  <span>Promedio:</span>
                  <strong>{report.promedio.toFixed(2)}</strong>
                </div>
                <div className="stat-item">
                  <span>Mínima:</span>
                  <strong>{report.minima}</strong>
                </div>
                <div className="stat-item">
                  <span>Máxima:</span>
                  <strong>{report.maxima}</strong>
                </div>
                <div className="stat-item">
                  <span>Total Calificaciones:</span>
                  <strong>{report.total}</strong>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
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
      case 'teachers':
        return renderTeachersTable();
      case 'reports':
        return renderReportsView();
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
            <button
              className={`tab-button ${activeTab === 'teachers' ? 'active' : ''}`}
              onClick={() => setActiveTab('teachers')}
            >
              <UserCheck size={20} />
              Profesores
            </button>
            <button
              className={`tab-button ${activeTab === 'reports' ? 'active' : ''}`}
              onClick={() => setActiveTab('reports')}
            >
              <FileText size={20} />
              Reportes
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

          {/* Modal de creación */}
          {showCreateModal && (
            <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>
                    {activeTab === 'subjects' ? 'Crear Nueva Materia' : 
                     activeTab === 'institutions' ? 'Crear Nueva Institución' : 
                     'Crear Nuevo'}
                  </h2>
                  <button className="modal-close" onClick={() => setShowCreateModal(false)}>
                    <X size={24} />
                  </button>
                </div>
                <form onSubmit={activeTab === 'subjects' ? handleCreateSubject : handleCreateInstitution}>
                  {activeTab === 'subjects' && (
                    <>
                      <div className="form-group">
                        <label>Código *</label>
                        <input
                          type="text"
                          value={createFormData.codigo || ''}
                          onChange={(e) => setCreateFormData({...createFormData, codigo: e.target.value})}
                          placeholder="Ej: MAT-101"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Nombre *</label>
                        <input
                          type="text"
                          value={createFormData.nombre || ''}
                          onChange={(e) => setCreateFormData({...createFormData, nombre: e.target.value})}
                          placeholder="Ej: Matemática I"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Nivel</label>
                        <select
                          value={createFormData.nivel || 'GRADO'}
                          onChange={(e) => setCreateFormData({...createFormData, nivel: e.target.value})}
                        >
                          <option value="GRADO">Grado</option>
                          <option value="POSTGRADO">Postgrado</option>
                          <option value="SECUNDARIO">Secundario</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label>Institución *</label>
                        <select
                          value={createFormData.institucion_id || ''}
                          onChange={(e) => setCreateFormData({...createFormData, institucion_id: e.target.value})}
                          required
                        >
                          <option value="">Seleccionar...</option>
                          {institutions.map(inst => (
                            <option key={inst._id} value={inst._id}>{inst.nombre}</option>
                          ))}
                        </select>
                      </div>
                    </>
                  )}
                  {activeTab === 'institutions' && (
                    <>
                      <div className="form-group">
                        <label>Código *</label>
                        <input
                          type="text"
                          value={createFormData.codigo || ''}
                          onChange={(e) => setCreateFormData({...createFormData, codigo: e.target.value})}
                          placeholder="Ej: INST-001"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Nombre *</label>
                        <input
                          type="text"
                          value={createFormData.nombre || ''}
                          onChange={(e) => setCreateFormData({...createFormData, nombre: e.target.value})}
                          placeholder="Ej: Colegio Nacional"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>País</label>
                        <input
                          type="text"
                          value={createFormData.pais || 'AR'}
                          onChange={(e) => setCreateFormData({...createFormData, pais: e.target.value})}
                          placeholder="AR"
                        />
                      </div>
                    </>
                  )}
                  <div className="modal-actions">
                    <button type="button" className="btn-cancel" onClick={() => setShowCreateModal(false)}>
                      Cancelar
                    </button>
                    <button type="submit" className="btn-submit">
                      Crear
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default AdminDashboard;
