# Documentación Técnica del Backend — EduGrade

> Sistema de gestión educativa multi-modelo. Backend en **Python/Flask**, con cuatro bases de datos que cumplen roles distintos y complementarios.

---

## 1. Arquitectura General

```
frontend (React)
      │  HTTP/REST
      ▼
  Flask API  (run.py · puerto 5000)
      │
      ├── MongoDB      → datos principales (documentos)
      ├── Neo4j        → relaciones académicas (grafo)
      ├── Redis        → caché de reglas de conversión
      └── Cassandra    → auditoría, metadatos, certificados
```

El punto de entrada es `run.py`. Registra seis Blueprints bajo el prefijo `/api/v1/`:

| Blueprint        | Prefijo                   | Responsabilidad                              |
|------------------|---------------------------|----------------------------------------------|
| `student_bp`     | `/api/v1/estudiantes`     | CRUD de estudiantes + traslados              |
| `academic_bp`    | `/api/v1/academic`        | Instituciones, Materias, Carreras            |
| `grading_bp`     | `/api/v1/calificaciones`  | Notas, inscripciones, conversiones           |
| `professor_bp`   | `/api/v1/profesores`      | CRUD de profesores + dashboard docente       |
| `reports_bp`     | `/api/v1/reportes`        | Reportes, estadísticas, certificado analítico|
| `trajectory_bp`  | `/api/v1/trayectoria`     | Trayectoria académica vía grafo              |

CORS habilitado para `http://localhost:3000`. `strict_slashes = False` evita problemas de redirección en preflight.

---

## 2. Bases de Datos: qué guarda cada una y por qué

### 2.1 MongoDB — Datos Principales
Base de datos documental. Almacena la información "de estado" del sistema.

| Colección           | Qué contiene                                                                 |
|---------------------|------------------------------------------------------------------------------|
| `estudiantes`       | Legajo, nombre, apellido, email, metadata de estado (ACTIVO/INACTIVO)       |
| `profesores`        | Legajo docente, nombre, especialidad, email, rol                             |
| `instituciones`     | Código, nombre, país, nivel (SECUNDARIO/UNIVERSITARIO/TERCIARIO), estado     |
| `materias`          | Código, nombre, nivel, referencia a institución (`institucion_id`), estado   |
| `carreras`          | Nombre, lista de `materias_ids`, estado                                      |
| `calificaciones`    | `estudiante_id`, `materia_id`, `valor_original` (nota + tipo), conversiones aplicadas |
| `reglas_conversion` | Código de regla, nombre, array de pares `{nota_origen, nota_destino}`        |

**Por qué MongoDB:** esquema flexible, ideal para documentos con campos variables (notas pueden ser números o letras según la escala del país).

### 2.2 Neo4j — Grafo de Relaciones Académicas
Almacena nodos y aristas que representan quién estudia qué, en qué institución, y con qué resultado.

**Nodos:**
- `Estudiante` — propiedades: `id_mongo`, `nombre`, `apellido`, `activo`
- `Materia` — propiedades: `id_mongo`, `codigo`, `nombre`
- `Institucion` — propiedades: `id_mongo`, `codigo`, `nombre`, `pais`, `nivel`
- `Carrera` — propiedades: `id_mongo`, `codigo`, `nombre`
- `Profesor` — propiedades: `id_mongo`, `nombre`, `legajo`

**Relaciones:**

| Relación            | Origen → Destino             | Propiedades clave                                              |
|---------------------|------------------------------|----------------------------------------------------------------|
| `PERTENECE_A`       | Estudiante → Institución     | —                                                             |
| `CURSANDO`          | Estudiante → Materia         | `anio`, `primer_parcial`, `segundo_parcial`, `final`, `previo`|
| `CURSÓ`             | Estudiante → Materia         | `estado` (APROBADO/REPROBADO/APROBADO (EQUIVALENCIA)), `fecha_cierre`, notas |
| `PERTENECE_A`       | Materia → Institución        | —                                                             |
| `CONTIENE`          | Carrera → Materia            | —                                                             |
| `DICTAN`            | Profesor → Materia           | `fecha_asignacion`                                            |
| `DICTARON`          | Profesor → Materia           | (historial: ya no la dicta activamente)                       |
| `EQUIVALE_A`        | Materia ↔ Materia            | Para homologaciones entre instituciones                       |

