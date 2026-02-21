import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import api from '../services/api';
import './ProfessorDashboard.css'; 

const ProfessorDashboard = ({ user, onLogout }) => {
  const [materias, setMaterias] = useState([]);
  const [selectedMateria, setSelectedMateria] = useState(null);
  const [alumnos, setAlumnos] = useState([]);
  const [loading, setLoading] = useState(true);

  // Notas temporales editadas antes de enviar
  const [notasEdit, setNotasEdit] = useState({});

  useEffect(() => {
    cargarMaterias();
  }, [user]);

  const cargarMaterias = async () => {
    try {
      const profId = user?._id || user?.id; 
      const response = await api.get(`/profesores/${profId}/materias`);
      setMaterias(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error al cargar materias:", error);
      setLoading(false);
    }
  };

  const seleccionarMateria = async (materia) => {
    setSelectedMateria(materia);
    cargarAlumnos(materia.materia_id);
  };

  const cargarAlumnos = async (materiaId) => {
    try {
      const response = await api.get(`/profesores/materia/${materiaId}/alumnos`);
      setAlumnos(response.data);
      setNotasEdit({});
    } catch (error) {
      console.error("Error al cargar alumnos:", error);
    }
  };

  const handleNotaChange = (estudianteId, tipoNota, valor) => {
    setNotasEdit(prev => ({
      ...prev,
      [`${estudianteId}-${tipoNota}`]: valor
    }));
  };

  const guardarNota = async (estudianteId, tipoNota) => {
    const valor = notasEdit[`${estudianteId}-${tipoNota}`];
    if (valor === undefined || valor === '') return alert('Ingresa un valor válido');

    try {
      await api.post('/calificaciones/cargar-nota', {
        estudiante_id: estudianteId,
        materia_id: selectedMateria.materia_id,
        tipo_nota: tipoNota,
        valor: parseFloat(valor)
      });
      alert('Nota guardada correctamente');
      cargarAlumnos(selectedMateria.materia_id); // Recargar
    } catch (error) {
      console.error("Error al guardar nota:", error);
      alert('Error al guardar la nota');
    }
  };

  const cerrarCursada = async (estudianteId) => {
    if (!window.confirm("¿Seguro que deseas cerrar la cursada para este alumno? Se moverá a su historial académico permanente.")) return;

    try {
      await api.post('/calificaciones/cerrar-cursada', {
        estudiante_id: estudianteId,
        materia_id: selectedMateria.materia_id
      });
      alert('Cursada cerrada exitosamente');
      cargarAlumnos(selectedMateria.materia_id); // Recargar lista
    } catch (error) {
      console.error("Error al cerrar cursada:", error);
      alert('Error al cerrar la cursada');
    }
  };

  return (
    <div className="dashboard-container">
      <Navbar user={user} onLogout={onLogout} />
      
      <div className="dashboard-content">
        <h1>Gestión de Calificaciones Docente</h1>
        
        {loading ? <p>Cargando tus materias...</p> : (
          <div className="materias-grid">
            {materias.length === 0 ? <p>No tienes materias asignadas actualmente.</p> : 
              materias.map(m => (
                <button 
                  key={m.materia_id} 
                  className={`materia-btn ${selectedMateria?.materia_id === m.materia_id ? 'active' : ''}`}
                  onClick={() => seleccionarMateria(m)}
                >
                  {m.nombre} ({m.codigo})
                </button>
              ))
            }
          </div>
        )}

        {selectedMateria && (
          <div className="alumnos-section" style={{marginTop: '30px'}}>
            <h2>Alumnos Inscriptos: {selectedMateria.nombre}</h2>
            {alumnos.length === 0 ? <p>No hay alumnos cursando esta materia.</p> : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Alumno</th>
                    <th>1° Parcial</th>
                    <th>2° Parcial</th>
                    <th>Final</th>
                    <th>Previo</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {alumnos.map(al => (
                    <tr key={al.estudiante_id}>
                      <td>{al.nombre_completo}</td>
                      
                      {['primer_parcial', 'segundo_parcial', 'final', 'previo'].map(tipo => (
                        <td key={tipo}>
                          <input 
                            type="number" 
                            style={{width: '60px'}}
                            defaultValue={al.notas[tipo] !== null ? al.notas[tipo] : ''}
                            onChange={(e) => handleNotaChange(al.estudiante_id, tipo, e.target.value)}
                          />
                          <button 
                            className="btn-small" 
                            onClick={() => guardarNota(al.estudiante_id, tipo)}
                            title="Guardar esta nota"
                          >
                            💾
                          </button>
                        </td>
                      ))}
                      
                      <td>
                        <button className="btn-danger" onClick={() => cerrarCursada(al.estudiante_id)}>
                          Cerrar Cursada
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfessorDashboard;