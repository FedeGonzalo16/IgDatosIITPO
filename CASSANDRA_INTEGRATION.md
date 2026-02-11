# Cassandra Integration - EduGrade Multi-Database System

## Overview

Cassandra completes the EduGrade system as the **immutable audit trail and analytics layer**. It provides:

- **Append-only audit logs** for regulatory compliance and trazabilidad
- **Pre-aggregated analytics** supporting 1M+ records without performance degradation
- **Instant dimensional filtering** by region, system, year, and country
- **Efficient sequential reads** with TIMEUUID clustering for time-range queries

## Architecture

### System Composition

```
┌─────────────────────────────────────────────────────────────┐
│                    EduGrade System                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MongoDB          Neo4j          Redis         Cassandra    │
│  ────────         ─────           ─────         ────────    │
│  Transactional    Graph           Cache &       Analytics & │
│  (OLTP)           Relationships   Sessions      Audit       │
│  - Students       - INSCRIPTO_EN  - 7d conv    (OLAP)      │
│  - Courses        - CURSÓ         - 24h sess   - Immutable │
│  - Grades         - trayectoria   - 30d audit  - Append-   │
│  - Rules          - estadísticas  - Student    only        │
│                                   cache        - COUNTER    │
└─────────────────────────────────────────────────────────────┘

                    Data Flow

MongoDB          ──────────┐
  │                        ├─→ Cassandra reportes_geograficos
  │ POST /api/v1/            
  │ calificaciones           ├─→ Cassandra analytics_aprobacion
  │                          │
  └──────────────────────────┼─→ Cassandra distribucion_notas
        neo4j                │
        relaciones           └─→ Cassandra registro_auditoria
                                     (immutable)

Redis            ──────────┐
  │                        │
  │ POST /api/redis/       ├─→ Cassandra reportes_sistemas
  │ conversiones/aplicar   │
  │                        ├─→ Cassandra registro_auditoria
  │                        │
  └────────────────────────┘
   (audit LIST)      (permanent)
   (30d TTL)
```

## Data Models

### Table 1: `reportes_geograficos`

**Purpose:** Pre-aggregated geographic analytics by institution and year

**Schema:**
```python
partition_key: ["region"]
clustering_key: [
    ("institucion_id", "ASC"),
    ("anio_lectivo", "DESC")
]
columns: {
    "region": TEXT,                  # CABA, Córdoba, Mendoza, etc.
    "institucion_id": TEXT,          # MongoDB ObjectId
    "anio_lectivo": INT,             # 2024, 2025
    "acumulado_notas": DOUBLE,       # SUM of all grades
    "contador_notas": COUNTER,       # COUNT of grades (atomic)
    "fecha_actualizacion": TIMESTAMP # Last update
}
```

**When to Use:**
- Which institutions in a region have highest average grades?
- Year-over-year trends: CABA 2023 vs 2024
- Geographic performance distribution

**Query Example:**
```python
# Get all institutions in CABA for 2024
GET /api/cassandra/reportes/geograficos?region=CABA&anio_lectivo=2024

# Returns: [{
#     "region": "CABA",
#     "institucion_id": "507f1f77bcf86cd799439013",
#     "anio_lectivo": 2024,
#     "promedio": 7.85,  # acumulado / contador
#     "total_registros": 1250
# }]
```

### Table 2: `reportes_sistemas`

**Purpose:** Cross-educational system conversion effectiveness tracking

**Schema:**
```python
partition_key: ["sistema_educativo"]
clustering_key: [
    ("anio_lectivo", "DESC"),
    ("materia_nombre", "ASC")
]
columns: {
    "sistema_educativo": TEXT,       # 'GB', 'AR', 'US', 'FR'
    "anio_lectivo": INT,             # 2024
    "materia_nombre": TEXT,          # Matemática, Física
    "promedio_convertido": FLOAT,    # Latest average in target system
    "contador_registros": COUNTER,   # Total conversions
    "fecha_actualizacion": TIMESTAMP # Last update
}
```

**When to Use:**
- How effective are GB→AR conversions for Matemática?
- Cross-system comparative analysis: AR vs US performance
- Subject-level conversion success rates