**Por qué Neo4j:** las consultas de trayectoria, detección de recursadas, materias equivalentes entre instituciones y cálculo de materias faltantes para recibirse son consultas de grafo nativas que serían muy costosas en SQL o MongoDB.

### 2.3 Redis — Caché de Reglas de Conversión
Almacena las reglas de conversión de notas con TTL de 7 días.

- Clave: `regla:<codigo_regla>` → valor: JSON de la regla completa.
- **Patrón Cache-Aside:** al aplicar una conversión se busca primero en Redis; si no está (miss), se consulta MongoDB y se recachea.
- Al crear o actualizar una regla, Redis se actualiza inmediatamente.

**Por qué Redis:** las conversiones de notas se aplican en masa durante los traslados. Cachear evita múltiples roundtrips a MongoDB para la misma regla.

### 2.4 Cassandra — Auditoría y Documentos Oficiales
Almacena eventos inmutables y documentos que no deben modificarse.

| Tabla                 | Contenido                                                                 |
|-----------------------|---------------------------------------------------------------------------|
| `entity_metadata`     | Estado (ACTIVO/INACTIVO) de estudiantes y profesores al momento de creación |
| `registro_auditoria`  | Cada acción sobre un estudiante: traslados, cargas de nota, con timestamp |
| `certificados_emitidos` | Snapshot JSON completo del certificado analítico en el momento de emisión |
| `historico_reglas`    | Versiones anteriores de reglas de conversión antes de ser modificadas     |

**Por qué Cassandra:** escritura de alta disponibilidad, ideal para logs de auditoría. El modelo wide-column con `PRIMARY KEY (id_estudiante, fecha_creacion)` permite recuperar todo el historial de un estudiante ordenado cronológicamente.

---

## 3. Servicios y Lógica de Negocio

### 3.1 StudentService

**`create(data)`**
1. Inserta documento en `estudiantes` (MongoDB).
2. Guarda metadata inicial en Cassandra (`entity_metadata`).
3. Crea nodo `Estudiante` en Neo4j con `MERGE` (idempotente).

**`get_all()` / `get_by_id()` / `get_by_email()`**
- Consulta MongoDB para los datos del estudiante.
- Hace un **join manual con Neo4j**: busca la relación `PERTENECE_A` para obtener `institucion_nombre`, `institucion_id` y `institucion_codigo`.
- Retorna un objeto enriquecido con ambos orígenes de datos.

**`cambiar_institucion(estudiante_id, nueva_institucion_id, regla_conversion_codigo)`**
Es la operación más compleja del sistema. Pasos:
1. **Obtiene la regla de conversión** desde MongoDB.
2. **En Neo4j**, busca materias que el estudiante aprobó (`CURSÓ` con `estado = APROBADO`) que tengan una relación `EQUIVALE_A` con materias de la nueva institución.
3. Para cada materia equivalente, **aplica el mapeo de notas** de la regla de conversión.
4. **Crea o actualiza** relaciones `CURSÓ` con `estado = 'APROBADO (EQUIVALENCIA)'` en Neo4j hacia las materias de la nueva institución.
5. **Guarda** la calificación convertida en MongoDB (`calificaciones`).
6. **Mueve al estudiante** de institución eliminando la relación `PERTENECE_A` anterior y creando una nueva.
7. **Registra auditoría** en Cassandra.

### 3.2 AcademicService

Gestiona Instituciones, Materias y Carreras. Toda operación escribe en **MongoDB + Neo4j** de forma sincronizada.

**Instituciones:** CRUD completo. El campo `nivel` acepta `SECUNDARIO`, `UNIVERSITARIO` o `TERCIARIO`. Se valida antes de guardar.

**Materias:** al crear, se vincula a una institución mediante la relación `(Materia)-[:PERTENECE_A]->(Institucion)` en Neo4j.

**Carreras:** colección en MongoDB + nodo en Neo4j. La relación `(Carrera)-[:CONTIENE]->(Materia)` permite calcular materias faltantes para recibirse.

**`get_materias_faltantes_para_recibirse(est_id, carrera_id)`**
- Obtiene IDs de materias aprobadas por el estudiante en Neo4j.
- Obtiene IDs de materias que contiene la carrera en Neo4j.
- Retorna la diferencia: materias de la carrera que el estudiante aún no aprobó.

