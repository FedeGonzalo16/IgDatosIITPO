import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { Users, BarChart3, Search, Filter, UserCheck, Plus, X, RefreshCw } from 'lucide-react';
import { studentService, subjectService, gradeService, institutionService, teacherService, conversionService, gradingOperations, reportService } from '../services/api';
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
  const [studentsList, setStudentsList] = useState([]);
  const [subjectsList, setSubjectsList] = useState([]);
  const [loadingStudentsSubjects, setLoadingStudentsSubjects] = useState(false);
  const [conversionRules, setConversionRules] = useState([]);
  const [showConversionModal, setShowConversionModal] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState(null);
  const [ruleForm, setRuleForm] = useState({ codigo_regla: '', nombre: '', mapeo: [{ nota_origen: '', nota_destino: '' }] });
  const [applyConversionForm, setApplyConversionForm] = useState({ calificacion_id: '', codigo_regla: '' });
  const [calificacionesList, setCalificacionesList] = useState([]);
  const [altaForm, setAltaForm] = useState({
    inscribir: { estudiante_id: '', materia_id: '', anio_lectivo: new Date().getFullYear() },
    cargarNota: { estudiante_id: '', materia_id: '', tipo_nota: 'final', valor: '' },
    cerrarCursada: { estudiante_id: '', materia_id: '' },
    registrar: { estudiante_id: '', materia_id: '', tipo: 'FINAL', nota: '' }
  });
  const navigate = useNavigate();

  // Cargar listas para dropdowns al montar (estudiantes, materias) y al cambiar de tab
  useEffect(() => {
    loadStudentsAndSubjects();
  }, []);

  useEffect(() => {
    loadData();
    if (activeTab === 'subjects' || activeTab === 'institutions' || activeTab === 'students') {
      loadInstitutions();
    }
    if (activeTab === 'grades') {
      loadStudentsAndSubjects();
    }
  }, [activeTab, filters]);

  const loadStudentsAndSubjects = async () => {
    setLoadingStudentsSubjects(true);
    try {
      const [stRes, subRes] = await Promise.all([
        studentService.getAll().catch((err) => {
          console.error('Error fetching students:', err?.response?.data || err);
          return { data: [] };
        }),
        subjectService.getAll().catch((err) => {
          console.error('Error fetching subjects:', err?.response?.data || err);
          return { data: [] };
        })
      ]);
      const st = Array.isArray(stRes?.data) ? stRes.data : (stRes?.data?.data || []);
      const sub = Array.isArray(subRes?.data) ? subRes.data : (subRes?.data?.data || []);
      setStudentsList(st);
      setSubjectsList(sub);
    } catch (e) {
      console.error('Error loading students/subjects:', e);
      setStudentsList([]);
      setSubjectsList([]);
    } finally {
      setLoadingStudentsSubjects(false);
    }
  };

  const loadConversionRules = async () => {
    try {
      const res = await conversionService.getAllRules();
      setConversionRules(res.data || []);
    } catch (e) {
      console.error('Error loading rules:', e);
      setConversionRules([]);
    }
  };


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
        // El backend ya resuelve institucion_nombre vía Neo4j en get_all()
        const response = await studentService.getAll();
        responseData = response.data.map(s => ({
          id: s._id,
          legajo: s.legajo,
          nombre: `${s.nombre} ${s.apellido}`,
          email: s.email,
          estado: s.metadata?.estado || 'ACTIVO',
          institucion: s.institucion_nombre || 'Sin institución',
          promedio: '—'
        }));

      } else if (activeTab === 'subjects') {
        // Cargamos materias e instituciones en paralelo para resolver el nombre
        const [subjectsRes, instsRes] = await Promise.all([
          subjectService.getAll(),
          institutionService.getAll()
        ]);
        const instMap = {};
        (instsRes.data || []).forEach(i => { instMap[i._id] = i.nombre; });
        responseData = subjectsRes.data.map(m => ({
          id: m._id,
          codigo: m.codigo,
          nombre: m.nombre,
          nivel: m.nivel || '—',
          institucion: instMap[m.institucion_id] || '—'
        }));

      } else if (activeTab === 'grades') {
        const response = await gradeService.getAll();
        const grades = response.data.map(g => ({
          id: g._id,
          estudiante_id: g.estudiante_id,
          materia_id: g.materia_id,
          nota_original: g.valor_original?.nota ?? '—',
          tipo: g.valor_original?.tipo ?? '—',
          fecha: g.created_at ? new Date(g.created_at).toISOString().split('T')[0] : '—',
          estudiante: '—',
          materia: '—'
        }));

        // Enriquecimiento paralelo: IDs únicos → un fetch por ID único
        const uniqueStudentIds = [...new Set(grades.map(g => g.estudiante_id).filter(Boolean))];
        const uniqueSubjectIds = [...new Set(grades.map(g => g.materia_id).filter(Boolean))];

        const [studentResults, subjectResults] = await Promise.all([
          Promise.all(uniqueStudentIds.map(id => studentService.getById(id).catch(() => null))),
          Promise.all(uniqueSubjectIds.map(id => subjectService.getById(id).catch(() => null)))
        ]);

        const studentMap = {};
        uniqueStudentIds.forEach((id, i) => {
          const d = studentResults[i]?.data;
          if (d) studentMap[id] = `${d.nombre} ${d.apellido}`;
        });
        const subjectMap = {};
        uniqueSubjectIds.forEach((id, i) => {
          const d = subjectResults[i]?.data;
          if (d) subjectMap[id] = d.nombre;
        });

        responseData = grades.map(g => ({
          ...g,
          estudiante: studentMap[g.estudiante_id] || '—',
          materia: subjectMap[g.materia_id] || '—'
        }));

      } else if (activeTab === 'institutions') {
        const response = await institutionService.getAll();
        const nivelLabel = { SECUNDARIO: 'Secundario', UNIVERSITARIO: 'Universitario', TERCIARIO: 'Terciario' };
        const baseData = response.data.map(i => ({
          id: i._id,
          codigo: i.codigo,
          nombre: i.nombre,
          nivel_educativo: nivelLabel[i.nivel] || i.nivel || 'No especificado',
          ubicacion: i.pais,
          estudiantes: '—',
          materias: '—'
        }));

        // Cargamos estadísticas reales de cada institución en paralelo
        const reports = await Promise.all(
          baseData.map(inst => reportService.getInstitutionReport(inst.id).catch(() => null))
        );
        responseData = baseData.map((inst, idx) => {
          const stats = reports[idx]?.data?.estadisticas;
          return {
            ...inst,
            estudiantes: stats != null ? stats.total_estudiantes : '—',
            materias: stats != null ? stats.total_materias : '—'
          };
        });

      } else if (activeTab === 'teachers') {
        const response = await teacherService.getAll();
        responseData = response.data.map(t => ({
          id: t._id,
          legajo: t.legajo_docente,
          nombre: `${t.nombre} ${t.apellido}`,
          especialidad: t.especialidad || '—'
        }));
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
      <div className="table-header">
        <h3>Estudiantes</h3>
        <button className="btn-add" onClick={() => {
          setCreateFormData({ legajo: '', nombre: '', apellido: '', email: '', institucion_id: '' });
          setShowCreateModal(true);
        }}>
          <Plus size={16} /> Agregar Estudiante
        </button>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Legajo</th>
            <th>Nombre</th>
            <th>Email</th>
            <th>Estado</th>
            <th>Institución</th>
          </tr>
        </thead>
        <tbody>
          {data.map(student => (
            <tr key={student.id}>
              <td><strong>{student.legajo}</strong></td>
              <td>{student.nombre}</td>
              <td>{student.email}</td>
              <td><span className={`status-badge ${(student.estado || 'activo').toLowerCase()}`}>{student.estado || 'ACTIVO'}</span></td>
              <td>{student.institucion}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const handleCreateStudent = async (e) => {
    e.preventDefault();
    try {
      const { legajo, nombre, apellido, email, institucion_id } = createFormData;
      const res = await studentService.create({ legajo, nombre, apellido, email: email || '' });
      const newId = res.data?.id;
      if (newId && institucion_id) {
        await studentService.update(newId, { institucion_id });
      }
      setShowCreateModal(false);
      setCreateFormData({});
      loadData();
      loadStudentsAndSubjects();
      alert('Estudiante creado exitosamente');
    } catch (error) {
      alert('Error al crear estudiante: ' + (error.response?.data?.error || error.message));
    }
  };

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

  const handleCreateTeacher = async (e) => {
    e.preventDefault();
    try {
      await teacherService.create({
        legajo_docente: createFormData.legajo_docente,
        nombre: createFormData.nombre,
        apellido: createFormData.apellido,
        especialidad: createFormData.especialidad || ''
      });
      setShowCreateModal(false);
      setCreateFormData({});
      loadData();
      alert('Profesor creado exitosamente');
    } catch (error) {
      alert('Error al crear profesor: ' + (error.response?.data?.error || error.message));
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
          </tr>
        </thead>
        <tbody>
          {data.map(subject => (
            <tr key={subject.id}>
              <td><strong>{subject.codigo}</strong></td>
              <td>{subject.nombre}</td>
              <td>{subject.nivel}</td>
              <td>{subject.institucion}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const handleInscribir = async (e) => {
    e.preventDefault();
    try {
      await gradingOperations.inscribirAlumno({
        estudiante_id: altaForm.inscribir.estudiante_id,
        materia_id: altaForm.inscribir.materia_id,
        anio_lectivo: altaForm.inscribir.anio_lectivo
      });
      alert('Inscripción realizada.');
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleCargarNota = async (e) => {
    e.preventDefault();
    try {
      await gradingOperations.cargarNota({
        estudiante_id: altaForm.cargarNota.estudiante_id,
        materia_id: altaForm.cargarNota.materia_id,
        tipo_nota: altaForm.cargarNota.tipo_nota,
        valor: Number(altaForm.cargarNota.valor)
      });
      alert('Nota cargada.');
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleCerrarCursada = async (e) => {
    e.preventDefault();
    try {
      await gradingOperations.cerrarCursada({
        estudiante_id: altaForm.cerrarCursada.estudiante_id,
        materia_id: altaForm.cerrarCursada.materia_id
      });
      alert('Cursada cerrada (APROBADO/REPROBADO según notas).');
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleRegistrarCalificacion = async (e) => {
    e.preventDefault();
    try {
      await gradeService.create({
        estudiante_id: altaForm.registrar.estudiante_id,
        materia_id: altaForm.registrar.materia_id,
        valor_original: { tipo: altaForm.registrar.tipo, nota: altaForm.registrar.nota }
      });
      alert('Calificación registrada.');
      setAltaForm(prev => ({ ...prev, registrar: { ...prev.registrar, tipo: 'FINAL', nota: '' } }));
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.error || err.message));
    }
  };

  const studentLabel = (s) => [s.nombre, s.apellido].filter(Boolean).join(' ') || s.email || s._id || '—';
  const subjectLabel = (m) => (m.codigo ? `${m.codigo} - ` : '') + (m.nombre || m._id || '—');

  const renderGradesAltaPanel = () => (
    <div className="alta-panel table-container">
      <div className="alta-panel-header">
        <h3>Alta de calificación</h3>
        <button type="button" className="btn-submit-small btn-outline" onClick={loadStudentsAndSubjects} disabled={loadingStudentsSubjects} title="Recargar listas de estudiantes y materias">
          {loadingStudentsSubjects ? 'Cargando...' : 'Actualizar listas'}
        </button>
      </div>
      <div className="alta-grid">
        <div className="alta-card">
          <h4>Inscribir alumno a materia</h4>
          <form onSubmit={handleInscribir} className="alta-form">
            <select value={altaForm.inscribir.estudiante_id} onChange={e => setAltaForm(prev => ({ ...prev, inscribir: { ...prev.inscribir, estudiante_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : studentsList.length === 0 ? 'No hay estudiantes' : 'Estudiante'}</option>
              {studentsList.map(s => <option key={s._id} value={s._id}>{studentLabel(s)}</option>)}
            </select>
            <select value={altaForm.inscribir.materia_id} onChange={e => setAltaForm(prev => ({ ...prev, inscribir: { ...prev.inscribir, materia_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : subjectsList.length === 0 ? 'No hay materias' : 'Materia'}</option>
              {subjectsList.map(m => <option key={m._id} value={m._id}>{subjectLabel(m)}</option>)}
            </select>
            <input type="number" min="2020" max="2030" value={altaForm.inscribir.anio_lectivo} onChange={e => setAltaForm(prev => ({ ...prev, inscribir: { ...prev.inscribir, anio_lectivo: +e.target.value } }))} />
            <button type="submit" className="btn-submit-small">Inscribir</button>
          </form>
        </div>
        <div className="alta-card">
          <h4>Cargar nota</h4>
          <form onSubmit={handleCargarNota} className="alta-form">
            <select value={altaForm.cargarNota.estudiante_id} onChange={e => setAltaForm(prev => ({ ...prev, cargarNota: { ...prev.cargarNota, estudiante_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : studentsList.length === 0 ? 'No hay estudiantes' : 'Estudiante'}</option>
              {studentsList.map(s => <option key={s._id} value={s._id}>{studentLabel(s)}</option>)}
            </select>
            <select value={altaForm.cargarNota.materia_id} onChange={e => setAltaForm(prev => ({ ...prev, cargarNota: { ...prev.cargarNota, materia_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : subjectsList.length === 0 ? 'No hay materias' : 'Materia'}</option>
              {subjectsList.map(m => <option key={m._id} value={m._id}>{m.codigo || m.nombre || m._id}</option>)}
            </select>
            <select value={altaForm.cargarNota.tipo_nota} onChange={e => setAltaForm(prev => ({ ...prev, cargarNota: { ...prev.cargarNota, tipo_nota: e.target.value } }))}>
              <option value="primer_parcial">1er parcial</option>
              <option value="segundo_parcial">2do parcial</option>
              <option value="final">Final</option>
              <option value="previo">Previo</option>
            </select>
            <input type="number" step="0.01" min="0" max="10" placeholder="Nota" value={altaForm.cargarNota.valor} onChange={e => setAltaForm(prev => ({ ...prev, cargarNota: { ...prev.cargarNota, valor: e.target.value } }))} required />
            <button type="submit" className="btn-submit-small">Cargar</button>
          </form>
        </div>
        <div className="alta-card">
          <h4>Cerrar cursada</h4>
          <form onSubmit={handleCerrarCursada} className="alta-form">
            <select value={altaForm.cerrarCursada.estudiante_id} onChange={e => setAltaForm(prev => ({ ...prev, cerrarCursada: { ...prev.cerrarCursada, estudiante_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : studentsList.length === 0 ? 'No hay estudiantes' : 'Estudiante'}</option>
              {studentsList.map(s => <option key={s._id} value={s._id}>{studentLabel(s)}</option>)}
            </select>
            <select value={altaForm.cerrarCursada.materia_id} onChange={e => setAltaForm(prev => ({ ...prev, cerrarCursada: { ...prev.cerrarCursada, materia_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : subjectsList.length === 0 ? 'No hay materias' : 'Materia'}</option>
              {subjectsList.map(m => <option key={m._id} value={m._id}>{m.codigo || m.nombre || m._id}</option>)}
            </select>
            <button type="submit" className="btn-submit-small">Cerrar cursada</button>
          </form>
        </div>
        <div className="alta-card">
          <h4>Registrar calificación (libro)</h4>
          <form onSubmit={handleRegistrarCalificacion} className="alta-form">
            <select value={altaForm.registrar.estudiante_id} onChange={e => setAltaForm(prev => ({ ...prev, registrar: { ...prev.registrar, estudiante_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : studentsList.length === 0 ? 'No hay estudiantes' : 'Estudiante'}</option>
              {studentsList.map(s => <option key={s._id} value={s._id}>{studentLabel(s)}</option>)}
            </select>
            <select value={altaForm.registrar.materia_id} onChange={e => setAltaForm(prev => ({ ...prev, registrar: { ...prev.registrar, materia_id: e.target.value } }))} required disabled={loadingStudentsSubjects}>
              <option value="">{loadingStudentsSubjects ? 'Cargando...' : subjectsList.length === 0 ? 'No hay materias' : 'Materia'}</option>
              {subjectsList.map(m => <option key={m._id} value={m._id}>{m.codigo || m.nombre || m._id}</option>)}
            </select>
            <select value={altaForm.registrar.tipo} onChange={e => setAltaForm(prev => ({ ...prev, registrar: { ...prev.registrar, tipo: e.target.value } }))}>
              <option value="PARCIAL_1">Parcial 1</option>
              <option value="PARCIAL_2">Parcial 2</option>
              <option value="FINAL">Final</option>
              <option value="PREVIO">Previo</option>
            </select>
            <input type="text" placeholder="Nota (ej: 7 o A)" value={altaForm.registrar.nota} onChange={e => setAltaForm(prev => ({ ...prev, registrar: { ...prev.registrar, nota: e.target.value } }))} required />
            <button type="submit" className="btn-submit-small">Registrar</button>
          </form>
        </div>
      </div>
    </div>
  );

  const renderGradesTable = () => (
    <>
      {renderGradesAltaPanel()}
      <div className="table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Estudiante</th>
              <th>Materia</th>
              <th>Nota</th>
              <th>Tipo</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody>
            {data.map(grade => (
              <tr key={grade.id}>
                <td>{grade.estudiante}</td>
                <td>{grade.materia}</td>
                <td><strong>{grade.nota_original}</strong></td>
                <td>{grade.tipo}</td>
                <td>{grade.fecha !== '—' ? new Date(grade.fecha).toLocaleDateString('es-ES') : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );

  const renderInstitutionsTable = () => (
    <div className="table-container">
      <div className="table-header">
        <h3>Instituciones</h3>
        <button className="btn-add" onClick={() => {
          setCreateFormData({ codigo: '', nombre: '', nivel: 'UNIVERSITARIO', pais: 'AR' });
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
          </tr>
        </thead>
        <tbody>
          {data.map(inst => (
            <tr key={inst.id}>
              <td><strong>{inst.codigo}</strong></td>
              <td>{inst.nombre}</td>
              <td>
                <span className={`nivel-badge ${(inst.nivel_educativo || '').toLowerCase()}`}>
                  {inst.nivel_educativo || '—'}
                </span>
              </td>
              <td>{inst.ubicacion}</td>
              <td>{inst.estudiantes}</td>
              <td>{inst.materias}</td>
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
        <button className="btn-add" onClick={() => {
          setCreateFormData({ legajo_docente: '', nombre: '', apellido: '', especialidad: '' });
          setShowCreateModal(true);
        }}>
          <Plus size={16} /> Agregar Profesor
        </button>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Legajo</th>
            <th>Nombre</th>
            <th>Especialidad</th>
          </tr>
        </thead>
        <tbody>
          {data.map(teacher => (
            <tr key={teacher.id}>
              <td><strong>{teacher.legajo}</strong></td>
              <td>{teacher.nombre}</td>
              <td>{teacher.especialidad}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const handleCreateRule = async (e) => {
    e.preventDefault();
    try {
      await conversionService.createRule({
        codigo_regla: ruleForm.codigo_regla,
        nombre: ruleForm.nombre,
        mapeo: ruleForm.mapeo.filter(m => m.nota_origen !== '' || m.nota_destino !== '')
      });
      setShowConversionModal(false);
      setRuleForm({ codigo_regla: '', nombre: '', mapeo: [{ nota_origen: '', nota_destino: '' }] });
      loadConversionRules();
      alert('Regla creada.');
    } catch (err) {
      alert('Error: ' + (err.response?.data?.error || err.message));
    }
  };

  const handleUpdateRule = async (e) => {
    e.preventDefault();
    if (!editingRuleId) return;
    try {
      await conversionService.updateRule(editingRuleId, {
        codigo_regla: ruleForm.codigo_regla,
        nombre: ruleForm.nombre,
        mapeo: ruleForm.mapeo.filter(m => m.nota_origen !== '' || m.nota_destino !== '')
      });
      setShowConversionModal(false);
      setEditingRuleId(null);
      setRuleForm({ codigo_regla: '', nombre: '', mapeo: [{ nota_origen: '', nota_destino: '' }] });
      loadConversionRules();
      alert('Regla actualizada.');
    } catch (err) {
      alert('Error: ' + (err.response?.data?.error || err.message));
    }
  };

  const openEditRule = (rule) => {
    setEditingRuleId(rule._id);
    setRuleForm({
      codigo_regla: rule.codigo_regla || '',
      nombre: rule.nombre || '',
      mapeo: (rule.mapeo && rule.mapeo.length) ? rule.mapeo : [{ nota_origen: '', nota_destino: '' }]
    });
    setShowConversionModal(true);
  };

  const openNewRule = () => {
    setEditingRuleId(null);
    setRuleForm({ codigo_regla: '', nombre: '', mapeo: [{ nota_origen: '', nota_destino: '' }] });
    setShowConversionModal(true);
  };

  const handleApplyConversion = async (e) => {
    e.preventDefault();
    try {
      const res = await conversionService.applyConversion(applyConversionForm);
      alert('Valor convertido: ' + res.data?.valor_convertido);
      loadData();
    } catch (err) {
      alert('Error: ' + (err.response?.data?.error || err.message));
    }
  };

  const renderConversionsView = () => (
    <div className="table-container">
      <div className="table-header">
        <h3>Reglas de conversión</h3>
        <button className="btn-add" onClick={openNewRule}><Plus size={16} /> Nueva regla</button>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Código</th>
            <th>Nombre</th>
            <th>Mapeo (origen → destino)</th>
          </tr>
        </thead>
        <tbody>
          {conversionRules.map(r => (
            <tr key={r._id}>
              <td><strong>{r.codigo_regla}</strong></td>
              <td>{r.nombre || '-'}</td>
              <td>{(r.mapeo || []).map(m => `${m.nota_origen}→${m.nota_destino}`).join(', ') || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {conversionRules.length === 0 && !loading && <p className="no-data-inline">No hay reglas. Crear una con &quot;Nueva regla&quot;.</p>}
      <div className="alta-panel" style={{ marginTop: '24px' }}>
        <h3>Aplicar conversión a una calificación</h3>
        <form onSubmit={handleApplyConversion} className="alta-form inline-form">
          <select value={applyConversionForm.calificacion_id} onChange={e => setApplyConversionForm(prev => ({ ...prev, calificacion_id: e.target.value }))} required>
            <option value="">Seleccionar calificación</option>
            {calificacionesList.slice(0, 50).map(c => (
              <option key={c._id} value={c._id}>
                {c._id.slice(-6)} — nota: {c.valor_original?.nota ?? 'N/A'}
              </option>
            ))}
          </select>
          <select value={applyConversionForm.codigo_regla} onChange={e => setApplyConversionForm(prev => ({ ...prev, codigo_regla: e.target.value }))} required>
            <option value="">Regla</option>
            {conversionRules.map(r => <option key={r._id} value={r.codigo_regla}>{r.codigo_regla}</option>)}
          </select>
          <button type="submit" className="btn-submit-small">Aplicar</button>
        </form>
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

          {/* Modal Conversión (crear/editar regla) */}
          {showConversionModal && (
            <div className="modal-overlay" onClick={() => { setShowConversionModal(false); setEditingRuleId(null); }}>
              <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>{editingRuleId ? 'Editar regla' : 'Nueva regla de conversión'}</h2>
                  <button className="modal-close" onClick={() => { setShowConversionModal(false); setEditingRuleId(null); }}><X size={24} /></button>
                </div>
                <form onSubmit={editingRuleId ? handleUpdateRule : handleCreateRule}>
                  <div className="form-group">
                    <label>Código regla *</label>
                    <input type="text" value={ruleForm.codigo_regla} onChange={e => setRuleForm(prev => ({ ...prev, codigo_regla: e.target.value }))} placeholder="Ej: ESCALA_10_A_4" required />
                  </div>
                  <div className="form-group">
                    <label>Nombre</label>
                    <input type="text" value={ruleForm.nombre} onChange={e => setRuleForm(prev => ({ ...prev, nombre: e.target.value }))} placeholder="Ej: Escala 0-10 a A-D" />
                  </div>
                  <div className="form-group">
                    <label>Mapeo (nota_origen → nota_destino)</label>
                    {ruleForm.mapeo.map((m, i) => (
                      <div key={i} className="mapeo-row">
                        <input type="text" placeholder="Origen" value={m.nota_origen} onChange={e => {
                          const next = [...ruleForm.mapeo]; next[i] = { ...next[i], nota_origen: e.target.value }; setRuleForm(prev => ({ ...prev, mapeo: next }));
                        }} />
                        <span>→</span>
                        <input type="text" placeholder="Destino" value={m.nota_destino} onChange={e => {
                          const next = [...ruleForm.mapeo]; next[i] = { ...next[i], nota_destino: e.target.value }; setRuleForm(prev => ({ ...prev, mapeo: next }));
                        }} />
                        {ruleForm.mapeo.length > 1 && (
                          <button type="button" className="btn-delete-small" onClick={() => setRuleForm(prev => ({ ...prev, mapeo: prev.mapeo.filter((_, j) => j !== i) }))}>Quitar</button>
                        )}
                      </div>
                    ))}
                    <button type="button" className="btn-add-small" onClick={() => setRuleForm(prev => ({ ...prev, mapeo: [...prev.mapeo, { nota_origen: '', nota_destino: '' }] }))}>+ Par</button>
                  </div>
                  <div className="modal-actions">
                    <button type="button" className="btn-cancel" onClick={() => { setShowConversionModal(false); setEditingRuleId(null); }}>Cancelar</button>
                    <button type="submit" className="btn-submit">{editingRuleId ? 'Guardar' : 'Crear'}</button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Modal de creación */}
          {showCreateModal && (
            <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h2>
                    {activeTab === 'students'     ? 'Crear Nuevo Estudiante' :
                     activeTab === 'subjects'     ? 'Crear Nueva Materia' :
                     activeTab === 'institutions' ? 'Crear Nueva Institución' :
                     activeTab === 'teachers'     ? 'Crear Nuevo Profesor' : 'Crear Nuevo'}
                  </h2>
                  <button className="modal-close" onClick={() => setShowCreateModal(false)}>
                    <X size={24} />
                  </button>
                </div>
                <form onSubmit={
                  activeTab === 'students'     ? handleCreateStudent :
                  activeTab === 'subjects'     ? handleCreateSubject :
                  activeTab === 'institutions' ? handleCreateInstitution :
                  activeTab === 'teachers'     ? handleCreateTeacher : (e) => e.preventDefault()
                }>
                  {activeTab === 'students' && (
                    <>
                      <div className="form-group">
                        <label>Legajo *</label>
                        <input
                          type="text"
                          value={createFormData.legajo || ''}
                          onChange={(e) => setCreateFormData({...createFormData, legajo: e.target.value})}
                          placeholder="Ej: EST-001"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Nombre *</label>
                        <input
                          type="text"
                          value={createFormData.nombre || ''}
                          onChange={(e) => setCreateFormData({...createFormData, nombre: e.target.value})}
                          placeholder="Ej: Juan"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Apellido *</label>
                        <input
                          type="text"
                          value={createFormData.apellido || ''}
                          onChange={(e) => setCreateFormData({...createFormData, apellido: e.target.value})}
                          placeholder="Ej: Pérez"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Email</label>
                        <input
                          type="email"
                          value={createFormData.email || ''}
                          onChange={(e) => setCreateFormData({...createFormData, email: e.target.value})}
                          placeholder="Ej: juan.perez@email.com"
                        />
                      </div>
                      <div className="form-group">
                        <label>Institución</label>
                        <select
                          value={createFormData.institucion_id || ''}
                          onChange={(e) => setCreateFormData({...createFormData, institucion_id: e.target.value})}
                        >
                          <option value="">Sin institución</option>
                          {institutions.map(inst => (
                            <option key={inst._id} value={inst._id}>{inst.nombre}</option>
                          ))}
                        </select>
                      </div>
                    </>
                  )}
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
                        <label>Nivel educativo *</label>
                        <select
                          value={createFormData.nivel || 'UNIVERSITARIO'}
                          onChange={(e) => setCreateFormData({...createFormData, nivel: e.target.value})}
                          required
                        >
                          <option value="SECUNDARIO">Secundario</option>
                          <option value="UNIVERSITARIO">Universitario</option>
                          <option value="TERCIARIO">Terciario</option>
                        </select>
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
                  {activeTab === 'teachers' && (
                    <>
                      <div className="form-group">
                        <label>Legajo Docente *</label>
                        <input
                          type="text"
                          value={createFormData.legajo_docente || ''}
                          onChange={(e) => setCreateFormData({...createFormData, legajo_docente: e.target.value})}
                          placeholder="Ej: PROF-001"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Nombre *</label>
                        <input
                          type="text"
                          value={createFormData.nombre || ''}
                          onChange={(e) => setCreateFormData({...createFormData, nombre: e.target.value})}
                          placeholder="Ej: Carlos"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Apellido *</label>
                        <input
                          type="text"
                          value={createFormData.apellido || ''}
                          onChange={(e) => setCreateFormData({...createFormData, apellido: e.target.value})}
                          placeholder="Ej: Mendoza"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Especialidad</label>
                        <input
                          type="text"
                          value={createFormData.especialidad || ''}
                          onChange={(e) => setCreateFormData({...createFormData, especialidad: e.target.value})}
                          placeholder="Ej: Bases de Datos"
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
