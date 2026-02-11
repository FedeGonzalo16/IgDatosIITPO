import React from 'react';
import { ArrowLeft } from 'lucide-react';
import './StudentMenuContent.css';

const StudentProfile = ({ user, onBack, stats }) => {
  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Mi Perfil</h2>
      </div>

      <div className="profile-details">
        <div className="detail-card">
          <h3>Información Personal</h3>
          <div className="detail-row">
            <span>Nombre:</span>
            <strong>{user?.nombre || 'N/A'}</strong>
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
      </div>
    </div>
  );
};

const StudentEnrollment = ({ subjects = [], onBack }) => {
  const allAvailableSubjects = [
    { id: 1, codigo: 'ART-001', nombre: 'Arte y Cultura', profesor: 'Lic. Pérez', estudiantes: 25 },
    { id: 2, codigo: 'DEP-001', nombre: 'Educación Física', profesor: 'Prof. García', estudiantes: 30 },
    { id: 3, codigo: 'MUS-001', nombre: 'Música', profesor: 'Mtra. López', estudiantes: 20 },
    { id: 4, codigo: 'TEC-001', nombre: 'Informática Avanzada', profesor: 'Ing. Martínez', estudiantes: 28 },
    { id: 5, codigo: 'GEO-001', nombre: 'Geografía Económica', profesor: 'Prof. Vázquez', estudiantes: 22 },
  ];

  const enrolled = subjects?.filter(s => s.estado === 'cursando' || s.estado === 'aprobada') || [];
  const availableSubjects = allAvailableSubjects.filter(
    as => !enrolled.some(es => es.codigo === as.codigo)
  );

  const [newEnrolled, setNewEnrolled] = React.useState([]);
  const [successMessage, setSuccessMessage] = React.useState('');

  const handleEnroll = (subject) => {
    if (!newEnrolled.find(s => s.id === subject.id)) {
      setNewEnrolled([...newEnrolled, subject]);
      setSuccessMessage(`¡Te inscribiste en ${subject.nombre}!`);
      setTimeout(() => setSuccessMessage(''), 3000);
    }
  };

  const handleRemove = (subjectId) => {
    setNewEnrolled(newEnrolled.filter(s => s.id !== subjectId));
  };

  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Inscribirse a Materias</h2>
      </div>

      {successMessage && <div className="success-message">{successMessage}</div>}

      <div className="enrollment-container">
        <div className="available-subjects">
          <h3>Materias Disponibles</h3>
          <div className="subjects-list">
            {availableSubjects.length > 0 ? (
              availableSubjects.map(subject => (
                <div key={subject.id} className="subject-item">
                  <div className="subject-info">
                    <h4>{subject.nombre}</h4>
                    <p>{subject.codigo}</p>
                    <small>Prof. {subject.profesor} | {subject.estudiantes} estudiantes</small>
                  </div>
                  <button
                    className="btn-enroll"
                    onClick={() => handleEnroll(subject)}
                    disabled={newEnrolled.find(s => s.id === subject.id)}
                  >
                    {newEnrolled.find(s => s.id === subject.id) ? '✓ Inscrito' : 'Inscribirse'}
                  </button>
                </div>
              ))
            ) : (
              <p style={{ color: '#999', padding: '20px', textAlign: 'center' }}>
                No hay materias disponibles para inscribirse en este momento.
              </p>
            )}
          </div>
        </div>

        {newEnrolled.length > 0 && (
          <div className="enrolled-subjects">
            <h3>Materias Seleccionadas ({newEnrolled.length})</h3>
            <div className="selected-list">
              {newEnrolled.map(subject => (
                <div key={subject.id} className="selected-item">
                  <div>
                    <strong>{subject.nombre}</strong>
                    <p>{subject.codigo}</p>
                  </div>
                  <button
                    className="btn-remove"
                    onClick={() => handleRemove(subject.id)}
                  >
                    Remover
                  </button>
                </div>
              ))}
            </div>
            <button className="btn-confirm">Confirmar Inscripción</button>
          </div>
        )}
      </div>
    </div>
  );
};

