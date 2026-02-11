# EduGrade Multi-Database API Reference

## System Overview

Complete API specification for EduGrade educational data management system spanning 5 integrated databases.

```
┌──────────────────────────────────────┐
│       Flask REST API Endpoints       │
├──────────────────────────────────────┤
│                                      │
│  MongoDB API (Port 5000)             │
│  ├─ Estudiantes (CRUD)               │
│  ├─ Instituciones (CRUD)             │
│  ├─ Materias (CRUD)                  │
│  ├─ Calificaciones (CRUD + audit)    │
│  ├─ Profesores (CRUD)                │
│  ├─ Reglas Conversión (CRUD)         │
│  ├─ Trayectoria (analytics)          │
│  └─ Reportes (aggregation)           │
│                                      │
│  Neo4j API (Port 5001)               │
│  ├─ Nodos (Estudiante, Materia...)   │
│  ├─ Relaciones (INSCRIPTO_EN, CURSÓ) │
│  ├─ Trayectoria (graph navigate)     │
│  └─ Estadísticas (counts, trends)    │
│                                      │
│  Redis API (Port 5002)               │
│  ├─ Conversiones (cache, apply)      │
│  ├─ Sesiones (student, auth)         │
│  ├─ Auditoría (LIST tracking)        │
│  └─ Monitoreo (salud, stats)         │
│                                      │
│  Cassandra API (Port 5003)           │
│  ├─ Auditoría (immutable append)     │
│  ├─ Reportes Geográficos (analytics) │
│  ├─ Reportes Sistemas (comparison)   │
│  ├─ Analytics (approval, distrib)    │
│  └─ Salud (status)                   │
│                                      │
└──────────────────────────────────────┘
```

---

## MongoDB API (app/endpoint-mongo.py)

### Base URL: `http://localhost:5000/api/v1`

### Estudiantes

#### POST /estudiantes
Create student
```json
{
  "legajo": "STU20241001",
  "nombre": "Juan",
  "apellido": "González",
  "documento": {
    "tipo": "DNI",
    "numero": "12345678",
    "pais": "AR"
  },
  "fecha_nacimiento": "2005-03-15",
  "email": "juan@example.com"
}
```

#### GET /estudiantes
List students (paginated, filtered)
```
GET /estudiantes?pagina=1&limite=50&legajo=STU&estado=ACTIVO
```

#### GET /estudiantes/{id}
Retrieve student by ID

#### PUT /estudiantes/{id}
Update student

#### DELETE /estudiantes/{id}
Soft delete (estado → INACTIVO)

### Instituciones

#### POST /instituciones
Create institution
```json
{
  "codigo": "INST-CABA-001",
  "nombre": "Colegio San Martín",
  "nivel_educativo": "SECUNDARIO",
  "ubicacion": {
    "region": "CABA",
    "provincia": "Buenos Aires",
    "pais": "AR",
    "ciudad": "CABA"
  }
}
```

#### GET /instituciones
List institutions (paginated, filtered)

#### GET /instituciones/{id}
Retrieve institution

#### PUT /instituciones/{id}
Update institution

#### DELETE /instituciones/{id}
Soft delete

### Materias

#### POST /materias
Create subject
```json
{
  "codigo": "MAT-002",
  "nombre": "Matemática",
  "nivel": "SECUNDARIO",
  "horas_semanales": 4,
  "institucion_id": "507f1f77bcf86cd799439012"
}
```

#### GET /materias
List subjects (paginated)

#### GET /materias/{id}
Retrieve subject

#### PUT /materias/{id}
Update subject

#### DELETE /materias/{id}
Soft delete

### Calificaciones

#### POST /calificaciones
Register grade (writes to MongoDB + Neo4j + Cassandra)
```json
{
  "estudiante_id": "507f1f77bcf86cd799439011",
  "materia_id": "507f1f77bcf86cd799439012",
  "valor_original": {
    "nota": 8.5,
    "tipo": "FINAL"
  },
  "componentes": [
    {
      "tipo": "PARCIAL_1",
      "valor": 8.0,
      "peso_porcentual": 0.3,
      "fecha": "2024-03-15",
      "observaciones": "Muy bien"
    }
  ],
  "fecha_emision": "2024-06-15",
  "created_by": "profesor_123",
  "anio_lectivo": 2024
}
```
**Cascades to:**
- Neo4j: TIENE_CALIFICACION relationship
- Cassandra: reportes_geograficos, analytics_aprobacion, registro_auditoria

