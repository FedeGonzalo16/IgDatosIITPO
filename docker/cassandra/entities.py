"""
CASSANDRA DATA ENTITIES & PATTERNS
Immutable audit trails and analytics for educational data management

This module documents the data structures, patterns, and usage guidelines
for Cassandra in the EduGrade system.

KEY PRINCIPLES:
- Append-only: No UPDATE or DELETE operations (only INSERT)
- Immutable: Timestamps and TIMEUUID ensure full traceability
- Performance: Pre-aggregated tables (COUNTER) eliminate need for aggregation jobs
- Compliance: Hash integrity and audit logs satisfy regulatory requirements
"""

# =============================================================================
# TABLE SCHEMAS
# =============================================================================

CASSANDRA_KEYSPACE = "edugrade_audit"
CASSANDRA_REPLICATION = {"class": "SimpleStrategy", "replication_factor": 3}

# ===== TABLE 1: REPORTES_GEOGRAFICOS =====
# Purpose: Pre-aggregated geographic/institutional analytics
# Use Case: Regional performance trends, institution comparison by year
# 
# Characteristics:
# - Partitioned by REGION (geographic dimension)
# - Clustered by institucion_id, anio_lectivo (DESC)
# - Uses native COUNTER type for atomic increments
# - No aggregation needed: reads pre-computed promedio directly
#
# Schema:
REPORTES_GEOGRAFICOS = {
    "partition_key": ["region"],
    "clustering_key": [("institucion_id", "ASC"), ("anio_lectivo", "DESC")],
    "columns": {
        "region": "TEXT",                      # Partition: CABA, Córdoba, etc.
        "institucion_id": "TEXT",              # Clustering: MongoDB ObjectId
        "anio_lectivo": "INT",                 # Clustering: 2024, 2025
        "acumulado_notas": "DOUBLE",           # SUM of all grades in this cell
        "contador_notas": "COUNTER",           # COUNT of grades (atomic increment)
        "fecha_actualizacion": "TIMESTAMP"     # Last update time
    },
    "use_cases": [
        "GET /api/cassandra/reportes/geograficos?region=CABA&anio_lectivo=2024",
        "Compare promedio = acumulado_notas / contador_notas across regions",
        "Year-over-year trends: 2023 vs 2024 by region"
    ]
}

# ===== TABLE 2: REPORTES_SISTEMAS =====
# Purpose: Cross-educational system comparisons (conversión effectiveness)
# Use Case: Track conversion success between GB/AR/US systems
#
# Schema:
REPORTES_SISTEMAS = {
    "partition_key": ["sistema_educativo"],
    "clustering_key": [("anio_lectivo", "DESC"), ("materia_nombre", "ASC")],
    "columns": {
        "sistema_educativo": "TEXT",           # Partition: 'GB', 'AR', 'US'
        "anio_lectivo": "INT",                 # Clustering: 2024
        "materia_nombre": "TEXT",              # Clustering: 'Matemática'
        "promedio_convertido": "FLOAT",        # Latest average grade in target system
        "contador_registros": "COUNTER",       # Total conversions for this row
        "fecha_actualizacion": "TIMESTAMP"     # Last update
    },
    "use_cases": [
        "Compare effectiveness of conversión rules: GB → AR vs GB → US",
        "Annual benchmarking: How does 2024 GB→AR conversion perform vs 2023?",
        "Subject-level analysis: Which subjects convert best for each system"
    ]
}

