/**
 * Ejemplos de integración con los servicios avanzados
 * Copiar y adaptar según tus necesidades
 */

// ==========================================
// EJEMPLO 1: Análisis Completo de Estudiante
// ==========================================

import { advancedQueryService } from '../services/advancedServices';

function StudentAnalysisExample() {
  const [analysis, setAnalysis] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        const result = await advancedQueryService.getCompleteStudentAnalysis('STUDENT_ID');
        setAnalysis(result);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, []);

  if (loading) return <p>Cargando análisis...</p>;
  if (!analysis) return <p>No hay datos disponibles</p>;

  return (
    <div>
      <h2>Análisis de {analysis.student.nombre}</h2>
      
      {/* Datos básicos del estudiante */}
      <section>
        <h3>Información del Estudiante</h3>
        <p>Nombre: {analysis.student.nombre}</p>
        <p>Email: {analysis.student.email}</p>
      </section>

      {/* Trayectoria académica (Neo4j) */}
      <section>
        <h3>Trayectoria Académica</h3>
        <p>{JSON.stringify(analysis.trayectory, null, 2)}</p>
      </section>

      {/* Audit trail (Cassandra) */}
      <section>
        <h3>Historial de Auditoría</h3>
        <p>{JSON.stringify(analysis.auditTrail, null, 2)}</p>
      </section>

      {/* Análisis en cache (Redis) */}
      <section>
        <h3>Análisis Cacheado</h3>
        <p>{JSON.stringify(analysis.cachedAnalysis, null, 2)}</p>
      </section>
    </div>
  );
}

// ==========================================
// EJEMPLO 2: Dashboard Ejecutivo
// ==========================================

import { cassandraService } from '../services/advancedServices';

