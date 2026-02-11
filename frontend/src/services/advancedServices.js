import axios from 'axios';

// ==========================================
// SERVICIOS ADICIONALES DE BASES DE DATOS
// ==========================================

// NEO4J - Para consultas de trayectoria y relaciones
const neo4jClient = axios.create({
  baseURL: process.env.REACT_APP_API_NEO4J_URL || 'http://localhost:5001/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// REDIS - Para cache y sesiones
const redisClient = axios.create({
  baseURL: process.env.REACT_APP_API_REDIS_URL || 'http://localhost:5002/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// CASSANDRA - Para auditoría e informes geográficos
const cassandraClient = axios.create({
  baseURL: process.env.REACT_APP_API_CASSANDRA_URL || 'http://localhost:5003/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ==========================================
// NEO4J SERVICES - Análisis de Trayectorias
// ==========================================

export const neo4jService = {
  /**
   * Obtener trayectoria completa de un estudiante
   * Incluye todas las materias, relaciones y recomendaciones
   */
  getStudentTrayectory: (studentId) =>
    neo4jClient.get(`/trayectory/student/${studentId}`),

  /**
   * Obtener estudiantes que cursaron una materia
   * Útil para estadísticas y comparativas
   */
  getSubjectStudents: (subjectId) =>
    neo4jClient.get(`/subject/${subjectId}/students`),

  /**
   * Analizar progresión académica
   * Detecta patrones y tendencias
   */
  getProgressionAnalysis: (studentId) =>
    neo4jClient.get(`/analysis/progression/${studentId}`),

  /**
   * Encontrar relaciones entre materias
   * Identifica prerequisitos y materias relacionadas
   */
  getSubjectRelations: (subjectId) =>
    neo4jClient.get(`/subject/${subjectId}/relations`),

  /**
   * Obtener recomendaciones para el estudiante
   * Basadas en su trayectoria
   */
  getRecommendations: (studentId) =>
    neo4jClient.get(`/recommendations/${studentId}`),
};

// ==========================================
// REDIS SERVICES - Cache y Sesiones
// ==========================================

export const redisService = {
  /**
   * Obtener datos en cache
   * Mejora velocidad de consultas frecuentes
   */
  getCached: (key) =>
    redisClient.get(`/cache/${key}`),

  /**
   * Almacenar datos en cache
   */
  setCache: (key, data, ttl = 3600) =>
    redisClient.post(`/cache/${key}`, { data, ttl }),

  /**
   * Limpiar cache de un usuario
   */
  clearUserCache: (userId) =>
    redisClient.delete(`/cache/user/${userId}`),

  /**
   * Obtener sesión activa
   */
  getSession: (sessionId) =>
    redisClient.get(`/session/${sessionId}`),

  /**
   * Crear nueva sesión
   */
  createSession: (userId, data) =>
    redisClient.post(`/session`, { userId, data }),

  /**
   * Obtener estadísticas de uso
   */
  getStats: () =>
    redisClient.get(`/stats`),

  /**
   * Aplicar reglas de conversión almacenadas
   */
  applyConversionRules: (grade) =>
    redisClient.post(`/conversions/apply`, { grade }),
};

// ==========================================
// CASSANDRA SERVICES - Auditoría e Informes
// ==========================================

export const cassandraService = {
  /**
   * Obtener historial de auditoría completo
   * Registros inmutables de cambios
   */
  getAuditLog: (params = {}) =>
    cassandraClient.get(`/audit/log`, { params }),

  /**
   * Obtener auditoría de un estudiante
   */
  getStudentAudit: (studentId) =>
    cassandraClient.get(`/audit/student/${studentId}`),

  /**
   * Obtener auditoría de una calificación
   */
  getGradeAudit: (gradeId) =>
    cassandraClient.get(`/audit/grade/${gradeId}`),

  /**
   * Reportes geográficos por región
   * Analiza distribución de estudiantes
   */
  getGeographicReport: (region) =>
    cassandraClient.get(`/reports/geographic/${region}`),

  /**
   * Comparativa de sistemas
   * Compara rendimiento entre bases de datos
   */
  getSystemComparison: () =>
    cassandraClient.get(`/reports/systems`),

  /**
   * Estadísticas de aprobación
   * Por materia, institución, período
   */
  getApprovalStats: (params = {}) =>
    cassandraClient.get(`/reports/approval`, { params }),

  /**
   * Análisis de distribución de calificaciones
   */
  getGradeDistribution: (subjectId) =>
    cassandraClient.get(`/reports/distribution/${subjectId}`),

  /**
   * Estado de la salud del sistema
   */
  getHealth: () =>
    cassandraClient.get(`/health`),

  /**
   * Métricas de rendimiento
   */
  getMetrics: () =>
    cassandraClient.get(`/metrics`),
};

// ==========================================
// SERVICIOS COMBINADOS - CONSULTAS INTELIGENTES
// ==========================================

/**
 * Servicio para consultas complejas que combinan múltiples bases de datos
 */
export const advancedQueryService = {
  /**
   * Análisis completo de estudiante
   * Combina datos de MongoDB, Neo4j, Redis y Cassandra
   */
  getCompleteStudentAnalysis: async (studentId) => {
    try {
      const [basicData, trayectory, audit, stats] = await Promise.all([
        axios.get(`/api/v1/estudiantes/${studentId}`),
        neo4jService.getStudentTrayectory(studentId),
        cassandraService.getStudentAudit(studentId),
        redisService.getCached(`analysis_${studentId}`),
      ]);

      return {
        student: basicData.data,
        trayectory: trayectory.data,
        auditTrail: audit.data,
        cachedAnalysis: stats.data,
      };
    } catch (error) {
      console.error('Error en análisis completo:', error);
      throw error;
    }
  },

  /**
   * Reporte institucional completo
   * Incluye estadísticas geográficas y de aprobación
   */
  getInstitutionalReport: async (institutionId) => {
    try {
      const [institution, geographic, approval, health] = await Promise.all([
        axios.get(`/api/v1/instituciones/${institutionId}`),
        cassandraService.getGeographicReport(`INST-${institutionId}`),
        cassandraService.getApprovalStats({ institution: institutionId }),
        cassandraService.getHealth(),
      ]);

      return {
        institution: institution.data,
        geographic: geographic.data,
        approval: approval.data,
        systemHealth: health.data,
      };
    } catch (error) {
      console.error('Error en reporte institucional:', error);
      throw error;
    }
  },

  /**
   * Dashboard ejecutivo
   * Resumen de todo el sistema
   */
  getExecutiveDashboard: async () => {
    try {
      const [students, subjects, approval, comparison, metrics] = await Promise.all([
        axios.get(`/api/v1/estudiantes?limite=1000`),
        axios.get(`/api/v1/materias?limite=1000`),
        cassandraService.getApprovalStats(),
        cassandraService.getSystemComparison(),
        cassandraService.getMetrics(),
      ]);

      return {
        totalStudents: students.data.length,
        totalSubjects: subjects.data.length,
        approvalStats: approval.data,
        systemComparison: comparison.data,
        metrics: metrics.data,
      };
    } catch (error) {
      console.error('Error en dashboard ejecutivo:', error);
      throw error;
    }
  },
};

// ==========================================
// HOOK PARA USAR SERVICIOS EN COMPONENTES
// ==========================================

// En tus componentes, puedes importar y usar:
// import { neo4jService, cassandraService, advancedQueryService } from '../services/advancedServices.js'

// Ejemplo:
// const [ trayectory, setTrayectory ] = useState(null);
// 
// useEffect(() => {
//   neo4jService.getStudentTrayectory(studentId)
//     .then(res => setTrayectory(res.data))
//     .catch(err => console.error(err));
// }, [studentId]);

export default {
  neo4jService,
  redisService,
  cassandraService,
  advancedQueryService,
};