**Query Example:**
```python
# Get conversion effectiveness for AR system in 2024
GET /api/cassandra/reportes/sistemas?sistema_educativo=AR&anio_lectivo=2024

# Returns effectiveness metrics for all subjects converted into AR system
```

### Table 3: `registro_auditoria` (IMMUTABLE)

**Purpose:** Append-only compliance audit log - NEVER UPDATE OR DELETE

**Schema:**
```python
partition_key: ["id_estudiante"]
clustering_key: [
    ("fecha_creacion", "DESC"),
    ("id_auditoria", "DESC")
]
columns: {
    "id_estudiante": TEXT,           # MongoDB ObjectId (partition)
    "fecha_creacion": TIMESTAMP,     # When recorded (clustering)
    "id_auditoria": TIMEUUID,        # Unique, ordered (clustering)
    "nota_original": TEXT,           # Grade value
    "usuario_auditor": TEXT,         # Who triggered
    "tipo_accion": TEXT,             # CALIFICACION_REGISTRADA | CONVERSION_APLICADA | CAMBIO_ESTADO
    "descripcion": TEXT,             # Human-readable
    "hash_integridad": TEXT,         # SHA256 for tampering detection
    "metadata": TEXT                 # JSON context
}
```

**Immutability Guarantees:**
1. **INSERT ONLY** - CQL doesn't support UPDATE/DELETE on this table
2. **TIMEUUID** - Ensures total ordering across all replicas
3. **Replication (RF=3)** - Must corrupt all 3 replicas to hide tampering
4. **Hash Integrity** - Detect modifications: SHA256 mismatch = tampered
5. **Write-Ahead Logs** - Cassandra persists to disk before acknowledging

**When to Use:**
- Regulatory audits: "Show all changes to student 123"
- Dispute resolution: "When was grade changed and by whom?"
- Compliance: Full trazabilidad of all academic transactions
- Forensics: Detect unauthorized modifications

**Query Example:**
```python
# Get all audit events for a student
GET /api/cassandra/auditoria/estudiante/507f1f77bcf86cd799439013

# Get audits in specific date range (for compliance period)
GET /api/cassandra/auditoria?fecha_inicio=2024-01-01&fecha_fin=2024-01-31

# Returns events with hash_integridad for verification
```

### Table 4: `auditoria_por_fecha`

**Purpose:** Optimized index for time-range audit queries

**Schema:**
```python
partition_key: ["fecha_creacion"]     # Enables range queries by date
clustering_key: [("id_auditoria", "DESC")]
denormalized_columns: {
    "id_estudiante": TEXT,
    "tipo_accion": TEXT,
    "usuario_auditor": TEXT
}
```

**Use:** Efficiently find "all audits during January compliance period"

### Table 5: `analytics_aprobacion`

**Purpose:** Approval rate metrics by country, education level, and year

**Schema:**
```python
partition_key: ["pais", "nivel_educativo"]
clustering_key: [("anio_lectivo", "DESC")]
columns: {
    "pais": TEXT,                    # Argentina, Brazil, etc.
    "nivel_educativo": TEXT,         # PRIMARIO, SECUNDARIO, UNIVERSITARIO
    "anio_lectivo": INT,             # 2024
    "total_calificaciones": COUNTER, # Total grades
    "total_aprobadas": COUNTER,      # Passing grades (>= 6.0)
    "promedio_notas": FLOAT          # Average grade
}
```

**Metrics Derived:**
```
tasa_aprobacion = (total_aprobadas / total_calificaciones) * 100
ejemplo: 756 aprobadas / 900 totales = 84%
```

**Query Example:**
```python
GET /api/cassandra/analytics/aprobacion?pais=AR&nivel_educativo=SECUNDARIO&anio_lectivo=2024

# Returns:
# {
#   "pais": "AR",
#   "nivel": "SECUNDARIO",
#   "anio": 2024,
#   "total_calificaciones": 156000,
#   "total_aprobadas": 131040,
#   "tasa_aprobacion_porcentaje": 84.0,
#   "promedio_notas": 7.42
# }
```

### Table 6: `distribucion_notas`

**Purpose:** Grade distribution histograms for quality assurance