function ExecutiveDashboard() {
  const [dashboard, setDashboard] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchDashboard = async () => {
      try {
        // Obtener datos desde Cassandra para el dashboard ejecutivo
        const [approval, metrics, comparison] = await Promise.all([
          cassandraService.getApprovalStats(),
          cassandraService.getMetrics(),
          cassandraService.getSystemComparison(),
        ]);

        setDashboard({
          approval: approval.data,
          metrics: metrics.data,
          comparison: comparison.data,
        });
      } catch (error) {
        console.error('Error cargando dashboard:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  if (loading) return <p>Cargando dashboard...</p>;
  if (!dashboard) return <p>No hay datos disponibles</p>;

  return (
    <div className="executive-dashboard">
      <h1>Dashboard Ejecutivo</h1>

      {/* Estadísticas de aprobación */}
      <section>
        <h2>Tasa de Aprobación</h2>
        <div className="stats-cards">
          {dashboard.approval?.map((stat, idx) => (
            <div key={idx} className="stat-card">
              <h3>{stat.materia}</h3>
              <p>Aprobbados: {stat.aprobados}</p>
              <p>Total: {stat.total}</p>
              <p>Tasa: {((stat.aprobados / stat.total) * 100).toFixed(2)}%</p>
            </div>
          ))}
        </div>
      </section>

      {/* Métricas del sistema */}
      <section>
        <h2>Métricas del Sistema</h2>
        <pre>{JSON.stringify(dashboard.metrics, null, 2)}</pre>
      </section>

      {/* Comparativa de sistemas */}
      <section>
        <h2>Comparativa de Bases de Datos</h2>
        <pre>{JSON.stringify(dashboard.comparison, null, 2)}</pre>
      </section>
    </div>
  );
}

// ==========================================
// EJEMPLO 3: Historial de Auditoría
// ==========================================

import { cassandraService } from '../services/advancedServices';

function AuditTrailViewer() {
  const [logs, setLogs] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [filters, setFilters] = React.useState({
    usuario: '',
    tipo_cambio: '',
    fecha_desde: '',
  });

  React.useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await cassandraService.getAuditLog(filters);
        setLogs(response.data);
      } catch (error) {
        console.error('Error cargando logs:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [filters]);

  return (
    <div className="audit-trail">
      <h1>Historial de Auditoría</h1>

      {/* Filtros */}
      <div className="filters">
        <input
          type="text"
          placeholder="Usuario"
          value={filters.usuario}
          onChange={(e) => setFilters({ ...filters, usuario: e.target.value })}
        />
        <select
          value={filters.tipo_cambio}
          onChange={(e) => setFilters({ ...filters, tipo_cambio: e.target.value })}
        >
          <option value="">Todos los cambios</option>
          <option value="CREATE">Crear</option>
          <option value="UPDATE">Actualizar</option>
          <option value="DELETE">Eliminar</option>
        </select>
        <input
          type="date"
          value={filters.fecha_desde}
          onChange={(e) => setFilters({ ...filters, fecha_desde: e.target.value })}
        />
      </div>

      {/* Tabla de logs */}
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Usuario</th>
              <th>Tipo de Cambio</th>
              <th>Tabla</th>
              <th>Detalles</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, idx) => (
              <tr key={idx}>
                <td>{new Date(log.timestamp).toLocaleString()}</td>
                <td>{log.usuario}</td>
                <td>{log.tipo_cambio}</td>
                <td>{log.tabla}</td>
                <td>{JSON.stringify(log.detalles)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ==========================================
// EJEMPLO 4: Análisis de Trayectoria (Neo4j)
// ==========================================

import { neo4jService } from '../services/advancedServices';

function TrayectoryAnalysis() {
  const [trayectory, setTrayectory] = React.useState(null);
  const [recommendations, setRecommendations] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchTrayectory = async (studentId) => {
      try {
        const [traj, recs] = await Promise.all([
          neo4jService.getStudentTrayectory(studentId),
          neo4jService.getRecommendations(studentId),
        ]);

        setTrayectory(traj.data);
        setRecommendations(recs.data);
      } catch (error) {
        console.error('Error cargando trayectoria:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTrayectory('STUDENT_ID');
  }, []);

  if (loading) return <p>Cargando trayectoria...</p>;
  if (!trayectory) return <p>No hay datos</p>;

  return (
    <div className="trayectory-analysis">
      <h1>Análisis de Trayectoria Académica</h1>

      {/* Visualización de camino académico */}
      <section>
        <h2>Camino Académico</h2>
        <div className="trayectory-graph">
          {/* Aquí podrías usar D3.js o similares para visualizar el grafo */}
          <pre>{JSON.stringify(trayectory, null, 2)}</pre>
        </div>
      </section>

      {/* Recomendaciones personalizadas */}
      <section>
        <h2>Recomendaciones</h2>
        <ul>
          {recommendations.map((rec, idx) => (
            <li key={idx}>
              <h3>{rec.titulo}</h3>
              <p>{rec.descripcion}</p>
              <p>Confianza: {(rec.confianza * 100).toFixed(1)}%</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

// ==========================================
// EJEMPLO 5: Reportes Geográficos (Cassandra)
// ==========================================

import { cassandraService } from '../services/advancedServices';

function GeographicReport() {
  const [regions, setRegions] = React.useState([]);
  const [selectedRegion, setSelectedRegion] = React.useState('CABA');
  const [report, setReport] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchReport = async () => {
      try {
        const response = await cassandraService.getGeographicReport(selectedRegion);
        setReport(response.data);
      } catch (error) {
        console.error('Error cargando reporte:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [selectedRegion]);

  return (
    <div className="geographic-report">
      <h1>Reportes Geográficos</h1>

      <div className="region-selector">
        <label>Selecciona una región:</label>
        <select value={selectedRegion} onChange={(e) => setSelectedRegion(e.target.value)}>
          <option value="CABA">CABA</option>
          <option value="BA">Buenos Aires</option>
          <option value="CÓRDOBA">Córdoba</option>
          <option value="ROSARIO">Rosario</option>
        </select>
      </div>

      {loading ? (
        <p>Cargando...</p>
      ) : report ? (
        <div className="report-content">
          <h2>Región: {selectedRegion}</h2>
          <p>Total Estudiantes: {report.total_estudiantes}</p>
          <p>Total Instituciones: {report.total_instituciones}</p>
          <p>Promedio de Aprobación: {(report.promedio_aprobacion * 100).toFixed(2)}%</p>
          
          <h3>Detalles por Institución:</h3>
          {report.instituciones?.map((inst, idx) => (
            <div key={idx} className="institution-detail">
              <h4>{inst.nombre}</h4>
              <p>Estudiantes: {inst.estudiantes}</p>
              <p>Aprobación: {(inst.tasa_aprobacion * 100).toFixed(2)}%</p>
            </div>
          ))}
        </div>
      ) : (
        <p>No hay datos disponibles</p>
      )}
    </div>
  );
}

export {
  StudentAnalysisExample,
  ExecutiveDashboard,
  AuditTrailViewer,
  TrayectoryAnalysis,
  GeographicReport,
};
