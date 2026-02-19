import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api/v1';

// Crear instancia de Axios
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para agregar token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para manejo de errores
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ==========================================
// AUTENTICACIÓN
// ==========================================

export const authService = {
  login: (email, password) => 
    apiClient.post('/auth/login', { email, password }),
  
  register: (userData) =>
    apiClient.post('/auth/register', userData),
  
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }
};

// ==========================================
// ESTUDIANTES
// ==========================================

export const studentService = {
  getAll: (params = {}) =>
    apiClient.get('/estudiantes', { params }),
  
  getById: (id) =>
    apiClient.get(`/estudiantes/${id}`),
  
  create: (data) =>
    apiClient.post('/estudiantes', data),
  
  update: (id, data) =>
    apiClient.put(`/estudiantes/${id}`, data),
  
  delete: (id) =>
    apiClient.delete(`/estudiantes/${id}`),

  getByEmail: (email) =>
    apiClient.get(`/estudiantes/email/${encodeURIComponent(email)}`)

  ,
  cambiarInstitucion: (id, nueva_institucion_id, regla_conversion_codigo) =>
    apiClient.post(`/estudiantes/${id}/cambiar-institucion`, { nueva_institucion_id, regla_conversion_codigo })
};

// ==========================================
// CALIFICACIONES
// ==========================================

export const gradeService = {
  getAll: (params = {}) =>
    apiClient.get('/calificaciones', { params }),
  
  getById: (id) =>
    apiClient.get(`/calificaciones/${id}`),
  
  getByStudent: (studentId, params = {}) =>
    apiClient.get(`/calificaciones/estudiante/${studentId}`, { params }),
  
  create: (data) =>
    apiClient.post('/calificaciones', data),
  
  update: (id, data) =>
    apiClient.put(`/calificaciones/${id}`, data),
  
  delete: (id) =>
    apiClient.delete(`/calificaciones/${id}`)
};

// ==========================================
// MATERIAS
// ==========================================

export const subjectService = {
  getAll: (params = {}) =>
    apiClient.get('/academic/materias', { params }),
  
  getById: (id) =>
    apiClient.get(`/academic/materias/${id}`),
  
  create: (data) =>
    apiClient.post('/academic/materias', data),
  
  update: (id, data) =>
    apiClient.put(`/academic/materias/${id}`, data),
  
  delete: (id) =>
    apiClient.delete(`/academic/materias/${id}`),
  
  getByStudent: (studentId) =>
    apiClient.get(`/academic/materias/estudiante/${studentId}`)
};

// ==========================================
// INSTITUCIONES
// ==========================================

export const institutionService = {
  getAll: (params = {}) =>
    apiClient.get('/academic/instituciones', { params }),
  
  getById: (id) =>
    apiClient.get(`/academic/instituciones/${id}`),
  
  create: (data) =>
    apiClient.post('/academic/instituciones', data),
  
  update: (id, data) =>
    apiClient.put(`/academic/instituciones/${id}`, data),
  
  delete: (id) =>
    apiClient.delete(`/academic/instituciones/${id}`)
};

// ==========================================
// CARRERAS (para reportes / certificado analítico)
// ==========================================

export const carreraService = {
  getAll: () => apiClient.get('/academic/carreras'),
  getById: (id) => apiClient.get(`/academic/carreras/${id}`)
};

// ==========================================
// PROFESORES
// ==========================================

export const teacherService = {
  getAll: (params = {}) =>
    apiClient.get('/profesores', { params }),
  
  getById: (id) =>
    apiClient.get(`/profesores/${id}`),
  
  create: (data) =>
    apiClient.post('/profesores', data),
  
  update: (id, data) =>
    apiClient.put(`/profesores/${id}`, data),
  
  delete: (id) =>
    apiClient.delete(`/profesores/${id}`)
};

// ==========================================
// REPORTES Y ANALYTICS
// ==========================================

export const reportService = {
  getStudentReport: (studentId) =>
    apiClient.get(`/reportes/estudiante/${studentId}`),
  
  getInstitutionReport: (institutionId) =>
    apiClient.get(`/reportes/institucion/${institutionId}`),
  
  getGradeStats: (params = {}) =>
    apiClient.get('/reportes/calificaciones', { params }),

  getApprovalStats: (params = {}) =>
    apiClient.get('/reportes/aprobacion', { params }),
  
  getAuditoria: (studentId) =>
    apiClient.get(`/reportes/auditoria/${studentId}`),
  
  getRegional: (region) =>
    apiClient.get(`/reportes/region/${region}`),

  /** Certificado analítico: reporte integral (promedio histórico, % avance, snapshot opcional) */
  getCertificadoAnalitico: (studentId, params = {}) =>
    apiClient.get(`/reportes/certificado-analitico/${studentId}`, { params })
};

// ==========================================
// TRAYECTORIA (NEO4J)
// ==========================================

export const trajectoryService = {
  getStudentTrajectory: (studentId) =>
    apiClient.get(`/trayectoria/estudiante/${studentId}`),
  
  getSubjectTrajectory: (subjectId) =>
    apiClient.get(`/trayectoria/materia/${subjectId}`)
};

// ==========================================
// CONVERSIONES
// ==========================================

export const conversionService = {
  getAllRules: () =>
    apiClient.get('/calificaciones/reglas'),
  
  getRuleById: (id) =>
    apiClient.get(`/calificaciones/reglas/${id}`),
  
  createRule: (data) =>
    apiClient.post('/calificaciones/reglas', data),
  
  updateRule: (id, data) =>
    apiClient.put(`/calificaciones/reglas/${id}`, data),
  
  applyConversion: (data) =>
    apiClient.post('/calificaciones/convertir', data)
};

// ==========================================
// GRADING OPERATIONS
// ==========================================

export const gradingOperations = {
  inscribirAlumno: (data) =>
    apiClient.post('/calificaciones/inscribir', data),
  
  cargarNota: (data) =>
    apiClient.post('/calificaciones/cargar-nota', data),
  
  cerrarCursada: (data) =>
    apiClient.post('/calificaciones/cerrar-cursada', data)
};

// ==========================================
// PROFESSOR OPERATIONS
// ==========================================

export const professorOperations = {
  asignarMateria: (profId, data) =>
    apiClient.post(`/profesores/${profId}/asignar-materia`, data)
};

export default apiClient;