# ===== TABLE 3: REGISTRO_AUDITORIA =====
# Purpose: Immutable, append-only audit trail for compliance
# Use Case: Regulatory audits, trazabilidad, dispute resolution
# 
# IMPORTANT: This is the PRIMARY audit log. INSERT ONLY - NO UPDATES/DELETES
# 
# Characteristics:
# - Partitioned by id_estudiante (allows per-student audit history)
# - Clustered by fecha_creacion (DESC), then id_auditoria (DESC)
# - TIMEUUID ensures total ordering even in distributed system
# - Every INSERT is immutable - cannot be changed or deleted
#
# Schema:
REGISTRO_AUDITORIA = {
    "partition_key": ["id_estudiante"],
    "clustering_key": [("fecha_creacion", "DESC"), ("id_auditoria", "DESC")],
    "columns": {
        "id_estudiante": "TEXT",               # Partition: MongoDB ObjectId
        "fecha_creacion": "TIMESTAMP",         # Clustering: When recorded
        "id_auditoria": "TIMEUUID",            # Clustering: Unique, ordered identifier
        "nota_original": "TEXT",               # Original grade value
        "usuario_auditor": "TEXT",             # Who triggered the action
        "tipo_accion": "TEXT",                 # CALIFICACION_REGISTRADA | CONVERSION_APLICADA | CAMBIO_ESTADO
        "descripcion": "TEXT",                 # Human-readable action description
        "hash_integridad": "TEXT",             # SHA256 for integrity verification
        "metadata": "TEXT"                     # JSON: additional context
    },
    "immutability_guarantees": [
        "INSERT ONLY - no UPDATE or DELETE",
        "TIMEUUID ensures total ordering across replicas",
        "Hash integrity allows detecting tampering",
        "Partition by estudiante enables per-student audit trails"
    ],
    "use_cases": [
        "Compliance: Full audit trail for regulatory audits",
        "Dispute resolution: When did grade change happen?",
        "Trazabilidad: Who changed what and when?",
        "Forensics: Detect unauthorized modifications (hash mismatch)"
    ]
}

# ===== TABLE 4: AUDITORIA_POR_FECHA =====
# Purpose: Optimized index for time-range queries
# Use Case: Find all audits in date range (e.g., 2024-01-01 to 2024-01-31)
#
# Schema:
AUDITORIA_POR_FECHA = {
    "partition_key": ["fecha_creacion"],
    "clustering_key": [("id_auditoria", "DESC")],
    "columns": {
        "fecha_creacion": "TIMESTAMP",         # Partition: Enables range queries
        "id_auditoria": "TIMEUUID",            # Clustering: Ordered within date
        "id_estudiante": "TEXT",               # Denormalized from primary audit
        "tipo_accion": "TEXT",                 # Allows filtering after fetch
        "usuario_auditor": "TEXT"              # Allows filtering after fetch
    },
    "use_cases": [
        "Find all audits between 2024-01-01 and 2024-01-31",
        "Historical analysis: Spike detection in modifications",
        "Compliance: Evidence of monitoring during specific period"
    ]
}

# ===== TABLE 5: ANALYTICS_APROBACION =====
# Purpose: Approval rate analytics by country/level
# Use Case: Educational ministry metrics, approval trend analysis
#
# Schema:
ANALYTICS_APROBACION = {
    "partition_key": ["pais", "nivel_educativo"],
    "clustering_key": [("anio_lectivo", "DESC")],
    "columns": {
        "pais": "TEXT",                        # Partition: 'AR', 'BR', 'MX'
        "nivel_educativo": "TEXT",             # Partition: 'PRIMARIO', 'SECUNDARIO', 'UNIVERSITARIO'
        "anio_lectivo": "INT",                 # Clustering: 2024
        "total_calificaciones": "COUNTER",     # Count of all grades
        "total_aprobadas": "COUNTER",          # Count of passing grades (>= 6.0)
        "promedio_notas": "FLOAT"              # Average grade value
    },
    "metrics": {
        "tasa_aprobacion": "total_aprobadas / total_calificaciones * 100",
        "promedio": "promedio_notas"
    },
    "use_cases": [
        "Ministry dashboard: Approval rates by country and level",
        "Trend analysis: How approval rates changed year-over-year",
        "Benchmarking: Compare 2024 SECUNDARIO approval rate across countries"
    ]
}

# ===== TABLE 6: DISTRIBUCION_NOTAS =====
# Purpose: Grade distribution histograms
# Use Case: Identify grade inflation, assess assessment quality
#
# Schema:
DISTRIBUCION_NOTAS = {
    "partition_key": ["pais", "nivel_educativo"],
    "clustering_key": [("anio_lectivo", "DESC"), ("rango_nota", "ASC")],
    "columns": {
        "pais": "TEXT",                        # Partition: Country
        "nivel_educativo": "TEXT",             # Partition: Education level
        "anio_lectivo": "INT",                 # Clustering: Year
        "rango_nota": "TEXT",                  # Clustering: '0-3' | '3-6' | '6-7' | '7-8' | '8-9' | '9-10'
        "cantidad": "COUNTER",                 # Count in this range
        "porcentaje": "FLOAT"                  # Percentage of total
    },
    "use_cases": [
        "Distribution shape: Normal vs bimodal (potential grade inflation)",
        "Quality assurance: Too many 10s indicate assessment leniency",
        "Policy analysis: Compare distributions across regions"
    ]
}