#### GET /calificaciones/{id}
Retrieve grade

#### PUT /calificaciones/{id}
Update grade (soft delete or mark as CORREGIDA)

#### DELETE /calificaciones/{id}
Soft delete

### Profesores

#### POST /profesores
Create professor
```json
{
  "legajo_docente": "PROF001",
  "nombre": "María",
  "apellido": "López",
  "email": "maria@example.com"
}
```

#### GET /profesores
List professors

#### GET /profesores/{id}
Retrieve professor

#### PUT /profesores/{id}
Update professor

#### DELETE /profesores/{id}
Soft delete

### Reglas Conversión

#### POST /reglas-conversion
Create conversion rule
```json
{
  "codigo_regla": "CONV-GB-AR-v1",
  "sistema_origen": "GB",
  "sistema_destino": "AR",
  "version_regla": 1,
  "escala_origen": [0, 10],
  "escala_destino": [0, 10],
  "mapeo": [
    {"nota_origen": 9.0, "nota_destino": 9.2},
    {"nota_origen": 8.5, "nota_destino": 8.7}
  ]
}
```

#### GET /reglas-conversion
List conversion rules

#### GET /reglas-conversion/{id}
Retrieve rule

#### PUT /reglas-conversion/{id}
Update rule

#### DELETE /reglas-conversion/{id}
Soft delete

### Trayectoria & Reportes

#### GET /estudiantes/{id}/trayectoria
Get student academic trajectory
```
Returns:
{
  "estudiante_id": "507f...",
  "nombre": "Juan González",
  "instituciones": [...],
  "materias_inscritas": [...],
  "materias_cursadas": [...],
  "promedio_general": 7.85,
  "total_aprobadas": 12,
  "historico_completo": [...]
}
```

#### GET /reportes/promedios
Aggregated grade averages
```
GET /reportes/promedios?pais=AR&nivel=SECUNDARIO&anio=2024
```

#### GET /reportes/distribucion
Grade distribution by region/level
```
GET /reportes/distribucion?pais=AR&region=CABA
```

---

## Neo4j Graph API (docker/neo4j/api_neo4j.py)

### Base URL: `http://localhost:5001/api/neo4j`

### Nodos (Nodes)

#### POST /nodos/estudiante
Create student node
```json
{
  "id": "507f1f77bcf86cd799439011",
  "nombre": "Juan",
  "apellido": "González",
  "legajo": "STU20241001"
}
```

#### POST /nodos/materia
Create subject node

#### POST /nodos/institucion
Create institution node

### Relaciones (Relationships)

#### POST /relaciones/inscripcion
Student inscribed in course
```json
{
  "estudiante_id": "507f1f77bcf86cd799439011",
  "materia_id": "507f1f77bcf86cd799439012",
  "fecha_inscripcion": "2024-01-15",
  "estado": "ACTIVA"
}
```

#### PUT /relaciones/inscripcion/{rel_id}
Update inscription state
```json
{
  "estado": "COMPLETADA" | "CANCELADA"
}
```

#### POST /relaciones/cursada
Register course participation (history)
```json
{
  "estudiante_id": "507f1f77bcf86cd799439011",
  "materia_id": "507f1f77bcf86cd799439012",
  "numero_intento": 1,
  "estado": "EN_CURSO" | "COMPLETADA" | "APROBADA" | "REPROBADA",
  "fecha_inicio": "2024-03-01"
}
```

### Trayectoria

#### GET /estudiantes/{est_id}/trayectoria
Full academic trajectory from graph
```
Returns: {
  "estudiante_id": "507f...",
  "instituciones": [...institutions from ESTUDIA_EN],
  "materias_inscritas": [...current from INSCRIPTO_EN],
  "materias_cursadas": [...history from CURSÓ with intento numbers],
  "relaciones_totales": {...summary}
}
```

