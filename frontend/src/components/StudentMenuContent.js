import React, { useState, useEffect } from 'react';
import { ArrowLeft, Plus, X, Edit } from 'lucide-react';
import { 
  subjectService, 
  gradingOperations, 
  conversionService, 
  institutionService, 
  studentService, 
  gradeService,
  trajectoryService,
  reportService
} from '../services/api';
import { descargarCertificadoAnalitico } from '../utils/certificadoAnalitico';
import './StudentMenuContent.css';

const StudentProfile = ({ user, onBack, stats, onUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState({
    nombre: user?.nombre || '',
    apellido: user?.apellido || '',
    email: user?.email || '',
    legajo: user?.legajo || ''
  });
  const [institutionName, setInstitutionName] = useState(user?.institucion || '');
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [trajectory, setTrajectory] = useState(null);
  const [institutions, setInstitutions] = useState([]);
  const [conversionRules, setConversionRules] = useState([]);
  const [selectedInstitution, setSelectedInstitution] = useState('');
  const [selectedRule, setSelectedRule] = useState('AR_TO_US');
  const [trajectoryLoading, setTrajectoryLoading] = useState(true);
  const [subjects, setSubjects] = useState([]);
  const [subjectsLoading, setSubjectsLoading] = useState(true);
  const [reportLoading, setReportLoading] = useState(false);

  useEffect(() => {
    const loadTrajectory = async () => {
      const studentId = user?._id || user?.id;
      if (!studentId) {
        setTrajectoryLoading(false);
        return;
      }
      try {
        const res = await trajectoryService.getStudentTrajectory(studentId);
        setTrajectory(res.data);
      } catch (err) {
        console.error('Error loading trajectory:', err);
      } finally {
        setTrajectoryLoading(false);
      }
    };
    loadTrajectory();
  }, [user?._id, user?.id]);

  const handleSave = async () => {
    try {
      setLoading(true);
      setErrorMessage('');
      const studentId = user?._id || user?.id;
      
      if (!studentId) {
        setErrorMessage('No se pudo identificar al estudiante');
        return;
      }

      await studentService.update(studentId, editedData);
      
      // Actualizar usuario en localStorage
      const updatedUser = { ...user, ...editedData };
      localStorage.setItem('user', JSON.stringify(updatedUser));
      
      setSuccessMessage('Perfil actualizado correctamente');
      setIsEditing(false);
      
      if (onUpdate) {
        onUpdate(updatedUser);
      }
      
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Error updating profile:', error);
      setErrorMessage(error.response?.data?.error || 'Error al actualizar perfil');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const fetchInstitutionName = async () => {
      try {
        const instsRes = await institutionService.getAll().catch(() => ({ data: [] }));
        const insts = instsRes.data || [];
        const instId = user?.institucion_id || user?.institucion;
        if (!instId) {
          setInstitutionName(user?.institucion || 'No asignada');
          return;
        }
        const found = insts.find(i => String(i._id) === String(instId) || i.nombre === instId);
        if (found) setInstitutionName(found.nombre);
        else setInstitutionName(typeof instId === 'string' ? instId : (user?.institucion || 'No asignada'));
      } catch (e) {
        console.warn('Could not load institution name:', e);
      }
    };

    fetchInstitutionName();
  }, [user]);

  useEffect(() => {
    const loadProfileData = async () => {
      if (!user?._id && !user?.id) return;
      const studentId = user._id || user.id;
      try {
        const [gradesRes, instRes, rulesRes] = await Promise.all([
          gradeService.getByStudent(studentId),
          institutionService.getAll().catch(() => ({ data: [] })),
          conversionService.getAllRules().catch(() => ({ data: [] }))
        ]);
        const subjList = gradesRes.data || [];
        const mapped = subjList.map((s, idx) => {
          const comps = [];
          if (s.notas) {
            if (s.notas.primer_parcial !== null) comps.push({ tipo: 'Primer Parcial', valor: s.notas.primer_parcial });
            if (s.notas.segundo_parcial !== null) comps.push({ tipo: 'Segundo Parcial', valor: s.notas.segundo_parcial });
            if (s.notas.final !== null) comps.push({ tipo: 'Final', valor: s.notas.final });
            if (s.notas.previo !== null) comps.push({ tipo: 'Previo', valor: s.notas.previo });
          }
          let notaFinal = null;
          if (s.notas?.final != null) notaFinal = s.notas.final;
          else if (s.notas?.previo != null) notaFinal = s.notas.previo;
          else if (s.estado?.startsWith?.('APROBADO') || s.estado === 'REPROBADO') notaFinal = s.notas?.final || s.notas?.previo;
          return {
            materia_id: s.materia_id, id: idx,
            codigo: s.materia_codigo || 'N/A',
            nombre: s.materia_nombre || 'Materia Desconocida',
            estado: s.estado || 'CURSANDO',
            nota: notaFinal,
            es_equivalencia: s.es_equivalencia || s.estado?.includes?.('EQUIVALENCIA'),
            nota_original: s.nota_original,
            materia_origen_nombre: s.materia_origen_nombre,
            metodo_conversion: s.metodo_conversion,
            fecha_conversion: s.fecha_conversion,
            componentes: comps,
            profesor: 'Sin asignar',
            anio: s.anio || 'Sin fecha',
            fecha_cierre: s.fecha_cierre || null
          };
        });
        setSubjects(mapped);
        setInstitutions(instRes.data || []);
        const rules = rulesRes.data || [];
        setConversionRules(rules);
        if (rules.length > 0 && !rules.find(r => r.codigo_regla === selectedRule)) setSelectedRule(rules[0].codigo_regla);
        setSelectedInstitution(user?.institucion_id || user?.institucion || '');
      } catch (err) {
        console.error('Error loading profile:', err);
      } finally {
        setSubjectsLoading(false);
      }
    };
    loadProfileData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?._id, user?.id]);

  const handleDescargarAnalitico = async () => {
    const studentId = user?._id || user?.id;
    if (!studentId) return;
    await descargarCertificadoAnalitico(reportService, studentId, user, setReportLoading);
  };

  const handleChangeInstitution = async () => {
    if (!selectedInstitution) return;
    const studentId = user?._id || user?.id;
    if (!studentId) return;
    try {
      setLoading(true);
      const result = await studentService.cambiarInstitucion(studentId, selectedInstitution, selectedRule);
      const res = await studentService.getById(studentId);
      const inst = institutions.find(i => String(i._id) === String(selectedInstitution));
      const updatedUser = { ...user, ...res.data, institucion_id: selectedInstitution };
      if (inst) updatedUser.institucion = inst.nombre;
      localStorage.setItem('user', JSON.stringify(updatedUser));
      if (onUpdate) onUpdate(updatedUser);
      setSuccessMessage(result.data?.total_homologadas > 0
        ? `Institución cambiada. ${result.data.total_homologadas} materia(s) aprobada(s) por equivalencia.`
        : 'Institución cambiada correctamente');
      setSelectedInstitution('');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setErrorMessage(err.response?.data?.error || 'Error al cambiar institución');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Mi Perfil</h2>
        <div className="profile-header-actions">
          <button className="btn-download-analitico" onClick={handleDescargarAnalitico} disabled={reportLoading}>
            {reportLoading ? 'Generando...' : 'Descargar analítico'}
          </button>
          {!isEditing ? (
            <button className="btn-edit-profile" onClick={() => setIsEditing(true)}>
              Editar Perfil
            </button>
          ) : (
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn-cancel" onClick={() => {
              setIsEditing(false);
              setEditedData({
                nombre: user?.nombre || '',
                apellido: user?.apellido || '',
                email: user?.email || '',
                legajo: user?.legajo || ''
              });
            }}>
              Cancelar
            </button>
            <button className="btn-save" onClick={handleSave} disabled={loading}>
              {loading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        )}
        </div>
      </div>

      {successMessage && <div className="success-message">{successMessage}</div>}
      {errorMessage && <div className="error-message">{errorMessage}</div>}

      <div className="profile-details">
        <div className="detail-card">
          <h3>Información Personal</h3>
          {isEditing ? (
            <div className="edit-form">
              <div className="form-group">
                <label>Nombre *</label>
                <input
                  type="text"
                  value={editedData.nombre}
                  onChange={(e) => setEditedData({...editedData, nombre: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Apellido *</label>
                <input
                  type="text"
                  value={editedData.apellido}
                  onChange={(e) => setEditedData({...editedData, apellido: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Email *</label>
                <input
                  type="email"
                  value={editedData.email}
                  onChange={(e) => setEditedData({...editedData, email: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Legajo</label>
                <input
                  type="text"
                  value={editedData.legajo}
                  onChange={(e) => setEditedData({...editedData, legajo: e.target.value})}
                />
              </div>
            </div>
          ) : (
            <>
              <div className="detail-row">
                <span>Nombre:</span>
                <strong>{user?.nombre || 'N/A'}</strong>
              </div>
              <div className="detail-row">
                <span>Apellido:</span>
                <strong>{user?.apellido || 'N/A'}</strong>
              </div>
              <div className="detail-row">
                <span>Email:</span>
                <strong>{user?.email || 'N/A'}</strong>
        <div className="detail-card change-institution-section">
          <h3>Cambiar Institución</h3>
          <p><strong>Institución actual:</strong> {institutionName || user?.institucion || 'No asignada'}</p>
          <div className="change-institution-inline">
            <select value={selectedInstitution} onChange={e => setSelectedInstitution(e.target.value)}>
              <option value="">-- Seleccione destino --</option>
              {institutions.filter(i => String(i._id) !== String(user?.institucion_id) && String(i._id) !== String(user?.institucion)).map(inst => (
                <option key={inst._id} value={inst._id}>{inst.nombre}</option>
              ))}
            </select>
            <select value={selectedRule} onChange={e => setSelectedRule(e.target.value)}>
              {conversionRules.length > 0 ? conversionRules.map(r => (
                <option key={r.codigo_regla} value={r.codigo_regla}>{r.nombre || r.codigo_regla}</option>
              )) : <option value="AR_TO_US">AR_TO_US</option>}
            </select>
            <button className="btn-confirm-small" onClick={handleChangeInstitution} disabled={!selectedInstitution || loading}>
              {loading ? 'Cambiando...' : 'Cambiar'}
            </button>
          </div>
        </div>

              </div>
              <div className="detail-row">
                <span>Legajo:</span>
                <strong>{user?.legajo || 'N/A'}</strong>
              </div>
              <div className="detail-row">
                <span>Rol:</span>
                <strong>{user?.rol || 'Estudiante'}</strong>
              </div>
              <div className="detail-row">
                <span>Institución:</span>
                <strong>{institutionName || user?.institucion || 'No asignada'}</strong>
              </div>
            </>
          )}
        </div>

        <div className="detail-card">
          <h3>Información Académica</h3>
          <div className="detail-row">
            <span>Promedio General:</span>
            <strong>{stats?.averageGrade || '0'}</strong>
          </div>
          <div className="detail-row">
            <span>Materias Cursando:</span>
            <strong>{stats?.inProgress || '0'}</strong>
          </div>
          <div className="detail-row">
            <span>Materias Aprobadas:</span>
            <strong>{stats?.passedSubjects || '0'}</strong>
          </div>
          <div className="detail-row">
            <span>Total de Materias:</span>
            <strong>{stats?.totalSubjects || '0'}</strong>
        <div className="detail-card change-institution-section">
          <h3>Cambiar Institución</h3>
          <p><strong>Institución actual:</strong> {institutionName || user?.institucion || 'No asignada'}</p>
          <div className="change-institution-inline">
            <select value={selectedInstitution} onChange={e => setSelectedInstitution(e.target.value)}>
              <option value="">-- Seleccione destino --</option>
              {institutions.filter(i => String(i._id) !== String(user?.institucion_id) && String(i._id) !== String(user?.institucion)).map(inst => (
                <option key={inst._id} value={inst._id}>{inst.nombre}</option>
              ))}
            </select>
            <select value={selectedRule} onChange={e => setSelectedRule(e.target.value)}>
              {conversionRules.length > 0 ? conversionRules.map(r => (
                <option key={r.codigo_regla} value={r.codigo_regla}>{r.nombre || r.codigo_regla}</option>
              )) : <option value="AR_TO_US">AR_TO_US</option>}
            </select>
            <button className="btn-confirm-small" onClick={handleChangeInstitution} disabled={!selectedInstitution || loading}>
              {loading ? 'Cambiando...' : 'Cambiar'}
            </button>
          </div>
        </div>

          </div>
        </div>

        <div className="detail-card historial-detallado-section">
          <h3>📚 Historial Académico Detallado</h3>
          {subjectsLoading ? (
            <p className="trajectory-loading">Cargando materias...</p>
          ) : subjects.length === 0 ? (
            <p className="trajectory-empty">No hay materias registradas.</p>
          ) : (
            <div className="historial-cards">
              {subjects.map(subject => (
                <div key={subject.id} className="subject-detail-card-mini">
                  <div className="subject-detail-header-mini">
                    <div>
                      <h4>{subject.nombre}</h4>
                      <p className="code-label">{subject.codigo}</p>
                    </div>
                    <div className="subject-meta-mini">
                      <span className={`status-badge ${subject.es_equivalencia ? 'equivalencia' : (subject.estado || '').toLowerCase()}`}>
                        {subject.es_equivalencia ? 'Equivalencia' : (subject.estado || 'N/A')}
                      </span>
                      {subject.nota != null && <span className="grade-badge-mini">{subject.nota}</span>}
                      {subject.es_equivalencia && subject.nota_original != null && (
                        <span className="orig-badge">Orig: {subject.nota_original}</span>
                      )}
                    </div>
                  </div>
                  {subject.componentes?.length > 0 && (
                    <div className="componentes-mini">
                      {subject.componentes.map((c, i) => (
                        <span key={i}>{c.tipo}: {c.valor}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="detail-card trajectory-section">
          <h3>📈 Trayectoria Académica</h3>
          {trajectoryLoading ? (
            <p className="trajectory-loading">Cargando trayectoria...</p>
          ) : trajectory ? (
            <>
              <div className="trajectory-block">
                <h4>Materias en curso ({trajectory.materias_en_curso?.length || 0})</h4>
                {(trajectory.materias_en_curso || []).length === 0 ? (
                  <p className="trajectory-empty">Ninguna</p>
                ) : (
                  <ul className="trajectory-list">
                    {(trajectory.materias_en_curso || []).map((m, idx) => (
                      <li key={idx} className="trajectory-item"><strong>{m.nombre}</strong> ({m.codigo}) — Año {m.anio}</li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="trajectory-block">
                <h4>Materias aprobadas ({trajectory.materias_aprobadas?.length || 0})</h4>
                {(trajectory.materias_aprobadas || []).length === 0 ? (
                  <p className="trajectory-empty">Ninguna</p>
                ) : (
                  <ul className="trajectory-list">
                    {(trajectory.materias_aprobadas || []).map((m, idx) => (
                      <li key={idx} className="trajectory-item approved">
                        <strong>{m.nombre}</strong> ({m.codigo}) — Nota: {m.nota_final ?? m.notas?.final ?? m.notas?.previo ?? 'N/A'}
                        {m.es_equivalencia && <span className="equivalencia-badge" title="Aprobada por equivalencia"> (Equivalencia)</span>}
                        {m.nota_original != null && m.es_equivalencia && <span> — Orig: {m.nota_original}</span>}
                        {m.materia_origen_nombre && m.es_equivalencia && <span> ← {m.materia_origen_nombre}</span>}
                        {m.metodo_conversion && m.es_equivalencia && <span className="equivalencia-metodo"> Regla: {m.metodo_conversion}</span>}
                        {m.fecha_conversion && m.es_equivalencia && (
                          <span className="equivalencia-fecha"> {new Date(m.fecha_conversion).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
                        )}
                        {' '}— Año {m.anio}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="trajectory-block">
                <h4>Materias reprobadas ({trajectory.materias_reprobadas?.length || 0})</h4>
                {(trajectory.materias_reprobadas || []).length === 0 ? (
                  <p className="trajectory-empty">Ninguna</p>
                ) : (
                  <ul className="trajectory-list">
                    {(trajectory.materias_reprobadas || []).map((m, idx) => (
                      <li key={idx} className="trajectory-item reprobada"><strong>{m.nombre}</strong> ({m.codigo}) — Nota: {m.nota_final} — Año {m.anio}</li>
                    ))}
                  </ul>
                )}
              </div>
              {trajectory.recursadas && trajectory.recursadas.length > 0 && (
                <div className="trajectory-block">
                  <h4>Recursadas</h4>
                  <ul className="trajectory-list">
                    {trajectory.recursadas.map((r, idx) => (
                      <li key={idx} className="trajectory-item"><strong>{r.nombre}</strong> ({r.codigo}) — {r.veces} veces</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className="trajectory-empty">No se pudo cargar la trayectoria.</p>
          )}
        </div>
      </div>
    </div>
  );
};

const StudentEnrollment = ({ user, onBack, onEnroll }) => {
  const [availableSubjects, setAvailableSubjects] = useState([]);
  const [enrolledSubjects, setEnrolledSubjects] = useState([]);
  const [newEnrolled, setNewEnrolled] = useState([]);
  const [loading, setLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [institutions, setInstitutions] = useState([]);
  const [userInstitution, setUserInstitution] = useState(null);
  const [newSubject, setNewSubject] = useState({
    codigo: '',
    nombre: '',
    nivel: 'GRADO',
    institucion_id: ''
  });
  
  // Verificar si el usuario es admin
  const isAdmin = user?.rol === 'admin';

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Cargar datos del usuario para obtener su institución
      let currentUser = user;
      let userInstId = user?.institucion_id || user?.institucion;
      
      if (user?._id || user?.id) {
        try {
          const userRes = await studentService.getById(user._id || user.id);
          if (userRes.data) {
            currentUser = userRes.data;
            userInstId = currentUser.institucion_id || currentUser.institucion || userInstId;
            setUserInstitution(userInstId);
          }
        } catch (e) {
          console.warn('Could not load user details:', e);
          if (userInstId) {
            setUserInstitution(userInstId);
          }
        }
      } else if (userInstId) {
        setUserInstitution(userInstId);
      }

      const [allSubjectsRes, enrolledRes, institutionsRes] = await Promise.all([
        subjectService.getAll(),
        user?._id || user?.id ? subjectService.getByStudent(user._id || user.id) : Promise.resolve({ data: [] }),
        institutionService.getAll().catch(() => ({ data: [] }))
      ]);

      const allSubjects = allSubjectsRes.data || [];
      const enrolled = enrolledRes.data || [];
      const insts = institutionsRes.data || [];
      
      setEnrolledSubjects(enrolled);
      
      // Filtrar materias disponibles
      const materiasCursadasIds = enrolled.map(e => e.materia_id);
      let filtered = allSubjects.filter(s => !materiasCursadasIds.includes(s._id));
      
      // Si el usuario tiene institución, filtrar por institución (solo estudiantes, no admin)
      if (userInstitution && !isAdmin) {
        filtered = filtered.filter(s => {
          const subjInstId = s.institucion_id?._id || s.institucion_id;
          return String(subjInstId) === String(userInstitution);
        });
      }
      
      setAvailableSubjects(filtered);
      setInstitutions(insts);
    } catch (error) {
      console.error('Error loading subjects:', error);
      const errorMsg = error.response?.data?.error || error.message;
      if (error.message.includes('Network') || error.code === 'ECONNREFUSED') {
        setErrorMessage('Error de conexión. Verifica que el backend esté corriendo en http://localhost:5000');
      } else {
        setErrorMessage('Error al cargar materias: ' + errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEnroll = async (subject) => {
    try {
      const studentId = user?._id || user?.id;
      if (!studentId) {
        setErrorMessage('No se pudo identificar al estudiante');
        return;
      }

      await gradingOperations.inscribirAlumno({
        estudiante_id: studentId,
        materia_id: subject._id,
        anio_lectivo: new Date().getFullYear()
      });

      setNewEnrolled([...newEnrolled, subject]);
      setSuccessMessage(`¡Te inscribiste en ${subject.nombre}!`);
      setErrorMessage('');
      setTimeout(() => {
        setSuccessMessage('');
        if (onEnroll) onEnroll();
      }, 3000);
    } catch (error) {
      console.error('Error enrolling:', error);
      const errorMsg = error.response?.data?.error || error.message;
      if (error.message.includes('Network') || error.code === 'ECONNREFUSED') {
        setErrorMessage('Error de conexión. Verifica que el backend esté corriendo.');
      } else if (error.response?.status === 404) {
        setErrorMessage('Estudiante o materia no encontrada. Verifica que existan en el sistema.');
      } else {
        setErrorMessage('Error al inscribirse: ' + errorMsg);
      }
      setSuccessMessage('');
    }
  };

  const handleRemove = (subjectId) => {
    setNewEnrolled(newEnrolled.filter(s => s._id !== subjectId));
  };

  const handleConfirm = async () => {
    setSuccessMessage('Inscripciones confirmadas');
    if (onEnroll) onEnroll();
    setTimeout(() => {
      setSuccessMessage('');
      onBack();
    }, 2000);
  };

  const handleCreateSubject = async (e) => {
    e.preventDefault();
    try {
      if (!newSubject.codigo || !newSubject.nombre) {
        setErrorMessage('Código y nombre son requeridos');
        return;
      }

      await subjectService.create(newSubject);
      setSuccessMessage(`Materia ${newSubject.nombre} creada exitosamente`);
      setErrorMessage('');
      
      setNewSubject({
        codigo: '',
        nombre: '',
        nivel: 'GRADO',
        institucion_id: institutions[0]?._id || ''
      });
      setShowCreateForm(false);
      
      await loadData();
      
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Error creating subject:', error);
      const errorMsg = error.response?.data?.error || error.message;
      if (error.message.includes('Network') || error.code === 'ECONNREFUSED') {
        setErrorMessage('Error de conexión. Verifica que el backend esté corriendo.');
      } else {
        setErrorMessage('Error al crear materia: ' + errorMsg);
      }
      setSuccessMessage('');
    }
  };

  if (loading) {
    return (
      <div className="menu-content">
        <div className="content-header">
          <button className="back-btn" onClick={onBack}>
            <ArrowLeft size={20} />
          </button>
          <h2>Inscribirse a Materias</h2>
        </div>
        <div className="loading-container">Cargando materias...</div>
      </div>
    );
  }

  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Inscribirse a Materias</h2>
        {isAdmin && (
          <button 
            className="btn-create-subject" 
            onClick={() => setShowCreateForm(!showCreateForm)}
            style={{ marginLeft: 'auto' }}
          >
            <Plus size={16} /> {showCreateForm ? 'Cancelar' : 'Crear Materia'}
          </button>
        )}
      </div>

      {successMessage && <div className="success-message">{successMessage}</div>}
      {errorMessage && <div className="error-message">{errorMessage}</div>}

      {showCreateForm && (
        <div className="create-subject-form">
          <h3>Crear Nueva Materia</h3>
          <form onSubmit={handleCreateSubject}>
            <div className="form-row">
              <div className="form-group">
                <label>Código *</label>
                <input
                  type="text"
                  value={newSubject.codigo}
                  onChange={(e) => setNewSubject({...newSubject, codigo: e.target.value})}
                  placeholder="Ej: MAT-101"
                  required
                />
              </div>
              <div className="form-group">
                <label>Nombre *</label>
                <input
                  type="text"
                  value={newSubject.nombre}
                  onChange={(e) => setNewSubject({...newSubject, nombre: e.target.value})}
                  placeholder="Ej: Matemática I"
                  required
                />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Nivel</label>
                <select
                  value={newSubject.nivel}
                  onChange={(e) => setNewSubject({...newSubject, nivel: e.target.value})}
                >
                  <option value="GRADO">Grado</option>
                  <option value="POSTGRADO">Postgrado</option>
                  <option value="SECUNDARIO">Secundario</option>
                </select>
              </div>
              <div className="form-group">
                <label>Institución</label>
                <select
                  value={newSubject.institucion_id}
                  onChange={(e) => setNewSubject({...newSubject, institucion_id: e.target.value})}
                >
                  <option value="">Seleccionar...</option>
                  {institutions.map(inst => (
                    <option key={inst._id} value={inst._id}>{inst.nombre}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="form-actions">
              <button type="button" className="btn-cancel" onClick={() => setShowCreateForm(false)}>
                Cancelar
              </button>
              <button type="submit" className="btn-submit">
                Crear Materia
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="enrollment-container">
        <div className="available-subjects">
          <h3>Materias Disponibles ({availableSubjects.length})</h3>
          {userInstitution && !isAdmin && (
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '15px' }}>
              Mostrando materias de tu institución
            </p>
          )}
          <div className="subjects-list">
            {availableSubjects.length > 0 ? (
              availableSubjects.map(subject => (
                <div key={subject._id} className="subject-item">
                  <div className="subject-info">
                    <h4>{subject.nombre}</h4>
                    <p>{subject.codigo}</p>
                    <small>Nivel: {subject.nivel || 'N/A'}</small>
                    {subject.institucion_id && (
                      <small style={{ display: 'block', marginTop: '5px' }}>
                        Institución: {institutions.find(i => i._id === subject.institucion_id)?.nombre || 'N/A'}
                      </small>
                    )}
                  </div>
                  <button
                    className="btn-enroll"
                    onClick={() => handleEnroll(subject)}
                    disabled={newEnrolled.find(s => s._id === subject._id)}
                  >
                    {newEnrolled.find(s => s._id === subject._id) ? '✓ Inscrito' : 'Inscribirse'}
                  </button>
                </div>
              ))
            ) : (
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <p style={{ color: '#999', marginBottom: '15px' }}>
                  {userInstitution 
                    ? 'No hay materias disponibles de tu institución para inscribirse en este momento.'
                    : 'No hay materias disponibles para inscribirse. Contacta a un administrador para asignarte una institución.'}
                </p>
                {isAdmin && (
                  <button 
                    className="btn-create-subject" 
                    onClick={() => setShowCreateForm(true)}
                  >
                    <Plus size={16} /> Crear Nueva Materia
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {newEnrolled.length > 0 && (
          <div className="enrolled-subjects">
            <h3>Materias Seleccionadas ({newEnrolled.length})</h3>
            <div className="selected-list">
              {newEnrolled.map(subject => (
                <div key={subject._id} className="selected-item">
                  <div>
                    <strong>{subject.nombre}</strong>
                    <p>{subject.codigo}</p>
                  </div>
                  <button
                    className="btn-remove"
                    onClick={() => handleRemove(subject._id)}
                  >
                    Remover
                  </button>
                </div>
              ))}
            </div>
            <button className="btn-confirm" onClick={handleConfirm}>Confirmar Inscripción</button>
          </div>
        )}
      </div>
    </div>
  );
};

const ChangeInstitution = ({ user, onBack, onUpdate }) => {
  const [institutions, setInstitutions] = useState([]);
  const [conversionRules, setConversionRules] = useState([]);
  const [selectedRule, setSelectedRule] = useState('AR_TO_US');
  const [loading, setLoading] = useState(true);
  const [selectedInst, setSelectedInst] = useState(null);
  const [currentInstitution, setCurrentInstitution] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const studentId = user?._id || user?.id;
      
      const [institutionsRes, userRes, rulesRes] = await Promise.all([
        institutionService.getAll(),
        studentId ? studentService.getById(studentId) : Promise.resolve({ data: null }),
        conversionService.getAllRules().catch(() => ({ data: [] }))
      ]);

      const allInstitutions = institutionsRes.data || [];
      const rules = rulesRes.data || [];
      setInstitutions(allInstitutions);
      setConversionRules(rules);
      
      if (rules.length > 0 && !rules.find(r => r.codigo_regla === selectedRule)) {
        setSelectedRule(rules[0].codigo_regla);
      }
      
      let instId = null;
      if (userRes.data) {
        instId = userRes.data.institucion_id || userRes.data.institucion;
      }
      if (!instId && user) {
        instId = user.institucion_id || user.institucion;
      }

      if (instId) {
        const inst = allInstitutions.find(i => String(i._id) === String(instId) || i.nombre === instId);
        if (inst) setCurrentInstitution(inst);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      setErrorMessage('Error al cargar instituciones');
    } finally {
      setLoading(false);
    }
  };

  const handleChangeInstitution = async () => {
    if (!selectedInst) return;
    
    try {
      setSaving(true);
      setErrorMessage('');
      const studentId = user?._id || user?.id;
      
      if (!studentId) {
        setErrorMessage('No se pudo identificar al estudiante');
        return;
      }

      const result = await studentService.cambiarInstitucion(
        studentId,
        selectedInst._id,
        selectedRule
      );

      const res = await studentService.getById(studentId);
      const updatedUser = { 
        ...user, 
        ...res.data,
        institucion_id: selectedInst._id, 
        institucion: selectedInst.nombre,
        institucion_nombre: selectedInst.nombre
      };
      localStorage.setItem('user', JSON.stringify(updatedUser));

      const homologadas = result.data?.total_homologadas ?? result.data?.materias_homologadas?.length ?? 0;
      const msg = homologadas > 0
        ? `Institución cambiada a ${selectedInst.nombre}. ${homologadas} materia(s) aprobada(s) por equivalencia.`
        : `Institución cambiada a ${selectedInst.nombre} exitosamente`;
      setSuccessMessage(msg);
      setCurrentInstitution(selectedInst);
      setSelectedInst(null);
      
      if (onUpdate) {
        onUpdate(updatedUser);
      }
      
      setTimeout(() => {
        setSuccessMessage('');
        onBack();
      }, 2000);
    } catch (error) {
      console.error('Error changing institution:', error);
      setErrorMessage(error.response?.data?.error || 'Error al cambiar institución');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="menu-content">
        <div className="content-header">
          <button className="back-btn" onClick={onBack}>
            <ArrowLeft size={20} />
          </button>
          <h2>Cambiar Institución</h2>
        </div>
        <div className="loading-container">Cargando instituciones...</div>
      </div>
    );
  }

  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Cambiar Institución</h2>
      </div>

      {successMessage && <div className="success-message">{successMessage}</div>}
      {errorMessage && <div className="error-message">{errorMessage}</div>}

      <div className="institution-container">
        <div className="current-institution">
          <h3>Institución Actual</h3>
          <div className="inst-card current">
            <h4>{currentInstitution?.nombre || user?.institucion || 'No asignada'}</h4>
            <p>{currentInstitution?.codigo || ''}</p>
            <p className="status">Estado: {currentInstitution ? 'Activo' : 'Pendiente'}</p>
          </div>
        </div>

        <div className="available-institutions">
          <h3>Instituciones Disponibles</h3>
          <div className="institutions-grid">
            {institutions.length > 0 ? (
              institutions
                .filter(inst => {
                  const curr = currentInstitution?._id || user?.institucion_id || user?.institucion;
                  return String(inst._id) !== String(curr) && inst.nombre !== curr;
                })
                .map(inst => (
                  <div
                    key={inst._id}
                    className={`inst-card ${selectedInst?._id === inst._id ? 'selected' : ''}`}
                    onClick={() => setSelectedInst(inst)}
                  >
                    <h4>{inst.nombre}</h4>
                    <p>{inst.codigo}</p>
                    <p>{inst.pais || 'N/A'}</p>
                  </div>
                ))
            ) : (
              <p style={{ color: '#999', padding: '20px', textAlign: 'center' }}>
                No hay instituciones disponibles
              </p>
            )}
          </div>
        </div>

        {selectedInst && (
          <div className="change-confirmation">
            <h3>¿Cambiar a {selectedInst.nombre}?</h3>
            <p>Al cambiar de institución se aplicarán automáticamente las equivalencias de materias aprobadas y la conversión de notas.</p>
            <div className="form-group" style={{ marginBottom: '15px' }}>
              <label>Regla de conversión de notas</label>
              <select 
                value={selectedRule} 
                onChange={e => setSelectedRule(e.target.value)}
                style={{ width: '100%', padding: '8px', marginTop: '4px' }}
              >
                {conversionRules.map(r => (
                  <option key={r.codigo_regla} value={r.codigo_regla}>{r.nombre || r.codigo_regla}</option>
                ))}
              </select>
            </div>
            <div className="confirmation-buttons">
              <button className="btn-cancel" onClick={() => setSelectedInst(null)} disabled={saving}>
                Cancelar
              </button>
              <button className="btn-confirm" onClick={handleChangeInstitution} disabled={saving}>
                {saving ? 'Cambiando...' : 'Confirmar Cambio'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const ConvertGrades = ({ historial = [], user, onBack }) => {
  const [conversionRules, setConversionRules] = useState([]);
  const [selectedRule, setSelectedRule] = useState(null);
  const [converted, setConverted] = useState([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [calificaciones, setCalificaciones] = useState([]);

  useEffect(() => {
    loadCalificaciones();
  }, [user]);

  const loadCalificaciones = async () => {
    try {
      if (!user?._id && !user?.id) return;
      
      const studentId = String(user._id || user.id);
      const allGrades = await gradeService.getAll();
      
      // Filtramos asegurando que exista la nota y los IDs coincidan exactamente
      const userGrades = allGrades.data.filter(g => 
        String(g.estudiante_id) === studentId && 
        g.valor_original && 
        g.valor_original.nota !== undefined && 
        g.valor_original.nota !== null
      );
      
      console.log("Calificaciones encontradas en Mongo:", userGrades);
      setCalificaciones(userGrades);
    } catch (error) {
      console.error('Error loading calificaciones:', error);
    }
  };

  // Cruzamos la información del historial de Neo4j con la calificación real de Mongo
  // Soporta notas numéricas (AR 1-10, DE 1-6, US GPA) y letras (UK A*-F, US A-F)
  const grades = historial
    .filter(h => (h.notas?.final !== null && h.notas?.final !== undefined) || (h.notas?.previo !== null && h.notas?.previo !== undefined))
    .map(h => {
      const notaAConvertir = (h.notas?.final !== null && h.notas?.final !== undefined) ? h.notas.final : h.notas?.previo;
      const materiaIdNeo = String(h.materia_id);
      const numVal = parseFloat(notaAConvertir);
      const notaVal = (typeof notaAConvertir === 'number' || !isNaN(numVal)) ? (numVal || notaAConvertir) : notaAConvertir;

      const calificacionMongo = calificaciones.find(c => {
        const isSameMateria = String(c.materia_id) === materiaIdNeo;
        const isFinal = ['FINAL', 'PREVIO', 'FINAL_PROJECT'].includes(c.valor_original?.tipo);
        return isSameMateria && isFinal;
      }) || calificaciones.find(c => String(c.materia_id) === materiaIdNeo); 

      return {
        calificacion_id: calificacionMongo ? calificacionMongo._id : null,
        materia_id: h.materia_id,
        materia: h.materia_nombre || 'Materia Desconocida',
        nota: notaVal,
        codigo: h.materia_codigo || '',
        tipo: calificacionMongo?.valor_original?.tipo || 'FINAL'
      };
    })
    .filter(g => g.nota !== null && g.nota !== undefined && g.nota !== '');

  useEffect(() => {
    const loadRules = async () => {
      try {
        const res = await conversionService.getAllRules();
        const rules = res.data || [];
        setConversionRules(rules);
      } catch (error) {
        console.error('Error cargando reglas de conversión:', error);
        setConversionRules([]);
      } finally {
        setLoading(false);
      }
    };
    loadRules();
  }, []);

  const handleSelectRule = (rule) => {
    setSelectedRule(rule);
    const convertedGrades = grades.map(grade => {
      const mapping = rule.mapeo.find(m => {
        const orig = m.nota_origen;
        const gradeVal = grade.nota;
        if (typeof orig === 'number' && (typeof gradeVal === 'number' || !isNaN(parseFloat(gradeVal)))) {
          return Math.abs(orig - parseFloat(gradeVal)) < 0.05;
        }
        const origStr = String(orig).toUpperCase().trim();
        const valStr = String(gradeVal).toUpperCase().trim();
        return origStr === valStr;
      });
      return {
        ...grade,
        convertida: mapping ? mapping.nota_destino : 'N/A'
      };
    });
    setConverted(convertedGrades);
  };

  const handleApplyConversion = async (grade) => {
    if (!selectedRule) {
      alert('Selecciona primero una regla de conversión.');
      return;
    }

    if (!grade.calificacion_id) {
      alert('No se encontró el registro en MongoDB. Crea el registro antes de aplicar la conversión.');
      return;
    }
    
    try {
      setApplying(true);
      await conversionService.applyConversion({
        calificacion_id: grade.calificacion_id,
        codigo_regla: selectedRule.codigo_regla
      });
      
      alert(`Conversión aplicada para ${grade.materia}. La conversión ha sido guardada.`);
      
      await loadCalificaciones();
    } catch (error) {
      console.error('Error applying conversion:', error);
      alert('Error al aplicar conversión: ' + (error.response?.data?.error || error.message));
    } finally {
      setApplying(false);
    }
  };

  const handleCreateCalificacion = async (item) => {
    try {
      setApplying(true);
      const studentId = String(user._id || user.id);
      // Construir payload mínimo para crear la calificación en Mongo
      const payload = {
        estudiante_id: studentId,
        materia_id: String(item.materia_id),
        valor_original: {
          tipo: item.tipo || 'FINAL',
          nota: item.nota
        }
      };

      await gradeService.create(payload);
      // Recargar calificaciones y recalcular convertidas
      await loadCalificaciones();
      if (selectedRule) handleSelectRule(selectedRule);
      alert(`Registro creado en Mongo para ${item.materia}. Ahora puedes aplicar la conversión.`);
    } catch (error) {
      console.error('Error creando calificación:', error);
      alert('Error al crear calificación: ' + (error.response?.data?.error || error.message));
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className="menu-content">
        <div className="content-header">
          <button className="back-btn" onClick={onBack}>
            <ArrowLeft size={20} />
          </button>
          <h2>Convertir Notas</h2>
        </div>
        <div className="loading-container">Cargando reglas de conversión...</div>
      </div>
    );
  }

  if (grades.length === 0) {
    return (
      <div className="menu-content">
        <div className="content-header">
          <button className="back-btn" onClick={onBack}>
            <ArrowLeft size={20} />
          </button>
          <h2>Convertir Notas</h2>
        </div>
        <div className="no-data">
          <p>No tienes notas finales para convertir</p>
        </div>
      </div>
    );
  }

  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Convertir Notas</h2>
      </div>

      <div className="conversion-container">
        <div className="system-selector">
          <h3>Selecciona una Regla de Conversión</h3>
          <p className="conversion-legend">
            Sistemas: Argentina (1-10) · Reino Unido (A*-F) · Estados Unidos (A-F, GPA 0-4) · Alemania (1.0-6.0)
          </p>
          <div className="system-buttons">
            {conversionRules.map((rule) => (
              <button
                key={rule.codigo_regla}
                className={`system-btn ${selectedRule?.codigo_regla === rule.codigo_regla ? 'active' : ''}`}
                onClick={() => handleSelectRule(rule)}
              >
                {rule.nombre}
              </button>
            ))}
          </div>
        </div>

        {converted.length > 0 && (
          <div className="conversion-results">
            <h3>Tus Notas Convertidas</h3>
            <table className="conversion-table">
              <thead>
                <tr>
                  <th>Materia</th>
                  <th>Código</th>
                  <th>Nota Original</th>
                  <th>Nota Convertida</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {converted.map((item, idx) => (
                  <tr key={idx}>
                    <td>{item.materia}</td>
                    <td>{item.codigo}</td>
                    <td className="original">{item.nota}</td>
                    <td className="converted">
                      {typeof item.convertida === 'number'
                        ? (Number.isInteger(item.convertida) ? item.convertida : item.convertida.toFixed(2))
                        : item.convertida}
                    </td>
                    <td>
                      {item.calificacion_id ? (
                        <button 
                          className="btn-apply"
                          onClick={() => handleApplyConversion(item)}
                          disabled={applying}
                        >
                          Aplicar
                        </button>
                      ) : (
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <button className="btn-apply" disabled style={{ opacity: 0.6 }}>
                            Aplicar
                          </button>
                          <button className="btn-create" onClick={() => handleCreateCalificacion(item)} disabled={applying}>
                            Crear registro
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!selectedRule && (
          <div className="no-system">
            <p>Selecciona una regla de conversión para ver tus notas convertidas</p>
          </div>
        )}
      </div>
    </div>
  );
};

export { StudentProfile, StudentEnrollment, ChangeInstitution, ConvertGrades };