# =============================================================================
# WRITE PATTERNS: DUAL PERSISTENCE
# =============================================================================

"""
PATTERN: Dual Persistence (MongoDB + Cassandra)

When a new calificación is registered:
1. Write to MongoDB calificaciones collection (primary, transactional)
2. Write to Cassandra reportes_geograficos (analytics)
3. Write to Cassandra registro_auditoria (compliance)

When conversión is applied:
1. Update MongoDB calificaciones.conversiones_aplicadas (APPEND)
2. Update Cassandra reportes_sistemas (analytics)
3. Append to Cassandra registro_auditoria (audit trail)
4. Push to Redis conversion_audit:{calif_id} LIST (ephemeral tracking)

Code Pattern:
    # 1. Write to MongoDB
    col_calificaciones.update_one(
        {"_id": calif_id},
        {"$push": {"conversiones_aplicadas": conversion_record}}
    )
    
    # 2. Write to Cassandra analytics
    session.execute(
        "UPDATE reportes_sistemas SET contador_registros = contador_registros + 1 ...",
        (sistema, anio, materia)
    )
    
    # 3. Write to Cassandra audit
    session.execute(
        "INSERT INTO registro_auditoria (...) VALUES (...)",
        (est_id, fecha, timeuuid, nota, usuario, tipo_accion, desc, hash, meta)
    )
    
    # 4. Write to Redis LIST (optional, for ephemeral tracking)
    r.lpush(f"conversion_audit:{calif_id}", json.dumps(audit_record))

This ensures:
- MongoDB: Transactional consistency for the core grade record
- Redis: High-speed queries for recent conversions + session management
- Cassandra: Immutable compliance log + pre-aggregated analytics
"""

# =============================================================================
# QUERY PATTERNS
# =============================================================================

QUERY_PATTERNS = {
    "geographic_analytics": {
        "description": "Compare institutions by region and year",
        "query": "SELECT * FROM reportes_geograficos WHERE region = ? AND anio_lectivo = ?",
        "example": "Report on all CABA institutions for 2024"
    },
    
    "approval_rate": {
        "description": "Get approval rate (%, count) by country/level/year",
        "query": "SELECT * FROM analytics_aprobacion WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ?",
        "example": "78% approval rate in secondary education in Argentina 2024"
    },
    
    "grade_distribution": {
        "description": "Histogram of grades by country/level/year",
        "query": "SELECT * FROM distribucion_notas WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ?",
        "example": "Grade distribution: 15% (9-10), 25% (8-9), 35% (6-8), 25% (< 6)"
    },
    
    "student_audit_trail": {
        "description": "Get all auditable actions for a student (append-only)",
        "query": "SELECT * FROM registro_auditoria WHERE id_estudiante = ? LIMIT ?",
        "example": "All changes to student 507f1f77bcf86cd799439013"
    },
    
    "audit_by_date_range": {
        "description": "Get all audits between two dates",
        "query": "SELECT * FROM auditoria_por_fecha WHERE fecha_creacion >= ? AND fecha_creacion <= ? LIMIT ?",
        "example": "All audits during January 2024 compliance period"
    },
    
    "conversion_effectiveness": {
        "description": "Compare conversion success across systems",
        "query": "SELECT * FROM reportes_sistemas WHERE sistema_educativo = ? AND anio_lectivo = ?",
        "example": "How successful was GB → AR conversion in 2024?"
    }
}

# =============================================================================
# DATA INTEGRITY PATTERNS
# =============================================================================