### Estadísticas

#### GET /estadisticas/estudiantes-totales
Count of all student nodes

#### GET /estadisticas/materias-top
Top 10 most enrolled subjects

#### GET /estadisticas/resumen
Summary statistics

---

## Redis Cache & Session API (docker/redis/api_redis.py)

### Base URL: `http://localhost:5002/api/redis`

### Conversiones (Caching & Application)

#### POST /conversiones
Load conversion rule from MongoDB into Redis cache (7-day TTL)
```json
{
  "regla_id_mongo": "507f1f77bcf86cd799439015"
}
```

#### GET /conversiones/{codigo}
Retrieve cached conversion rule with TTL info

#### POST /conversiones/aplicar
Apply conversion and persist to MongoDB + Cassandra
```json
{
  "calificacion_id_mongo": "507f1f77bcf86cd799439014",
  "codigo_regla": "CONV-GB-AR-v1",
  "convertido_por": "usuario_123"
}
```
**Cascades to:**
- Redis LIST: conversion_audit:{cal_id} (ephemeral, 30d)
- MongoDB: calificaciones.conversiones_aplicadas (APPEND)
- Cassandra: reportes_sistemas, registro_auditoria (immutable)

#### GET /conversiones/auditoria/{cal_id}
Get conversion audit trail from Redis LIST
```
Returns: [
  {
    "fecha_conversion": "2024-06-20T14:30:00",
    "valor_original": 8.5,
    "valor_convertido": 8.7,
    "sistema_origen": "GB",
    "sistema_destino": "AR"
  },
  ...
]
```

#### LIST /conversiones
List all cached conversion rules

#### DELETE /conversiones/{codigo}
Remove conversion from cache

### Sesiones (Student Sessions)

#### POST /sesiones
Create student session (24-hour TTL)
```json
{
  "estudiante_id_mongo": "507f1f77bcf86cd799439011",
  "legajo": "STU20241001",
  "nombre": "Juan"
}
```
**Returns:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "estado": "ACTIVA",
  "fecha_creacion": "2024-06-20T15:00:00",
  "expira_en_horas": 24
}
```

#### GET /sesiones/{session_id}
Retrieve session info + last access time

#### PUT /sesiones/{session_id}
Update session (touch last_accessed)

#### DELETE /sesiones/{session_id}
Close session (logout)

#### GET /sesiones/estudiante/{est_id}
Get session by student ID

#### GET /sesiones
List all active sessions with TTL

### Student Cache

#### POST /cache/estudiante
Cache student data (7-day TTL)

#### GET /cache/estudiante/{est_id}
Retrieve cached student data

### Monitoreo

#### GET /estadisticas
Redis stats: conversiones count, sesiones activas, auditoría entries, memory
```json
{
  "conversiones_cacheadas": 8,
  "sesiones_activas": 3,
  "registros_auditoria": 45,
  "estudiantes_cacheados": 12,
  "memoria_usada_mb": 2.5
}
```

#### GET /salud
Health check - verify Redis is responding

---

## Cassandra Analytics & Audit API (docker/cassandra/api_cassandra.py)

### Base URL: `http://localhost:5003/api/cassandra`

### Auditoría (Immutable Append-Only)

#### POST /auditoria
Register audit event (append-only)
```json
{
  "id_estudiante": "507f1f77bcf86cd799439011",
  "tipo_accion": "CALIFICACION_REGISTRADA" | "CONVERSION_APLICADA" | "CAMBIO_ESTADO",
  "nota_original": "8.5",
  "usuario_auditor": "profesor_123",
  "descripcion": "Registrada calificación de Matemática",
  "metadata": {
    "materia": "Matemática",
    "fecha_emision": "2024-01-15"
  }
}
```
**Returns:**
```json
{
  "id_auditoria": "07d86c58-3f8a-11eb-88b1-e0b9dd0c5e67",
  "hash_integridad": "a1b2c3d4e5f6...",
  "timestamp": "2024-06-20T15:30:00"
}
```

#### GET /auditoria/estudiante/{id}
Get audit trail for student (most recent first)
```
GET /auditoria/estudiante/507f...?limit=100&tipo_accion=CONVERSION_APLICADA
```