const ChangeInstitution = ({ user, onBack }) => {
  const [institutions] = React.useState([
    { id: 1, codigo: 'INST-001', nombre: 'Colegio San Martín', ciudad: 'CABA', estudiantes: 450 },
    { id: 2, codigo: 'INST-002', nombre: 'Escuela Técnica', ciudad: 'La Plata', estudiantes: 320 },
    { id: 3, codigo: 'INST-003', nombre: 'Instituto Privado', ciudad: 'CABA', estudiantes: 280 },
    { id: 4, codigo: 'INST-004', nombre: 'Liceo Municipal', ciudad: 'Quilmes', estudiantes: 390 },
  ]);

  const [selectedInst, setSelectedInst] = React.useState(null);
  const [successMessage, setSuccessMessage] = React.useState('');

  const handleChangeInstitution = () => {
    if (selectedInst) {
      setSuccessMessage(`Cambio de institución a ${selectedInst.nombre} solicitado. Será procesado en breve.`);
      setTimeout(() => setSuccessMessage(''), 5000);
      setSelectedInst(null);
    }
  };

  return (
    <div className="menu-content">
      <div className="content-header">
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={20} />
        </button>
        <h2>Cambiar Institución</h2>
      </div>

      {successMessage && <div className="success-message">{successMessage}</div>}

      <div className="institution-container">
        <div className="current-institution">
          <h3>Institución Actual</h3>
          <div className="inst-card current">
            <h4>Colegio San Martín</h4>
            <p>CABA, Buenos Aires</p>
            <p className="status">Estado: Activo</p>
          </div>
        </div>

        <div className="available-institutions">
          <h3>Instituciones Disponibles</h3>
          <div className="institutions-grid">
            {institutions.map(inst => (
              <div
                key={inst.id}
                className={`inst-card ${selectedInst?.id === inst.id ? 'selected' : ''}`}
                onClick={() => setSelectedInst(inst)}
              >
                <h4>{inst.nombre}</h4>
                <p>{inst.codigo}</p>
                <p>{inst.ciudad}</p>
                <small>{inst.estudiantes} estudiantes</small>
              </div>
            ))}
          </div>
        </div>

        {selectedInst && (
          <div className="change-confirmation">
            <h3>¿Cambiar a {selectedInst.nombre}?</h3>
            <p>Esta acción requiere aprobación administrativa.</p>
            <div className="confirmation-buttons">
              <button className="btn-cancel" onClick={() => setSelectedInst(null)}>
                Cancelar
              </button>
              <button className="btn-confirm" onClick={handleChangeInstitution}>
                Confirmar Cambio
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const ConvertGrades = ({ subjects = [], onBack }) => {
  const subjectGrades = subjects
    .filter(s => s.nota !== null)
    .map(s => ({
      materia: s.nombre,
      nota: s.nota,
      tipo: 'FINAL',
      codigo: s.codigo
    }));

  const grades = subjectGrades.length > 0 ? subjectGrades : [
    { materia: 'Matemática', nota: 8.5, tipo: 'FINAL', codigo: 'MAT-001' },
    { materia: 'Lengua', nota: 9.0, tipo: 'FINAL', codigo: 'LEN-001' },
    { materia: 'Física', nota: 8.5, tipo: 'FINAL', codigo: 'FIS-001' },
  ];

  const [conversionSystem, setConversionSystem] = React.useState('');
  const [converted, setConverted] = React.useState([]);

  const conversionSystems = {
    'a-4': {
      name: 'Escala 0-4',
      convert: (nota) => (nota / 10) * 4
    },
    'a-100': {
      name: 'Escala 0-100',
      convert: (nota) => nota * 10
    },
    'letter': {
      name: 'Letras (A-F)',
      convert: (nota) => {
        if (nota >= 9) return 'A';
        if (nota >= 8) return 'B';
        if (nota >= 7) return 'C';
        if (nota >= 6) return 'D';
        return 'F';
      }
    },
    'percentage': {
      name: 'Porcentaje (%)',
      convert: (nota) => nota * 10
    },
  };

  React.useEffect(() => {
    if (conversionSystem && conversionSystems[conversionSystem]) {
      const system = conversionSystems[conversionSystem];
      setConverted(grades.map(g => ({
        ...g,
        convertida: system.convert(g.nota)
      })));
    }
  }, [conversionSystem, grades]);

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
          <h3>Selecciona un Sistema de Conversión</h3>
          <div className="system-buttons">
            {Object.entries(conversionSystems).map(([key, system]) => (
              <button
                key={key}
                className={`system-btn ${conversionSystem === key ? 'active' : ''}`}
                onClick={() => setConversionSystem(key)}
              >
                {system.name}
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!conversionSystem && (
          <div className="no-system">
            <p>Selecciona un sistema de conversión para ver tus notas convertidas</p>
          </div>
        )}
      </div>
    </div>
  );
};

export { StudentProfile, StudentEnrollment, ChangeInstitution, ConvertGrades };
