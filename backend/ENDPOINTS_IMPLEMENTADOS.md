# Endpoints Implementados - Sistema EduGrade

## Resumen de Implementación

Este documento lista todos los endpoints implementados en el backend y su estado de integración con el frontend.

---

## ✅ Endpoints Completamente Implementados

### 1. Estudiantes (`/api/v1/estudiantes`)

- ✅ `POST /` - Crear estudiante
- ✅ `GET /` - Obtener todos los estudiantes
- ✅ `GET /<uid>` - Obtener estudiante por ID
- ✅ `PUT /<uid>` - Actualizar estudiante
- ✅ `DELETE /<uid>` - Eliminar estudiante (soft delete)
- ✅ `GET /email/<email>` - Obtener estudiante por email

**Frontend:** ✅ Integrado en AdminDashboard

---

### 2. Instituciones (`/api/v1/academic/instituciones`)

- ✅ `POST /instituciones` - Crear institución
- ✅ `GET /instituciones` - Obtener todas las instituciones
- ✅ `GET /instituciones/<uid>` - Obtener institución por ID
- ✅ `PUT /instituciones/<uid>` - Actualizar institución
- ✅ `DELETE /instituciones/<uid>` - Eliminar institución (soft delete)

**Frontend:** ✅ Integrado en AdminDashboard

---

### 3. Materias (`/api/v1/academic/materias`)

- ✅ `POST /materias` - Crear materia
- ✅ `GET /materias` - Obtener todas las materias
- ✅ `GET /materias/<uid>` - Obtener materia por ID
- ✅ `PUT /materias/<uid>` - Actualizar materia
- ✅ `DELETE /materias/<uid>` - Eliminar materia (soft delete)
- ✅ `GET /materias/estudiante/<est_id>` - Obtener materias de un estudiante

**Frontend:** ✅ Integrado en AdminDashboard

---

### 3b. Carreras (`/api/v1/academic/carreras`)

- ✅ `POST /carreras` - Crear carrera
- ✅ `GET /carreras` - Obtener todas las carreras
- ✅ `GET /carreras/<uid>` - Obtener carrera por ID
- ✅ `POST /carreras/<carrera_id>/materias/<materia_id>` - Agregar materia a carrera
- ✅ `GET /carreras/<carrera_id>/materias` - Materias que contiene la carrera
- ✅ `GET /carreras/<carrera_id>/faltantes/<est_id>` - Materias que le faltan al estudiante para recibirse

**Frontend:** ❌ Pendiente de integración

---

### 4. Calificaciones (`/api/v1/calificaciones`)

- ✅ `POST /` - Registrar calificación
- ✅ `GET /` - Obtener todas las calificaciones
- ✅ `GET /<calif_id>` - Obtener calificación por ID
- ✅ `PUT /<calif_id>` - Actualizar calificación
- ✅ `DELETE /<calif_id>` - Eliminar calificación (soft delete)
- ✅ `GET /estudiante/<uid>` - Obtener historial de estudiante
- ✅ `POST /inscribir` - Inscribir alumno a materia
- ✅ `POST /cargar-nota` - Cargar nota en relación CURSANDO
- ✅ `POST /cerrar-cursada` - Cerrar cursada y evaluar aprobación

**Frontend:** ✅ Integrado en AdminDashboard

---

### 5. Profesores (`/api/v1/profesores`)

- ✅ `POST /` - Crear profesor
- ✅ `GET /` - Obtener todos los profesores
- ✅ `GET /<uid>` - Obtener profesor por ID
- ✅ `PUT /<uid>` - Actualizar profesor
- ✅ `DELETE /<uid>` - Eliminar profesor (soft delete)
- ✅ `POST /<prof_id>/asignar-materia` - Asignar materia a profesor

**Frontend:** ⚠️ Pendiente de integración

---

### 6. Conversiones / Reglas (`/api/v1/calificaciones`)

- ✅ `GET /reglas` - Listar todas las reglas de conversión
- ✅ `POST /reglas` - Crear regla de conversión
- ✅ `GET /reglas/<regla_id>` - Obtener regla por ID
- ✅ `PUT /reglas/<regla_id>` - Actualizar regla (auditoría en Cassandra: historico_reglas)
- ✅ `POST /convertir` - Aplicar conversión de nota

**Frontend:** ⚠️ Pendiente de integración

---

### 7. Trayectorias (`/api/v1/trayectoria`)

- ✅ `GET /estudiante/<est_id>` - Obtener trayectoria completa de estudiante
- ✅ `GET /materia/<mat_id>` - Obtener trayectoria de materia (todos los estudiantes)

**Frontend:** ⚠️ Pendiente de integración

---

### 8. Reportes (`/api/v1/reportes`)

- ✅ `GET /certificado-analitico/<est_id>` - Certificado analítico (reporte integral: datos alumno + materias aprobadas + promedio histórico + % avance; opcional snapshot en Cassandra)
  - Query: `?carrera_nombre=...&guardar_snapshot=true|false`
- ✅ `GET /auditoria/<est_id>` - Obtener auditoría de estudiante
- ✅ `GET /region/<region>` - Obtener reporte geográfico
- ✅ `GET /estudiante/<est_id>` - Reporte completo de estudiante
- ✅ `GET /institucion/<inst_id>` - Reporte de institución
- ✅ `GET /calificaciones` - Estadísticas de calificaciones
- ✅ `GET /aprobacion` - Estadísticas de aprobación

**Frontend:** ⚠️ Pendiente de integración

---

## 🔧 Configuración

### CORS
- ✅ Habilitado en `run.py` con `flask-cors`

### Dependencias
Todas las dependencias están listadas en `requirements.txt`:
- Flask >= 3.0.0
- flask-cors >= 4.0.0
- pymongo >= 4.6.0
- neo4j >= 5.15.0
- redis >= 5.0.0
- cassandra-driver >= 3.29.0
- requests >= 2.31.0

---

## 📊 Estado de Integración Frontend

### ✅ Completamente Integrado
- AdminDashboard: Estudiantes, Materias, Calificaciones, Instituciones

### ⚠️ Parcialmente Integrado
- StudentDashboard: Usa datos mock, necesita actualización

### ❌ Pendiente de Integración
- Gestión de Profesores
- Visualización de Trayectorias
- Reportes y Analytics
- Conversión de Notas (listar/editar reglas)
- Certificado analítico y Carreras
- Auditoría

---

## 🚀 Próximos Pasos (Frontend)

1. **Actualizar StudentDashboard** para usar servicios reales
2. **Crear componentes de visualización**:
   - Gráficos de trayectorias
   - Tablas de reportes
   - Formularios de conversión (GET/PUT reglas)
   - Certificado analítico y materias faltantes por carrera
3. **Implementar visualizaciones de Neo4j**:
   - Grafo de relaciones académicas
   - Trayectorias visuales
4. **Agregar componentes de analytics**:
   - Dashboard de estadísticas
   - Gráficos de aprobación
   - Reportes geográficos




