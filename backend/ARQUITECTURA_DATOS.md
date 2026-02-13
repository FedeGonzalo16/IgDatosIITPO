# Arquitectura de Datos - Sistema EduGrade

## Visión General

Este sistema utiliza una arquitectura de **Polyglot Persistence**, donde cada base de datos se utiliza para el propósito que mejor se adapta a sus fortalezas. La estrategia permite optimizar el rendimiento, la escalabilidad y la consistencia según las necesidades específicas de cada tipo de operación.

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE APLICACIÓN                       │
│              (Flask - Services & Routes)                    │
└──────────────────────┬─────────────────────────────--───────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   MongoDB    │ │  Neo4j    │ │   Redis      │
│  (Documentos)│ │  (Grafos) │ │   (Cache)    │
└──────────────┘ └──────────┘ └──────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
              ┌──────────────┐
              │  Cassandra   │
              │ (Analytics &  │
              │   Metadata)  │
              └──────────────┘
```

---

## 1. MongoDB - Almacenamiento Transaccional Principal

### Propósito
Base de datos **ACID-compliant** para operaciones transaccionales y almacenamiento de documentos estructurados.

### Datos Almacenados

#### Colecciones Principales:

1. **`estudiantes`**
   - Datos: `legajo`, `nombre`, `apellido`, `email`, `pais`
   - **NO incluye metadatos** (estos van a Cassandra)
   - Soft delete mediante campo `metadata.estado`

2. **`instituciones`**
   - Datos: `codigo`, `nombre`, `pais`
   - Metadatos: `metadata.created_at`, `metadata.estado`

3. **`materias`**
   - Datos: `codigo`, `nombre`, `nivel`
   - Referencia: `institucion_id` (ObjectId)

4. **`profesores`**
   - Datos: `legajo_docente`, `nombre`, `apellido`, `especialidad`
   - Metadatos en Cassandra

5. **`calificaciones`**
   - Datos: `estudiante_id`, `materia_id`, `valor_original`
   - Array append-only: `conversiones_aplicadas[]`
   - Hash de integridad (SHA256)

6. **`reglas_conversion`**
   - Datos: `codigo_regla`, `mapeo[]` (nota_origen → nota_destino)
   - También cacheado en Redis

### Características
- ✅ **CRUD completo** para todas las entidades
- ✅ **Soft delete** mediante `metadata.estado`
- ✅ **Transacciones ACID** para operaciones críticas
- ✅ **Índices únicos** en campos clave (legajo, codigo)
- ✅ **Sincronización** con Neo4j en operaciones de escritura

---

## 2. Neo4j - Base de Datos de Grafos

### Propósito
Almacenar y navegar **relaciones académicas** entre entidades. Ideal para consultas de trayectorias, recursadas y relaciones complejas.

### Modelo de Datos

#### Nodos:
- **`Estudiante`** {id_mongo, nombre, legajo}
- **`Materia`** {id_mongo, codigo, nombre}
- **`Institucion`** {id_mongo, codigo, nombre, pais}
- **`Profesor`** {id_mongo, nombre, legajo}

#### Relaciones:

1. **`CURSANDO`** (Estudiante → Materia)
   - Propiedades: `anio`, `estado` (EN_CURSO), `primer_parcial`, `segundo_parcial`, `final`, `previo`
   - Permite múltiples relaciones (recursadas)

2. **`CURSÓ`** (Estudiante → Materia)
   - Propiedades: Copia de `CURSANDO` + `estado` (APROBADO/REPROBADO), `fecha_cierre`
   - Relación histórica (no se modifica)

3. **`PERTENECE_A`** (Materia → Institucion)
   - Relación de pertenencia

4. **`DICTAN`** / **`DICTARON`** (Profesor → Materia)
   - `DICTAN`: Relación activa
   - `DICTARON`: Relación histórica
   - Propiedades: `fecha_asignacion`

### Flujos de Datos

#### Crear Estudiante:
```python
# 1. MongoDB: Insertar documento
mongo_id = db.estudiantes.insert_one(doc).inserted_id