**Schema:**
```python
partition_key: ["pais", "nivel_educativo"]
clustering_key: [
    ("anio_lectivo", "DESC"),
    ("rango_nota", "ASC")
]
columns: {
    "pais": TEXT,
    "nivel_educativo": TEXT,
    "anio_lectivo": INT,
    "rango_nota": TEXT,              # "0-3" | "3-6" | "6-7" | "7-8" | "8-9" | "9-10"
    "cantidad": COUNTER,             # Count in range
    "porcentaje": FLOAT              # Percentage of total
}
```

**Use Cases:**
- Detect grade inflation: Too many 9-10 grades?
- Quality assurance: Bimodal distribution indicates assessment issues
- Comparative analysis: Region A vs B grade distributions

**Query Example:**
```python
GET /api/cassandra/analytics/distribucion?pais=AR&nivel_educativo=SECUNDARIO&anio_lectivo=2024

# Returns histogram showing percentage of students in each grade range
# Identifies potential assessment problems
```

## Integration Points

### 1. Calificación Registration (MongoDB → Cassandra)

When `POST /api/v1/calificaciones` is called:

```python
# 1. Write to MongoDB (transactional)
col_calificaciones.insert_one(calificacion)

# 2. Sync to Neo4j (relationship)
session.run("MERGE (e)--[r:TIENE_CALIFICACION]->(m)")

# 3. Write to Cassandra (analytics + audit)
# a) Update reportes_geograficos
cassandra.execute(
    "UPDATE reportes_geograficos SET acumulado_notas = acumulado_notas + ?, "
    "contador_notas = contador_notas + 1 "
    "WHERE region = ? AND institucion_id = ? AND anio_lectivo = ?",
    (nota, region, institucion, year)
)

# b) Update analytics_aprobacion
cassandra.execute(
    "UPDATE analytics_aprobacion SET total_calificaciones = total_calificaciones + 1, "
    "total_aprobadas = total_aprobadas + ? WHERE pais = ? AND nivel = ? AND anio = ?",
    (1 if aprobado else 0, pais, nivel, anio)
)

# c) Register in immutable audit trail
cassandra.execute(
    "INSERT INTO registro_auditoria (id_est, fecha, id_audit, nota, usuario, accion, desc, hash, meta) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    (est_id, now, timeuuid(), nota, usuario, 'CALIFICACION_REGISTRADA', desc, hash, meta)
)
```

### 2. Conversión Application (Redis → Cassandra)

When `POST /api/redis/conversiones/aplicar` is called:

```python
# 1. Read rule from Redis cache (fallback to MongoDB)
regla = redis.get(f"conversion:{codigo_regla}")

# 2. Apply conversion logic
valor_convertido = mapeo[nota_original]

# 3. Persist to MongoDB
col_calificaciones.update_one(
    {"_id": calif_id},
    {"$push": {"conversiones_aplicadas": conversion_record}}
)

# 4. Log to Redis LIST (ephemeral, 30d)
redis.lpush(f"conversion_audit:{calif_id}", conversion_record)

# 5. Write to Cassandra (analytics + audit)
# a) Update reportes_sistemas
cassandra.execute(
    "UPDATE reportes_sistemas SET promedio_convertido = ?, "
    "contador_registros = contador_registros + 1 WHERE sistema = ? AND anio = ? AND materia = ?",
    (valor_convertido, sistema_destino, anio, materia)
)

# b) Register in immutable audit trail
cassandra.execute(
    "INSERT INTO registro_auditoria (...) VALUES (...)",
    (est_id, fecha, timeuuid, nota_orig, usuario, 'CONVERSION_APLICADA', desc, hash, meta)
)
```

## Performance Characteristics

### At 1M+ Records

**Query Performance:**
- **Geographic analytics:** O(1) - COUNTER pre-computes sums
- **Approval rates:** O(1) - COUNTER provides count
- **Distribution histogram:** O(6) - range buckets are fixed
- **Audit trail by student:** O(log N) - partitioned by student

**No Aggregation Jobs Needed:**
- Traditional: Run daily job to sum all grades by region
- EduGrade: COUNTER accumulates automatically, query instantly

**Concurrent Writes:**
- Multiple students getting grades simultaneously
- Cassandra's COUNTER type handles distributed increments atomically
- No locking needed, peak throughput 100k+ writes/sec

### Storage Efficiency