### 3.3 GradingService

**`inscribir_alumno(est_id, mat_id, anio_lectivo)`**
- Crea relación `CURSANDO` en Neo4j con `CREATE` (no `MERGE`) para soportar recursadas múltiples.

**`cargar_nota(est_id, mat_id, tipo_nota, valor)`**
- Actualiza la propiedad correspondiente (`primer_parcial`, `segundo_parcial`, `final` o `previo`) en la relación `CURSANDO` o `CURSÓ` en Neo4j.
- Registra en Cassandra.

**`cerrar_cursada(est_id, mat_id)`**
- En una sola query Cypher: evalúa si `final >= 4` o `previo >= 4` → `APROBADO`, sino `REPROBADO`.
- Crea nueva relación `CURSÓ` copiando todas las propiedades de `CURSANDO`.
- Elimina la relación `CURSANDO`.

**`registrar_calificacion(data)`**
- Guarda la nota en MongoDB (`calificaciones`).
- Llama a `cargar_nota` para sincronizar el valor en el grafo Neo4j.

### 3.4 ConversionService

**`create_rule(data)` / `update_rule(regla_id, data)`**
- Escribe en MongoDB.
- Cachea en Redis con TTL 7 días.
- Al actualizar, guarda el estado anterior en Cassandra (`historico_reglas`) para trazabilidad.

**`aplicar_conversion(data)`**
- Patrón **Cache-Aside**: busca la regla en Redis primero; si no está, la trae de MongoDB.
- Aplica el mapeo de notas (soporta comparación numérica con tolerancia `0.01` y comparación de strings case-insensitive).
- Hace `$push` en el array `conversiones_aplicadas` de la calificación en MongoDB (no sobreescribe, registra el historial de conversiones).

### 3.5 ProfessorService

- CRUD estándar con sincronización MongoDB + Neo4j.
- **`asignar_materia(prof_id, mat_id)`**: crea relación `DICTAN` en Neo4j.
- **`get_materias_by_profesor(prof_id)`**: consulta Neo4j para obtener las materias activas del profesor (`DICTAN`).
- **`get_alumnos_by_materia(mat_id)`**: consulta Neo4j para obtener todos los estudiantes con relación `CURSANDO` hacia esa materia, incluyendo sus notas parciales.

### 3.6 TranscriptService — Certificado Analítico

**`generar_certificado_analitico(estudiante_id, carrera_nombre, guardar_snapshot)`**
1. Trae datos del estudiante desde MongoDB.
2. Consulta en Neo4j todas las relaciones `CURSÓ` con `estado = 'APROBADO'` y calcula el **promedio histórico**.
3. Si se indica una carrera, calcula el **porcentaje de avance** comparando materias aprobadas contra materias de la carrera.
4. Opcionalmente, guarda el certificado completo como **snapshot JSON inmutable** en Cassandra (`certificados_emitidos`).

### 3.7 AnalyticsService

- **`get_auditoria_estudiante(est_id)`**: consulta Cassandra (`registro_auditoria`) para traer el historial completo de acciones sobre el estudiante, ordenado por fecha.
- **`get_reporte_geo(region)`**: consulta Cassandra (`reportes_geograficos`) para estadísticas regionales.

### 3.8 MetadataService

- **`save_metadata(entity_type, entity_id, estado)`**: escribe en Cassandra (`entity_metadata`) el estado inicial de cualquier entidad creada (estudiante, profesor).

---

## 4. Endpoints Completos

### `/api/v1/estudiantes`
| Método | Ruta                                   | Descripción                                              |
|--------|----------------------------------------|----------------------------------------------------------|
| POST   | `/`                                    | Crear estudiante (MongoDB + Neo4j + Cassandra)           |
| GET    | `/`                                    | Listar todos (con institución desde Neo4j)               |
| GET    | `/<uid>`                               | Obtener por ID (con institución desde Neo4j)             |
| PUT    | `/<uid>`                               | Actualizar (sincroniza Neo4j; si hay `institucion_id`, mueve la relación `PERTENECE_A`) |
| DELETE | `/<uid>`                               | Soft delete (estado INACTIVO en Mongo; DETACH DELETE en Neo4j) |
| GET    | `/email/<email>`                       | Buscar por email (con institución desde Neo4j)           |
| POST   | `/<id>/cambiar-institucion`            | Traslado con homologación de materias y conversión de notas |