# 2. Neo4j: Crear nodo sincronizado
MERGE (e:Estudiante {id_mongo: $id})
SET e.nombre = $nombre
```

#### Inscribir Alumno a Materia:
```python
# Solo en Neo4j (relación)
CREATE (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO {
    anio: $anio,
    estado: 'EN_CURSO'
}]->(m:Materia {id_mongo: $mat_id})
```

#### Cargar Nota:
```python
# Solo en Neo4j (actualizar relación)
MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO]->(m:Materia {id_mongo: $mat_id})
SET r.primer_parcial = $valor
```

#### Cerrar Cursada:
```python
# 1. Evaluar estado (APROBADO/REPROBADO)
# 2. Crear relación histórica CURSÓ
# 3. Eliminar relación activa CURSANDO
```

### Ventajas
- ✅ **Consultas complejas** de trayectorias en una sola query
- ✅ **Detección automática** de recursadas (múltiples relaciones)
- ✅ **Navegación eficiente** de relaciones académicas
- ✅ **Consistencia de relaciones** mantenida automáticamente

---

## 3. Redis - Capa de Caché

### Propósito
Almacenamiento **ephemeral** (temporal) para mejorar el rendimiento de lecturas frecuentes.

### Datos Cacheados

#### 1. **Reglas de Conversión**
```
Clave: regla:{codigo_regla}
Valor: JSON de la regla completa
TTL: 7 días (604800 segundos)
```

**Patrón Cache-Aside:**
```python
# 1. Intentar leer de Redis
rule = redis.get(f"regla:{codigo}")

# 2. Si no existe (cache miss), leer de MongoDB
if not rule:
    rule = db.reglas_conversion.find_one(...)
    # 3. Guardar en Redis para próximas consultas
    redis.setex(key, 604800, json.dumps(rule))
```

#### 2. **Sesiones de Usuario** (futuro)
- TTL: 24 horas

#### 3. **Auditoría Temporal** (futuro)
- Listas con TTL: 30 días

### Características
- ✅ **Alta velocidad** de lectura (< 1ms)
- ✅ **TTL automático** para invalidación
- ✅ **Cache-Aside pattern** con fallback a MongoDB
- ✅ **Reducción de carga** en MongoDB para consultas frecuentes

---

## 4. Cassandra - Analytics y Metadatos

### Propósito
Almacenamiento **append-only** para auditoría y metadatos. Optimizado para escrituras masivas y consultas analíticas.

### Tablas

#### 1. **`entity_metadata`**
```sql
CREATE TABLE entity_metadata (
    entity_type text,
    entity_id text,
    estado text,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (entity_type, entity_id)
)
```

**Uso:**
- Metadatos de estado (ACTIVO/INACTIVO) para todas las entidades
- Separación de concerns: datos en MongoDB, metadatos en Cassandra
- Consultas por tipo de entidad

**Flujo:**
```python
# Al crear estudiante/profesor
MetadataService.save_metadata('estudiante', mongo_id, 'ACTIVO')
```

#### 2. **`registro_auditoria`**
```sql
CREATE TABLE registro_auditoria (
    id_estudiante text,
    fecha_creacion timestamp,
    id_auditoria uuid,
    tipo_accion text,
    nota_original text,
    PRIMARY KEY (id_estudiante, fecha_creacion, id_auditoria)
)
```

**Uso:**
- Registro **inmutable** de todas las acciones
- Auditoría de cargas de notas
- Consultas por estudiante ordenadas por fecha

**Flujo:**
```python
# Al cargar nota
session_cass.execute("""
    INSERT INTO registro_auditoria 
    (id_estudiante, fecha_creacion, id_auditoria, tipo_accion, nota_original)
    VALUES (%s, toTimestamp(now()), uuid(), %s, %s)
""", (est_id, f"CARGA_{tipo_nota.upper()}", str(valor)))
```

#### 3. **`reportes_geograficos`** (futuro)
- Pre-agregaciones por región
- COUNTER para acumulados

### Características
- ✅ **Append-only**: Datos inmutables para auditoría
- ✅ **TIMEUUID**: Ordenamiento temporal eficiente
- ✅ **Escalabilidad horizontal**: Distribución automática
- ✅ **Consistencia eventual**: Aceptable para analytics

---

## 5. Flujos de Datos Completos

### Flujo 1: Crear Estudiante

```
1. MongoDB
   └─ INSERT INTO estudiantes {legajo, nombre, apellido, email}
   └─ Retorna: mongo_id