"""
HASH INTEGRITY for Audit Records

Every audit entry includes hash_integridad = SHA256(...)
This enables detection of tampering. Even though Cassandra is immutable,
the hash allows verification that the original data hasn't been modified.

SHA256 is computed over:
{
    "id_estudiante": "...",
    "tipo_accion": "CALIFICACION_REGISTRADA",
    "fecha_creacion": "2024-01-15T10:30:00",
    "usuario_auditor": "profesor_123",
    "nota_original": "8.5"
}

If an attacker modifies one of these fields (even in another replica),
the hash won't match, revealing tampering.

APPEND-ONLY GUARANTEE

Cassandra ensures immutability through:
1. INSERT ONLY semantics (no UPDATE/DELETE on registro_auditoria)
2. Replication RF=3 means 3 copies - must corrupt all to hide tampering
3. TIMEUUID clustering ensures total ordering globally
4. Cassandra's WAL (write-ahead logs) persist before acknowledging

Therefore, once an audit record is INSERTed and acknowledged, it cannot be:
- Modified (CQL doesn't support UPDATE/DELETE on this table)
- Deleted from all replicas (would require quorum corruption)
- Reordered (TIMEUUID prevents this)

COUNTER DATA TYPE

native COUNTER type in Cassandra provides:
- Atomic increments (no race conditions)
- Replication-aware (+1 across replicas = +1 globally)
- No aggregation needed (pre-computed counters)

Example: contador_notas in reportes_geograficos
Instead of: SELECT COUNT(*) WHERE region=? AND institucion=? AND anio=?
We do: SELECT contador_notas FROM reportes_geograficos WHERE ...
Result: O(1) query vs O(n) aggregation
"""

# =============================================================================
# CONSISTENCY GUARANTEES
# =============================================================================

CONSISTENCY_MODEL = {
    "mongodb": {
        "type": "ACID transactions",
        "guarantees": "Strong consistency, CRUD operations on single documents",
        "use_case": "Primary grade storage, single source of truth"
    },
    
    "cassandra": {
        "type": "Eventually consistent (by design)",
        "guarantees": "Immutability trumps consistency; all 3 replicas have same immutable data",
        "replication_factor": 3,
        "read_strategy": "Read from any replica (all have same data immutably)",
        "use_case": "Audit trails and analytics (immutability > consistency)"
    },
    
    "redis": {
        "type": "In-memory, single node",
        "guarantees": "Strong consistency for session and audit cache",
        "ttl_auto_cleanup": True,
        "use_case": "Ephemeral audit tracking, session management"
    }
}

# =============================================================================
# PERFORMANCE CHARACTERISTICS
# =============================================================================

PERFORMANCE_AT_SCALE = {
    "analytics_without_degradation": {
        "problem": "1M records shouldn't slow down analytics",
        "solution": "Pre-aggregated tables (COUNTER) eliminate aggregation jobs",
        "query_time": "O(1) - read single row",
        "example": "Get 2024 promedio for 100 institutions: 100 queries × O(1) = instant"
    },
    
    "instant_dimensional_filtering": {
        "problem": "Filter by region, year, system instantaneously",
        "solution": "Design partition keys as primary filter dimensions",
        "example_1": "reportes_geograficos partitioned by region",
        "example_2": "analytics_aprobacion partitioned by (pais, nivel_educativo)"
    },
    
    "efficient_sequential_reads": {
        "problem": "Time-range queries need efficient sequential access",
        "solution": "TIMEUUID clustering in DESC order",
        "example": "SELECT FROM registro_auditoria WHERE id_est=? -- reads newest first",
        "benefit": "Pagination: skip N and take M = instant (doesn't scan full table)"
    }
}

# =============================================================================
# OPERATIONAL PATTERNS
# =============================================================================

"""
TTL (Time-To-Live) Policies
- registro_auditoria: NO TTL (immutable, permanent)
- reportes_geograficos: NO TTL (permanent analytics)
- reportes_sistemas: NO TTL (permanent conversion records)
- auditoria_por_fecha: Optional TTL if only keeping recent audit index

Background processes:
- ETL from MongoDB → Cassandra: 
  - On each POST /api/v1/calificaciones: write to reportes_geograficos
  - On each POST /api/redis/conversiones/aplicar: write to reportes_sistemas
  - ALWAYS append to registro_auditoria (never skip audit)
  
Backups:
- Cassandra snapshots should be automated
- All data is append-only, safe to restore from snapshots
"""