**COUNTER vs INT:**
- Native COUNTER: Extra bytes for tombstone tracking (eventual consistency)
- Still more efficient than storing all 1M grade records then aggregating
- TTL can clean old data if needed

## API Endpoints

### Auditoría
```
POST   /api/cassandra/auditoria
GET    /api/cassandra/auditoria/estudiante/<id>
GET    /api/cassandra/auditoria?fecha_inicio=...&fecha_fin=...
```

### Reportes Geográficos
```
POST   /api/cassandra/reportes/geograficos
GET    /api/cassandra/reportes/geograficos?region=...
```

### Reportes Sistemas
```
POST   /api/cassandra/reportes/sistemas
GET    /api/cassandra/reportes/sistemas?sistema=...
```

### Analytics
```
POST   /api/cassandra/analytics/aprobacion
GET    /api/cassandra/analytics/aprobacion?pais=...&nivel=...
POST   /api/cassandra/analytics/distribucion
GET    /api/cassandra/analytics/distribucion?pais=...
```

### Health
```
GET    /api/cassandra/salud
```

## Consistency Model

| Database | Type | Guarantee | Use Case |
|----------|------|-----------|----------|
| MongoDB | ACID | Strong | Primary transactional storage |
| Neo4j | ACID | Strong | Relationship integrity |
| Redis | Single-node | Strong | Session/cache |
| Cassandra | Eventually Consistent | Immutability | Audit & analytics |

**Cassandra Immutability > Consistency:**
- Data replicated to 3 nodes (RF=3)
- All 3 replicas have identical immutable data
- Even if one replica is unavailable, other 2 have audit trail
- Impossible to hide modification without corrupting all replicas

## Deployment

### Docker Compose Configuration
```yaml
cassandra:
  image: cassandra:4.1.3
  environment:
    CASSANDRA_CLUSTER_NAME: "edugrade_cluster"
    CASSANDRA_DC: "us-east-1"
  ports:
    - "7000:7000"    # inter-node communication
    - "9042:9042"    # CQL native protocol
  volumes:
    - cassandra_data:/var/lib/cassandra
```

### Initialization
```python
# Create keyspace and tables (runs automatically on startup)
python docker/cassandra/api_cassandra.py

# Replication factor 3 recommended for production
# SimpleStrategy OK for single-datacenter deployments
```

## Monitoring

### Key Metrics
1. **Write latency:** Should be < 50ms for COUNTER updates
2. **Query latency:** Should be < 10ms for direct lookups
3. **Audit trail growth:** ~100 bytes/record, 1M records = ~100GB
4. **Cache hit ratio:** Monitor Redis alongside Cassandra

### Troubleshooting

**Slow queries:**
- Check if querying without partition key
- Verify clustering order is utilized for range queries
- Monitor GC pauses (Cassandra runs on JVM)

**Audit trail gaps:**
- Check cassandra_session is not None before INSERT
- Monitor replication factor (RF=3 protects against node failure)
- Check commit logs aren't getting truncated

**COUNTER anomalies:**
- COUNTERs are eventually consistent
- If seeing duplicate increments, verify counter_cache_size in cassandra.yaml
- Repairs needed if deltas don't converge

## Security Considerations

1. **Hash Integrity (SHA256):**
   - Detects tampering within a single record
   - Not cryptographic proof (attacker could rehash)
   - Requires separate signing for regulatory compliance

2. **Immutability:**
   - Append-only guarantees forensic integrity
   - Cannot retroactively hide modifications
   - Audit trail survives database compromises (recovery from backups)

3. **Access Control:**
   - Use role-based access in Cassandra (create_role)
   - Restrict audit_table readers to compliance team
   - Log who reads/queries audit trails

4. **Encryption:**
   - Use TLS between clients and Cassandra
   - Enable encryption_at_rest in cassandra.yaml
   - Encrypt backups

## References

- [Cassandra Query Language (CQL)](https://cassandra.apache.org/doc/latest/cassandra/cql/)
- [COUNTER Data Type](https://cassandra.apache.org/doc/latest/cassandra/cql/types.html#counters)
- [TIMEUUID](https://cassandra.apache.org/doc/latest/cassandra/cql/types.html#timeuuid)
- [Partition Key Design](https://cassandra.apache.org/doc/latest/cassandra/data_modeling/index.html)