2. Cassandra (paralelo)
   └─ INSERT INTO entity_metadata (estudiante, mongo_id, ACTIVO)

3. Neo4j (paralelo)
   └─ MERGE (e:Estudiante {id_mongo: mongo_id})
   └─ SET e.nombre = nombre

Resultado: Datos sincronizados en 3 bases de datos
```

### Flujo 2: Registrar Calificación

```
1. MongoDB
   └─ INSERT INTO calificaciones {
        estudiante_id,
        materia_id,
        valor_original: {nota, tipo}
      }

2. Neo4j
   └─ MATCH (e:Estudiante)-[r:CURSANDO]->(m:Materia)
   └─ SET r.{tipo_nota} = valor

3. Cassandra
   └─ INSERT INTO registro_auditoria (id_estudiante, tipo_accion, nota_original)

Resultado: Calificación registrada + relación actualizada + auditoría
```

### Flujo 3: Aplicar Conversión de Nota

```
1. Redis (lectura)
   └─ GET regla:{codigo_regla}
   └─ Si no existe → MongoDB (fallback)

2. MongoDB (lectura)
   └─ GET calificaciones WHERE _id = calificacion_id

3. Cálculo (aplicación)
   └─ Mapeo: nota_origen → nota_destino

4. MongoDB (escritura)
   └─ UPDATE calificaciones
   └─ $push conversiones_aplicadas[] {
        regla, valor_convertido, fecha
      }

Resultado: Conversión aplicada y registrada (append-only)
```

### Flujo 4: Cerrar Cursada (Evaluar Aprobación)

```
1. Neo4j (lectura)
   └─ MATCH (e:Estudiante)-[r:CURSANDO]->(m:Materia)
   └─ Leer: r.final, r.previo

2. Neo4j (evaluación)
   └─ Calcular estado: final >= 6 OR previo >= 6 → APROBADO

3. Neo4j (escritura)
   └─ CREATE (e)-[r2:CURSÓ]->(m)
   └─ SET r2 = properties(r) + estado + fecha_cierre
   └─ DELETE r (relación CURSANDO)

