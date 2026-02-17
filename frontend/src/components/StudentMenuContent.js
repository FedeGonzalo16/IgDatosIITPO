import React, { useState, useEffect } from 'react';
import { ArrowLeft, Plus, X, Edit } from 'lucide-react';
import { 
  subjectService, 
  gradingOperations, 
  conversionService, 
  institutionService, 
  studentService, 
  gradeService,
  trajectoryService
} from '../services/api';
import './StudentMenuContent.css';

const StudentProfile = ({ user, onBack, stats, onUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState({
    nombre: user?.nombre || '',
    apellido: user?.apellido || '',
    email: user?.email || '',
    legajo: user?.legajo || ''
  });
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [trajectory, setTrajectory] = useState(null);
  const [trajectoryLoading, setTrajectoryLoading] = useState(true);

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

  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Mi Perfil</h2>
        <div className="profile-header-actions">
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
              </div>
              <div className="detail-row">
                <span>Legajo:</span>
                <strong>{user?.legajo || 'N/A'}</strong>
              </div>
              <div className="detail-row">
                <span>Rol:</span>
                <strong>{user?.rol || 'Estudiante'}</strong>
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
          </div>
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
                      <li key={idx} className="trajectory-item approved"><strong>{m.nombre}</strong> ({m.codigo}) — Nota: {m.nota_final} — Año {m.anio}</li>
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
          // Usar institución del user si está disponible
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
      
      // Filtrar materias disponibles:
      // 1. Que no esté cursando ni haya cursado
      // 2. Que sean de la misma institución del usuario (si tiene institución)
      const materiasCursadasIds = enrolled.map(e => e.materia_id);
      let filtered = allSubjects.filter(s => 
        !materiasCursadasIds.includes(s._id)
      );
      
      // Si el usuario tiene institución, filtrar por institución (solo estudiantes, no admin)
      if (userInstitution && !isAdmin) {
        filtered = filtered.filter(s => {
          const subjInstId = s.institucion_id?._id || s.institucion_id;
          const userInstIdStr = String(userInstitution);
          const subjInstIdStr = String(subjInstId);
          return subjInstIdStr === userInstIdStr;
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
    // Las inscripciones ya se hicieron individualmente
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

      const response = await subjectService.create(newSubject);
      setSuccessMessage(`Materia ${newSubject.nombre} creada exitosamente`);
      setErrorMessage('');
      
      // Resetear formulario
      setNewSubject({
        codigo: '',
        nombre: '',
        nivel: 'GRADO',
        institucion_id: institutions[0]?._id || ''
      });
      setShowCreateForm(false);
      
      // Recargar materias
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
                    : 'No hay materias disponibles para inscribirse en este momento. Contacta a un administrador para asignarte una institución.'}
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
      const [institutionsRes, userRes] = await Promise.all([
        institutionService.getAll(),
        user?._id || user?.id ? studentService.getById(user._id || user.id) : Promise.resolve({ data: null })
      ]);

      setInstitutions(institutionsRes.data || []);
      
      if (userRes.data) {
        const instId = userRes.data.institucion_id || userRes.data.institucion;
        if (instId) {
          const inst = institutionsRes.data.find(i => i._id === instId);
          setCurrentInstitution(inst);
        }
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

      // Actualizar estudiante con nueva institución
      await studentService.update(studentId, {
        institucion_id: selectedInst._id
      });

      // Actualizar usuario en localStorage
      const updatedUser = { ...user, institucion_id: selectedInst._id, institucion: selectedInst.nombre };
      localStorage.setItem('user', JSON.stringify(updatedUser));

      setSuccessMessage(`Institución cambiada a ${selectedInst.nombre} exitosamente`);
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
            <p className="status">Estado: Activo</p>
          </div>
        </div>

        <div className="available-institutions">
          <h3>Instituciones Disponibles</h3>
          <div className="institutions-grid">
            {institutions.length > 0 ? (
              institutions.map(inst => (
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
            <p>Al cambiar de institución, solo podrás inscribirte a materias de la nueva institución.</p>
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

  // Cargar calificaciones del usuario desde MongoDB
  useEffect(() => {
    loadCalificaciones();
  }, [user]);

  const loadCalificaciones = async () => {
    try {
      if (!user?._id && !user?.id) return;
      
      const studentId = user._id || user.id;
      const response = await gradeService.getByStudent(studentId);
      
      // Obtener calificaciones completas desde MongoDB
      const allGrades = await gradeService.getAll();
      const userGrades = allGrades.data.filter(g => 
        g.estudiante_id === studentId && 
        g.valor_original?.nota
      );
      
      setCalificaciones(userGrades);
    } catch (error) {
      console.error('Error loading calificaciones:', error);
    }
  };

  // Extraer notas del historial (Neo4j) y calificaciones (MongoDB)
  const grades = [
    ...historial
      .filter(h => h.notas?.final)
      .map(h => ({
        calificacion_id: null,
        materia_id: h.materia_id,
        materia: h.materia_nombre || 'Materia',
        nota: parseFloat(h.notas.final),
        codigo: h.materia_codigo || '',
        tipo: 'FINAL',
        fuente: 'historial'
      })),
    ...calificaciones.map(c => ({
      calificacion_id: c._id,
      materia_id: c.materia_id,
      materia: 'Materia', // Se puede enriquecer después
      nota: parseFloat(c.valor_original?.nota) || 0,
      codigo: '',
      tipo: c.valor_original?.tipo || 'FINAL',
      fuente: 'calificacion'
    }))
  ].filter(g => !isNaN(g.nota) && g.nota > 0);

  useEffect(() => {
    // En una implementación real, cargaríamos las reglas desde el backend
    // Por ahora usamos reglas predefinidas
    setConversionRules([
      { codigo_regla: 'AR_TO_US', nombre: 'Argentina a Estados Unidos', mapeo: [
        { nota_origen: 10, nota_destino: 'A' },
        { nota_origen: 9, nota_destino: 'A' },
        { nota_origen: 8, nota_destino: 'B' },
        { nota_origen: 7, nota_destino: 'C' },
        { nota_origen: 6, nota_destino: 'D' },
        { nota_origen: 4, nota_destino: 'F' }
      ]},
      { codigo_regla: 'AR_TO_4', nombre: 'Argentina a Escala 0-4', mapeo: [
        { nota_origen: 10, nota_destino: 4.0 },
        { nota_origen: 9, nota_destino: 3.5 },
        { nota_origen: 8, nota_destino: 3.0 },
        { nota_origen: 7, nota_destino: 2.5 },
        { nota_origen: 6, nota_destino: 2.0 },
        { nota_origen: 4, nota_destino: 1.0 }
      ]}
    ]);
    setLoading(false);
  }, []);

  const handleSelectRule = (rule) => {
    setSelectedRule(rule);
    const convertedGrades = grades.map(grade => {
      const mapping = rule.mapeo.find(m => 
        Math.abs(parseFloat(m.nota_origen) - grade.nota) < 0.5
      );
      return {
        ...grade,
        convertida: mapping ? mapping.nota_destino : 'N/A'
      };
    });
    setConverted(convertedGrades);
  };

  const handleApplyConversion = async (grade) => {
    if (!selectedRule || !grade.calificacion_id) {
      alert('Esta nota no puede ser convertida (no tiene ID de calificación en MongoDB)');
      return;
    }
    
    try {
      setApplying(true);
      await conversionService.applyConversion({
        calificacion_id: grade.calificacion_id,
        codigo_regla: selectedRule.codigo_regla
      });
      
      alert(`Conversión aplicada para ${grade.materia}. La conversión ha sido guardada.`);
      
      // Recargar calificaciones para ver la conversión aplicada
      await loadCalificaciones();
    } catch (error) {
      console.error('Error applying conversion:', error);
      alert('Error al aplicar conversión: ' + (error.response?.data?.error || error.message));
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
                        ? item.convertida.toFixed(2)
                        : item.convertida}
                    </td>
                    <td>
                      <button 
                        className="btn-apply"
                        onClick={() => handleApplyConversion(item)}
                        disabled={applying}
                      >
                        Aplicar
                      </button>
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
