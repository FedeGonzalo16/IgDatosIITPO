"""
ENTIDADES Y ESTRUCTURAS DE DATOS EN REDIS

Redis se utiliza para:
1. Caché de reglas de conversión (acceso rápido)
2. Gestión de sesiones de estudiantes
3. Auditoría de conversiones aplicadas
4. Caché de datos de estudiantes

KEYS Y ESTRUCTURAS:
"""

# ==========================================
# CONVERSIONES
# ==========================================

# conversion:{codigo_regla}
# STRING (JSON)
# TTL: 7 días (604800 segundos)
# Almacena la regla completa de conversión para acceso rápido
CONVERSION_EXAMPLE = {
    "_id": "507f1f77bcf86cd799439015",
    "codigo_regla": "CONV-UK-AR-v1",
    "sistema_origen": "GB",
    "sistema_destino": "AR",
    "version_regla": "1.0",
    "escala_origen": ["A*", "A", "B", "C", "D", "E", "F"],
    "escala_destino": {"tipo": "numerica", "min": 1, "max": 10, "aprobado": 6},
    "mapeo": [
        {"nota_origen": "A*", "nota_destino": 9.2},
        {"nota_origen": "A", "nota_destino": 8.5},
        {"nota_origen": "F", "nota_destino": 2.0}
    ],
    "normativa_asociada": "Resolución Ministerial 456/2023",
    "metadata": {
        "vigencia_desde": "2023-01-01T00:00:00Z",
        "vigencia_hasta": None,
        "estado": "VIGENTE"
    }
}


# ==========================================
# AUDITORÍA DE CONVERSIONES
# ==========================================

# conversion_audit:{calificacion_id}
# LIST (JSON elements)
# TTL: 30 días (2592000 segundos)
# Almacena historial de cada conversión aplicada a una calificación
CONVERSION_AUDIT_EXAMPLE = {
    "regla_id": "507f1f77bcf86cd799439015",
    "codigo_regla": "CONV-UK-AR-v1",
    "sistema_origen": "GB",
    "sistema_destino": "AR",
    "valor_original": "A*",
    "valor_convertido": 9.2,
    "fecha_conversion": "2024-01-15T14:30:00",
    "convertido_por": "usuario_123"
}


# ==========================================
# SESIONES DE ESTUDIANTES
# ==========================================

# session:{session_id}
# STRING (JSON)
# TTL: 24 horas (86400 segundos)
# Información de sesión activa del estudiante
SESSION_EXAMPLE = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "estudiante_id_mongo": "507f1f77bcf86cd799439013",
    "legajo": "2024-ARG-001234",
    "nombre": "Juan",
    "apellido": "Pérez",
    "email": "juan@example.com",
    "fecha_creacion": "2024-01-15T09:00:00",
    "ultimo_acceso": "2024-01-15T14:30:00",
    "estado": "ACTIVA"
}

# student_session:{estudiante_id_mongo}
# STRING (session_id)
# TTL: 24 horas
# Índice rápido para obtener la sesión activa de un estudiante
# Valor: "550e8400-e29b-41d4-a716-446655440000"


# ==========================================
# CACHÉ DE ESTUDIANTES
# ==========================================

# student:{estudiante_id_mongo}
# STRING (JSON)
# TTL: 7 días (604800 segundos)
# Datos básicos del estudiante para acceso rápido
STUDENT_CACHE_EXAMPLE = {
    "id_mongo": "507f1f77bcf86cd799439013",
    "legajo": "2024-ARG-001234",
    "nombre": "Juan",
    "apellido": "Pérez",
    "email": "juan@example.com",
    "pais": "AR",
    "fecha_cache": "2024-01-15T09:00:00"
}


# ==========================================
# PATRONES DE KEYS
# ==========================================

PATTERNS = {
    "conversiones": "conversion:*",  # Todas las reglas
    "auditoria": "conversion_audit:*",  # Auditoría de todas las conversiones
    "sesiones": "session:*",  # Todas las sesiones activas
    "estudiantes_cache": "student:*",  # Todos los estudiantes cacheados
    "indices_sesion": "student_session:*"  # Índices de sesiones por estudiante
}


# ==========================================
# OPERACIONES BÁSICAS
# ==========================================

"""
CREAR SESIÓN:
    POST /api/redis/sesiones
    {
        "estudiante_id_mongo": "507f1f77bcf86cd799439013",
        "legajo": "2024-ARG-001234",
        "nombre": "Juan",
        "apellido": "Pérez",
        "email": "juan@example.com"
    }
    
    Retorna:
    {
        "session_id": "550e8400-e29b-41d4-a716-446655440000",
        "ttl": 86400
    }

OBTENER SESIÓN:
    GET /api/redis/sesiones/{session_id}
    
CERRAR SESIÓN:
    DELETE /api/redis/sesiones/{session_id}

CARGAR CONVERSIÓN:
    POST /api/redis/conversiones
    {
        "regla_id_mongo": "507f1f77bcf86cd799439015"
    }

APLICAR CONVERSIÓN (y persistir en MongoDB):
    POST /api/redis/conversiones/aplicar
    {
        "calificacion_id_mongo": "507f1f77bcf86cd799439014",
        "codigo_regla": "CONV-UK-AR-v1",
        "convertido_por": "usuario_123"
    }
    
    - Busca la regla en Redis
    - Si no está, la trae de MongoDB y la cachea
    - Obtiene la calificación de MongoDB
    - Aplica la conversión
    - Registra en auditoría (Redis)
    - Persiste en MongoDB (conversiones_aplicadas)

OBTENER AUDITORÍA:
    GET /api/redis/conversiones/auditoria/{calificacion_id}
    
    Retorna historial completo de conversiones aplicadas
"""