### `/api/v1/academic`
| Método | Ruta                                           | Descripción                                        |
|--------|------------------------------------------------|----------------------------------------------------|
| POST/GET | `/instituciones`                             | Crear / listar instituciones activas               |
| GET/PUT/DELETE | `/instituciones/<uid>`                 | CRUD individual                                    |
| POST/GET | `/materias`                                  | Crear / listar materias vigentes                   |
| GET/PUT/DELETE | `/materias/<uid>`                      | CRUD individual                                    |
| GET    | `/materias/estudiante/<est_id>`                | Materias que cursó un estudiante (desde Neo4j)     |
| POST/GET | `/carreras`                                  | Crear / listar carreras                            |
| GET    | `/carreras/<uid>`                              | Detalle de carrera                                 |
| POST   | `/carreras/<carrera_id>/materias/<materia_id>` | Agregar materia a carrera                          |
| GET    | `/carreras/<carrera_id>/materias`              | Materias de una carrera                            |
| GET    | `/carreras/<carrera_id>/faltantes/<est_id>`    | Materias que le faltan al estudiante para recibirse|

### `/api/v1/calificaciones`
| Método | Ruta                      | Descripción                                                 |
|--------|---------------------------|-------------------------------------------------------------|
| POST   | `/`                       | Registrar calificación (MongoDB + sincroniza Neo4j)         |
| GET    | `/`                       | Listar todas (últimas 100)                                  |
| GET/PUT/DELETE | `/<calif_id>`     | CRUD individual                                             |
| GET    | `/estudiante/<uid>`       | Historial completo de un estudiante desde Neo4j             |
| POST   | `/inscribir`              | Inscribir alumno a materia (crea `CURSANDO` en Neo4j)       |
| POST   | `/cargar-nota`            | Cargar nota parcial/final (actualiza relación en Neo4j)     |
| POST   | `/cerrar-cursada`         | Evalúa y convierte `CURSANDO` → `CURSÓ` con APROBADO/REPROBADO |
| GET    | `/reglas`                 | Listar reglas de conversión                                 |
| POST   | `/reglas`                 | Crear regla (MongoDB + Redis)                               |
| GET/PUT | `/reglas/<regla_id>`     | Leer / actualizar regla (historial en Cassandra)            |
| POST   | `/convertir`              | Aplicar conversión a una calificación (Cache-Aside Redis)   |

### `/api/v1/profesores`
| Método | Ruta                              | Descripción                                             |
|--------|-----------------------------------|---------------------------------------------------------|
| POST/GET | `/`                             | Crear / listar profesores                               |
| GET/PUT/DELETE | `/<uid>`                  | CRUD individual                                         |
| GET    | `/email/<email>`                  | Buscar por email                                        |
| POST   | `/<prof_id>/asignar-materia`      | Crear relación `DICTAN` en Neo4j                        |
| GET    | `/<prof_id>/materias`             | Materias activas que dicta el profesor (Neo4j)          |
| GET    | `/materia/<mat_id>/alumnos`       | Alumnos cursando esa materia con sus notas (Neo4j)      |

### `/api/v1/reportes`
| Método | Ruta                                 | Descripción                                                           |
|--------|--------------------------------------|-----------------------------------------------------------------------|
| GET    | `/estudiante/<est_id>`               | Reporte completo: datos + calificaciones (Mongo) + estadísticas (Neo4j) + auditoría (Cassandra) |
| GET    | `/institucion/<inst_id>`             | Datos + materias + total estudiantes/materias activas (Neo4j)         |
| GET    | `/auditoria/<est_id>`                | Historial de auditoría del estudiante desde Cassandra                 |
| GET    | `/calificaciones`                    | Estadísticas: promedio, mín, máx, aprobados, reprobados (MongoDB)     |
| GET    | `/aprobacion`                        | Tasa de aprobación global desde Neo4j                                 |
| GET    | `/certificado-analitico/<est_id>`    | Certificado con materias aprobadas, promedio histórico y % avance (snapshot en Cassandra) |
| GET    | `/region/<region>`                   | Reporte geográfico desde Cassandra                                    |