#### GET /auditoria
Query audit trail by date range (for compliance)
```
GET /auditoria?fecha_inicio=2024-01-01&fecha_fin=2024-01-31&limit=1000
```

### Reportes Geográficos

#### POST /reportes/geograficos
Register grade into geographic analytics
```json
{
  "region": "CABA",
  "institucion_id": "507f1f77bcf86cd799439012",
  "anio_lectivo": 2024,
  "nota": 8.5
}
```

#### GET /reportes/geograficos
Get geographic analytics
```
GET /reportes/geograficos?region=CABA&anio_lectivo=2024
GET /reportes/geograficos?region=CABA&institucion_id=507f...&anio_lectivo=2024
```
**Returns:** Promedio per institution in region with year-over-year

### Reportes Sistemas

#### POST /reportes/sistemas
Register conversion into system analytics
```json
{
  "sistema_educativo": "AR",
  "anio_lectivo": 2024,
  "materia_nombre": "Matemática",
  "promedio_convertido": 8.7
}
```

#### GET /reportes/sistemas
Cross-system effectiveness analysis
```
GET /reportes/sistemas?sistema_educativo=AR&anio_lectivo=2024
```
**Returns:** Promedio per subject after conversion into target system

### Analytics - Approval Rates

#### POST /analytics/aprobacion
Register approval metric
```json
{
  "pais": "AR",
  "nivel_educativo": "SECUNDARIO",
  "anio_lectivo": 2024,
  "aprobado": true,
  "nota": 8.5
}
```

#### GET /analytics/aprobacion
Get approval rate metrics
```
GET /analytics/aprobacion?pais=AR&nivel_educativo=SECUNDARIO&anio_lectivo=2024
```
**Returns:**
```json
{
  "pais": "AR",
  "nivel": "SECUNDARIO",
  "anio": 2024,
  "total_calificaciones": 156000,
  "total_aprobadas": 131040,
  "tasa_aprobacion_porcentaje": 84.0,
  "promedio_notas": 7.42
}
```

### Analytics - Distribution

#### POST /analytics/distribucion
Register grade distribution
```json
{
  "pais": "AR",
  "nivel_educativo": "SECUNDARIO",
  "anio_lectivo": 2024,
  "rango_nota": "8-9"
}
```

#### GET /analytics/distribucion
Get grade distribution histogram
```
GET /analytics/distribucion?pais=AR&nivel_educativo=SECUNDARIO&anio_lectivo=2024
```
**Returns:** Percentage in each grade range

### Salud

#### GET /salud
Health check - verify Cassandra connection
```json
{
  "estado": "OK",
  "servicio": "Cassandra",
  "conectado": true,
  "keyspace": "edugrade_audit"
}
```

---

## Data Flow Examples

### Scenario 1: Student Registration & Grade Recording

```
1. POST /api/v1/estudiantes (MongoDB)
   └─ Create student doc

2. POST /api/v1/calificaciones (MongoDB)
   ├─ INSERT into calificaciones collection
   ├─ MERGE Neo4j nodes & TIENE_CALIFICACION relationship
   ├─ UPDATE Cassandra reportes_geograficos (COUNTER +1)
   ├─ UPDATE Cassandra analytics_aprobacion (COUNTER +1)
   ├─ INSERT Cassandra registro_auditoria (immutable)
   └─ Response: grade recorded in all 4 databases

3. GET /api/v1/calificaciones/{id} (MongoDB)
   └─ Retrieve from transactional storage

4. GET /api/neo4j/estudiantes/{id}/trayectoria (Neo4j)
   └─ Navigate graph to show full academic history

5. GET /api/cassandra/auditoria/estudiante/{id} (Cassandra)
   └─ View immutable audit trail of registration event
```

### Scenario 2: Grade Conversion