Resultado: Cursada cerrada, relación histórica creada
```

---

## 6. Patrones de Consistencia

### 1. **Dual Write Pattern**
Cuando se crea/modifica una entidad, se escribe en MongoDB y Neo4j simultáneamente.

**Ventajas:**
- Cada BD mantiene su modelo optimizado
- Consultas rápidas en ambas

**Desventajas:**
- Posible inconsistencia temporal si una escritura falla
- No hay transacciones distribuidas

**Mitigación:**
- Validación de conexiones al inicio
- Manejo de errores con rollback manual si es crítico

### 2. **Cache-Aside Pattern**
Redis como caché de lectura con fallback a MongoDB.

**Flujo:**
```
1. Leer de Redis
2. Si miss → Leer de MongoDB
3. Escribir en Redis para próxima vez
```

### 3. **Append-Only Pattern**
Cassandra para auditoría: solo escrituras, nunca modificaciones.

**Ventajas:**
- Inmutabilidad garantizada
- Historial completo
- Escalabilidad para escrituras masivas

### 4. **Eventual Consistency**
Cassandra puede tener retraso en replicación, pero es aceptable para analytics.

---

## 7. Estrategias de Sincronización

### Sincronización MongoDB ↔ Neo4j

**Al crear entidad:**
- MongoDB: Documento completo
- Neo4j: Nodo con `id_mongo` como referencia

**Al actualizar:**
- MongoDB: Update del documento
- Neo4j: Update del nodo (si aplica)

**Al eliminar:**
- MongoDB: Soft delete (`metadata.estado = INACTIVO`)
- Neo4j: DELETE nodo o marcarlo

### Sincronización MongoDB ↔ Redis

**Al crear regla:**
- MongoDB: Insert
- Redis: SET con TTL

**Al leer regla:**
- Redis primero (cache hit)
- MongoDB si miss (y luego cachear)

### Sincronización MongoDB ↔ Cassandra

**Al crear entidad:**
- MongoDB: Documento (datos)
- Cassandra: Metadatos (estado, timestamps)

**Al registrar acción:**
- MongoDB: Puede o no almacenar
- Cassandra: Siempre registra (auditoría)

---

## 8. Consideraciones de Diseño

### Separación de Concerns

1. **MongoDB**: Datos transaccionales, documentos estructurados
2. **Neo4j**: Relaciones y navegación de grafos
3. **Redis**: Caché temporal para rendimiento
4. **Cassandra**: Metadatos y auditoría inmutable

### Identificadores

- **MongoDB**: `_id` (ObjectId) como identificador principal
- **Neo4j**: `id_mongo` como referencia al documento MongoDB
- **Cassandra**: Claves compuestas según patrón de consulta

### Consistencia vs. Rendimiento

- **MongoDB + Neo4j**: Consistencia fuerte (escrituras síncronas)
- **Redis**: Consistencia eventual (TTL + invalidación)
- **Cassandra**: Consistencia eventual (aceptable para analytics)

### Escalabilidad

- **MongoDB**: Sharding horizontal
- **Neo4j**: Clustering (Causal Cluster)
- **Redis**: Redis Cluster
- **Cassandra**: Distribución automática (RF=1 en desarrollo)

---

## 9. Ejemplos de Consultas

### Consulta 1: Historial de Estudiante (MongoDB)
```python
db.calificaciones.find({"estudiante_id": ObjectId(uid)})
```

### Consulta 2: Trayectoria Completa (Neo4j)
```cypher
MATCH (e:Estudiante {id_mongo: $id})-[r:CURSÓ]->(m:Materia)
RETURN m.nombre, r.estado, r.fecha_cierre
ORDER BY r.fecha_cierre DESC
```

### Consulta 3: Regla de Conversión (Redis → MongoDB)
```python
# Intento 1: Redis
rule = redis.get(f"regla:{codigo}")

# Intento 2: MongoDB (fallback)
if not rule:
    rule = db.reglas_conversion.find_one({"codigo_regla": codigo})
```

### Consulta 4: Auditoría de Estudiante (Cassandra)
```python
session.execute("""
    SELECT * FROM registro_auditoria 
    WHERE id_estudiante = %s
    ORDER BY fecha_creacion DESC
""", (est_id,))
```

---

## 10. Mejores Prácticas

### ✅ DO

1. **Usar MongoDB** para CRUD transaccional
2. **Usar Neo4j** para consultas de relaciones
3. **Cachear en Redis** datos de lectura frecuente
4. **Auditar en Cassandra** todas las acciones críticas
5. **Mantener `id_mongo`** como referencia entre MongoDB y Neo4j
6. **Usar soft delete** en MongoDB, hard delete en Neo4j si es necesario

### ❌ DON'T

1. **No duplicar** toda la lógica en múltiples bases de datos
2. **No usar Redis** para datos permanentes (solo caché)
3. **No modificar** datos de auditoría en Cassandra
4. **No crear** relaciones complejas en MongoDB (usar Neo4j)
5. **No olvidar** sincronizar MongoDB y Neo4j en escrituras

---

## 11. Troubleshooting

### Problema: Inconsistencia entre MongoDB y Neo4j

**Solución:**
- Verificar que ambas escrituras se ejecuten
- Implementar retry logic si una falla
- Considerar transacciones distribuidas (2PC) si es crítico

### Problema: Cache desactualizado en Redis

**Solución:**
- Reducir TTL
- Invalidar cache al actualizar datos
- Usar versionado de claves

### Problema: Cassandra no disponible

**Solución:**
- El sistema continúa funcionando (Cassandra es opcional)
- Los metadatos se pueden almacenar temporalmente en MongoDB
- Re-sincronizar cuando Cassandra esté disponible

---

## 12. Referencias

- **MongoDB**: Documentación oficial de PyMongo
- **Neo4j**: Cypher Query Language Reference
- **Redis**: Redis Python Client (redis-py)
- **Cassandra**: DataStax Python Driver

---

**Última actualización:** 2024
**Versión del documento:** 1.0