### `/api/v1/trayectoria`
| Método | Ruta                     | Descripción                                                                          |
|--------|--------------------------|--------------------------------------------------------------------------------------|
| GET    | `/estudiante/<est_id>`   | Trayectoria completa: en curso, aprobadas, reprobadas, recursadas (todo desde Neo4j) |
| GET    | `/materia/<mat_id>`      | Vista desde la materia: quién la cursó, aprobó o reprobó                             |

---

## 5. Flujos de Datos Clave

### Flujo 1: Login de un estudiante
```
Frontend → GET /api/v1/estudiantes/email/<email>
           └── MongoDB: find_one({email})
           └── Neo4j: MATCH (e)-[:PERTENECE_A]->(i) → institucion_nombre
           ← Retorna objeto con datos personales + institución actual
```

### Flujo 2: Ciclo de vida de una cursada
```
1. Inscripción:   POST /calificaciones/inscribir
                  → Neo4j: CREATE (e)-[:CURSANDO {anio}]->(m)

2. Carga de nota: POST /calificaciones/cargar-nota
                  → Neo4j: SET r.primer_parcial = valor

3. Cierre:        POST /calificaciones/cerrar-cursada
                  → Neo4j: evalúa notas → crea CURSÓ (APROBADO|REPROBADO)
                           elimina CURSANDO
```

### Flujo 3: Traslado entre instituciones (operación más compleja)
```
POST /estudiantes/<id>/cambiar-institucion
  │
  ├─ 1. Lee regla de conversión desde MongoDB
  │
  ├─ 2. Neo4j: busca materias aprobadas con EQUIVALE_A en nueva institución
  │
  ├─ 3. Aplica mapeo de notas (según regla)
  │
  ├─ 4. Neo4j: crea CURSÓ {estado: 'APROBADO (EQUIVALENCIA)'} en materias destino
  │
  ├─ 5. MongoDB: guarda calificaciones convertidas
  │
  ├─ 6. Neo4j: borra PERTENECE_A vieja, crea nueva hacia institución destino
  │
  └─ 7. Cassandra: INSERT en registro_auditoria
```

### Flujo 4: Aplicar conversión de nota (Cache-Aside)
```
POST /calificaciones/convertir
  │
  ├─ Busca regla en Redis (GET regla:<codigo>)
  │   ├── HIT  → usa JSON de Redis
  │   └── MISS → MongoDB find + Redis SETEX (7 días)
  │
  ├─ Lee calificación desde MongoDB
  ├─ Aplica mapeo (número o letra)
  └─ MongoDB: $push en conversiones_aplicadas (append-only, preserva historial)
```

### Flujo 5: Certificado Analítico
```
GET /reportes/certificado-analitico/<est_id>
  │
  ├─ MongoDB: datos personales del estudiante
  ├─ Neo4j: MATCH CURSÓ WHERE estado='APROBADO' → lista materias aprobadas
  ├─ Calcula promedio histórico
  ├─ (Opcional) MongoDB: carrera → calcula % de avance
  └─ Cassandra: INSERT snapshot JSON inmutable (tabla certificados_emitidos)
```

---

## 6. Decisiones de Diseño Importantes

**Sincronización dual MongoDB ↔ Neo4j**
Toda entidad (estudiante, materia, institución, profesor) existe en ambas bases. 
MongoDB es la fuente de verdad de los datos; 
Neo4j es la fuente de verdad de las relaciones. 
Si una operación falla a mitad, los datos pueden quedar inconsistentes — esto se acepta a cambio de la potencia de consultas de grafo.

**Soft Delete generalizado**
No se borran documentos en MongoDB; se cambia `metadata.estado` a `INACTIVO`. En Neo4j sí se hace `DETACH DELETE` para limpiar relaciones.

**Append-only en conversiones**
El array `conversiones_aplicadas` en `calificaciones` nunca se sobreescribe, solo se agregan entradas. Esto mantiene el historial completo de todas las conversiones aplicadas a cada nota.

**Relación `CURSANDO` con `CREATE` (no `MERGE`)**
Se usa `CREATE` en lugar de `MERGE` para permitir que un estudiante curse la misma materia más de una vez (recursada). Esto genera múltiples aristas entre el mismo par de nodos.

**Cassandra como auditoria y documentos oficiales**
Cassandra es write-optimized y append-only por diseño. Ideal para logs que nunca se modifican. Los certificados emitidos son snapshots inmutables: aunque el alumno curse más materias, el certificado refleja el estado exacto en el momento de la emisión.