```
1. POST /api/redis/conversiones (Redis)
   └─ Load conversion rule from MongoDB into Redis cache

2. POST /api/redis/conversiones/aplicar (Redis + MongoDB + Cassandra)
   ├─ GET rule from Redis cache
   ├─ GET grade from MongoDB
   ├─ Calculate conversion (nota_origen → nota_destino)
   ├─ LPUSH Redis LIST conversion_audit:{cal_id} (ephemeral)
   ├─ $PUSH MongoDB calificaciones.conversiones_aplicadas (persistent)
   ├─ UPDATE Cassandra reportes_sistemas (system effectiveness)
   ├─ INSERT Cassandra registro_auditoria (immutable log)
   └─ Response: conversion recorded in all systems

3. GET /api/redis/conversiones/auditoria/{cal_id} (Redis)
   └─ View recent conversion history (30 days)

4. GET /api/cassandra/reportes/sistemas?sistema=AR (Cassandra)
   └─ View cross-system effectiveness metrics

5. GET /api/cassandra/auditoria/estudiante/{id} (Cassandra)
   └─ View immutable record of conversion event forever
```

### Scenario 3: Compliance Audit

```
1. GET /api/cassandra/auditoria?fecha_inicio=2024-01-01&fecha_fin=2024-01-31 (Cassandra)
   └─ Retrieve all audit entries during January for compliance

2. For each event:
   - Verify hash_integridad (SHA256 matches original data)
   - Check usuario_auditor, fecha_creacion, tipo_accion
   - Follow id_auditoria (TIMEUUID) ordering
   - Confirm no UPDATEs or DELETEs (append-only guarantee)

3. GET /api/cassandra/analytics/aprobacion?pais=AR&nivel=SECUNDARIO&anio=2024 (Cassandra)
   └─ Generate ministry report: approval rates by region

4. GET /api/cassandra/analytics/distribucion?pais=AR&nivel=SECUNDARIO&anio=2024 (Cassandra)
   └─ Detect assessment issues via grade distribution
```

---

## Error Handling

All endpoints return structured errors:

```json
{
  "error": "Campos requeridos: legajo, nombre, apellido",
  "status": 400
}
```

Common HTTP Status Codes:
- `201 Created` - Resource created successfully
- `200 OK` - Request successful
- `400 Bad Request` - Missing/invalid fields
- `404 Not Found` - Resource not found
- `409 Conflict` - Duplicate unique field
- `500 Internal Server Error` - Server error (check logs)

---

## Rate Limiting & Caching

| API | Caching | TTL | Read Optimized |
|-----|---------|-----|-----------------|
| MongoDB | None | - | Write-heavy |
| Neo4j | Graph cache | - | Relationship queries |
| Redis | Native | 7d rules, 24h sessions, 30d audit | Very fast reads |
| Cassandra | Pre-aggregated | None (immutable) | Analytical reads |

---

## Development Guide

### Running All Services

```bash
docker-compose up -d

# Check status
curl http://localhost:5000/api/v1/salud  # MongoDB
curl http://localhost:5001/api/neo4j/salud  # Neo4j  
curl http://localhost:5002/api/redis/salud  # Redis
curl http://localhost:5003/api/cassandra/salud  # Cassandra
```

### Testing Complete Flow

```bash
# 1. Create student
STUDENT_ID=$(curl -X POST http://localhost:5000/api/v1/estudiantes \
  -H "Content-Type: application/json" \
  -d '{"legajo": "TEST001", ...}' | jq -r '.id')

# 2. Register grade (cascades to all DBs)
curl -X POST http://localhost:5000/api/v1/calificaciones \
  -H "Content-Type: application/json" \
  -d "{\"estudiante_id\": \"$STUDENT_ID\", ...}"

# 3. Apply conversion
curl -X POST http://localhost:5002/api/redis/conversiones/aplicar \
  -H "Content-Type: application/json" \
  -d '{"calificacion_id_mongo": "...", "codigo_regla": "..."}'

# 4. View immutable audit trail
curl http://localhost:5003/api/cassandra/auditoria/estudiante/$STUDENT_ID
```

---

## References

- [MongoDB Schema](./coleccionesNuevas.txt)
- [Neo4j Graph Model](./docker/neo4j/entities.py)
- [Redis Patterns](./docker/redis/entities.py)
- [Cassandra Tables](./docker/cassandra/entities.py)
- [Full Architecture](./CASSANDRA_INTEGRATION.md)
