from flask import Flask, request, jsonify
import redis
import json
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from cassandra.cluster import Cluster

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE CONEXIONES
# ==========================================

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# Conexión a MongoDB para sincronizar conversiones
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:estudiantes2026@localhost:27017/?authSource=admin')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['edugrade_global']
col_conversiones = db['reglas_conversion']
col_calificaciones = db['calificaciones']
col_materias = db['materias']
col_instituciones = db['instituciones']

# Conexión a Cassandra
CASSANDRA_HOSTS = os.getenv('CASSANDRA_HOSTS', 'localhost').split(',')
CASSANDRA_KEYSPACE = 'edugrade_audit'
try:
    cassandra_cluster = Cluster(CASSANDRA_HOSTS)
    cassandra_session = cassandra_cluster.connect()
    cassandra_session.set_keyspace(CASSANDRA_KEYSPACE)
except Exception as e:
    print(f"[Cassandra] Advertencia: {e}")
    cassandra_session = None

# ==========================================
# UTILIDADES
# ==========================================

def verificar_conexion():
    """Verifica que Redis esté disponible"""
    try:
        r.ping()
        return True
    except Exception as e:
        print(f"[Redis] Error de conexión: {e}")
        return False

def obtener_timeuuid():
    """Obtiene un TIMEUUID actual"""
    from uuid import uuid1
    return uuid1()

def calcular_hash_integridad(datos):
    """Calcula hash SHA256 para integridad de registros"""
    import hashlib
    json_str = json.dumps(datos, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


# ==========================================
# CONVERSIONES: GESTIÓN DE REGLAS
# ==========================================

#Guardar reglas de conversión en Redis para acceso rápido y sincronizar con MongoDB.
@app.route('/api/redis/conversiones', methods=['POST'])
def cargar_conversion_en_redis():
    """
    Cargar una regla de conversión desde MongoDB a Redis (caching)
    {
        "regla_id_mongo": "507f1f77bcf86cd799439015"
    }
    """
    datos = request.json
    
    if not datos or 'regla_id_mongo' not in datos:
        return jsonify({"error": "Campo obligatorio: regla_id_mongo"}), 400
    
    try:
        from bson import ObjectId
        
        # Obtener regla desde MongoDB
        regla = col_conversiones.find_one({'_id': ObjectId(datos['regla_id_mongo'])})
        
        if not regla:
            return jsonify({"error": "Regla de conversión no encontrada en MongoDB"}), 404
        
        codigo_regla = regla.get('codigo_regla')
        
        # Convertir ObjectId a string para JSON
        regla_json = json.dumps({
            '_id': str(regla['_id']),
            'codigo_regla': codigo_regla,
            'sistema_origen': regla.get('sistema_origen'),
            'sistema_destino': regla.get('sistema_destino'),
            'version_regla': regla.get('version_regla'),
            'escala_origen': regla.get('escala_origen'),
            'escala_destino': regla.get('escala_destino'),
            'mapeo': regla.get('mapeo', []),
            'normativa_asociada': regla.get('normativa_asociada'),
            'metadata': regla.get('metadata')
        }, default=str)
        
        # Guardar en Redis con expiración de 7 días
        r.setex(f"conversion:{codigo_regla}", 604800, regla_json)
        
        return jsonify({
            "mensaje": "Regla cargada en Redis",
            "codigo_regla": codigo_regla,
            "sistema": f"{regla.get('sistema_origen')} → {regla.get('sistema_destino')}"
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener regla de conversión desde Redis para aplicación rápida en conversiones. 
@app.route('/api/redis/conversiones/<codigo_regla>', methods=['GET'])
def obtener_conversion_redis(codigo_regla):
    """
    Obtener regla de conversión desde Redis (caché rápido)
    """
    try:
        regla_json = r.get(f"conversion:{codigo_regla}")
        
        if not regla_json:
            return jsonify({"error": "Regla no encontrada en caché Redis", "disponible": False}), 404
        
        regla = json.loads(regla_json)
        
        return jsonify({
            "regla": regla,
            "disponible": True,
            "ttl": r.ttl(f"conversion:{codigo_regla}")
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Listar todas las reglas de conversión disponibles en Redis para monitoreo y administración.
@app.route('/api/redis/conversiones', methods=['GET'])
def listar_conversiones_redis():
    """
    Listar todas las conversiones en caché
    """
    try:
        claves = r.keys("conversion:*")
        conversiones = []
        
        for clave in claves:
            regla_json = r.get(clave)
            if regla_json:
                regla = json.loads(regla_json)
                conversiones.append({
                    "codigo": regla['codigo_regla'],
                    "origen": regla['sistema_origen'],
                    "destino": regla['sistema_destino'],
                    "ttl": r.ttl(clave)
                })
        
        #devolvemos la lista de conversiones con su código, sistemas involucrados y tiempo de vida restante en caché
        return jsonify({
            "total": len(conversiones),
            "conversiones": conversiones
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


#Eliminar una regla de conversión del caché de Redis
@app.route('/api/redis/conversiones/<codigo_regla>', methods=['DELETE'])
def eliminar_conversion_redis(codigo_regla):
    """
    Eliminar regla de conversión del caché
    """
    try:
        resultado = r.delete(f"conversion:{codigo_regla}")
        
        if resultado == 0:
            return jsonify({"error": "Regla no encontrada"}), 404
        
        return jsonify({"mensaje": "Regla eliminada del caché"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# CONVERSIONES: APLICAR Y REGISTRAR
# ==========================================

# Aplicar una conversión a una calificación y registrar el resultado en MongoDB, Redis (auditoría) y Cassandra (reportes y auditoría inmutable).
@app.route('/api/redis/conversiones/aplicar', methods=['POST'])
def aplicar_conversion():
    """
    Aplicar una conversión a una calificación y persistir el resultado en MongoDB y Cassandra
    {
        "calificacion_id_mongo": "507f1f77bcf86cd799439014",
        "codigo_regla": "CONV-UK-AR-v1",
        "convertido_por": "usuario_123"
    }
    """
    datos = request.json
    
    if not datos or 'calificacion_id_mongo' not in datos or 'codigo_regla' not in datos:
        return jsonify({"error": "Campos requeridos: calificacion_id_mongo, codigo_regla"}), 400
    
    try:
        from bson import ObjectId
        
        calificacion_id = datos['calificacion_id_mongo']
        codigo_regla = datos['codigo_regla']
        convertido_por = datos.get('convertido_por', 'sistema')
        
        # Obtener regla desde Redis
        regla_json = r.get(f"conversion:{codigo_regla}")
        
        if not regla_json:
            # Si no está en caché, intentar traerla desde MongoDB
            regla_db = col_conversiones.find_one({'codigo_regla': codigo_regla})
            if not regla_db:
                return jsonify({"error": "Regla de conversión no encontrada"}), 404
            
            # Cargarla en Redis para futuras consultas
            regla_json = json.dumps({
                '_id': str(regla_db['_id']),
                'codigo_regla': codigo_regla,
                'sistema_origen': regla_db.get('sistema_origen'),
                'sistema_destino': regla_db.get('sistema_destino'),
                'version_regla': regla_db.get('version_regla'),
                'escala_origen': regla_db.get('escala_origen'),
                'escala_destino': regla_db.get('escala_destino'),
                'mapeo': regla_db.get('mapeo', []),
                'normativa_asociada': regla_db.get('normativa_asociada'),
                'metadata': regla_db.get('metadata')
            }, default=str)
            r.setex(f"conversion:{codigo_regla}", 604800, regla_json)
        
        regla = json.loads(regla_json)
        
        # Obtener calificación original
        if not ObjectId.is_valid(calificacion_id):
            return jsonify({"error": "ID de calificación inválido"}), 400
        
        calificacion = col_calificaciones.find_one({'_id': ObjectId(calificacion_id)})
        
        if not calificacion:
            return jsonify({"error": "Calificación no encontrada"}), 404
        
        # Obtener valor original
        nota_original = calificacion['valor_original']['nota']
        
        # Buscar equivalencia en mapeo
        valor_convertido = None
        for mapeo in regla.get('mapeo', []):
            if str(mapeo.get('nota_origen')) == str(nota_original):
                valor_convertido = mapeo.get('nota_destino')
                break
        
        if valor_convertido is None:
            return jsonify({
                "error": f"No existe equivalencia para {nota_original} en escala {regla['sistema_origen']}"
            }), 400
        
        # Registrar conversión en auditoría de Redis
        conversion_record = {
            "regla_id": regla['_id'],
            "codigo_regla": codigo_regla,
            "sistema_origen": regla['sistema_origen'],
            "sistema_destino": regla['sistema_destino'],
            "valor_original": nota_original,
            "valor_convertido": valor_convertido,
            "fecha_conversion": datetime.utcnow().isoformat(),
            "convertido_por": convertido_por
        }
        
        # Agregar a la auditoría de conversiones en Redis
        r.lpush(
            f"conversion_audit:{calificacion_id}",
            json.dumps(conversion_record, default=str)
        )
        r.expire(f"conversion_audit:{calificacion_id}", 2592000)  # 30 días
        
        # Persistir en MongoDB
        col_calificaciones.update_one(
            {'_id': ObjectId(calificacion_id)},
            {
                '$push': {
                    'conversiones_aplicadas': {
                        'regla_id': ObjectId(regla['_id']),
                        'sistema_destino': regla['sistema_destino'],
                        'valor_convertido': valor_convertido,
                        'fecha_conversion': datetime.utcnow(),
                        'convertido_por': convertido_por
                    }
                },
                '$set': {
                    'metadata.updated_at': datetime.utcnow()
                }
            }
        )
        
        # ===== Escribir en Cassandra =====
        if cassandra_session:
            try:
                # Obtener materia e institución para contexto
                materia = col_materias.find_one({'_id': ObjectId(calificacion['materia_id'])}) if 'materia_id' in calificacion else None
                institucion = None
                if materia and 'institucion_id' in materia:
                    institucion = col_instituciones.find_one({'_id': ObjectId(materia['institucion_id'])})
                
                anio_lectivo = datetime.utcnow().year
                materia_nombre = materia.get('nombre', 'N/A') if materia else 'N/A'
                
                # 1. Registrar en reportes_sistemas para cálculos de promedio y estadísticas
                cassandra_session.execute(
                    f"""
                    UPDATE {CASSANDRA_KEYSPACE}.reportes_sistemas
                    SET promedio_convertido = ?,
                        contador_registros = contador_registros + 1,
                        fecha_actualizacion = ?
                    WHERE sistema_educativo = ? AND anio_lectivo = ? AND materia_nombre = ?
                    """,
                    (float(valor_convertido), datetime.utcnow(),
                     regla['sistema_destino'], anio_lectivo, materia_nombre)
                )
                
                # 2. Registrar en audit trail inmutable
                fecha_creacion = datetime.utcnow()
                id_auditoria = obtener_timeuuid()
                
                datos_integridad = {
                    "id_estudiante": str(calificacion['estudiante_id']),
                    "tipo_accion": "CONVERSION_APLICADA",
                    "fecha_creacion": fecha_creacion.isoformat(),
                    "usuario_auditor": convertido_por,
                    "nota_original": nota_original
                }
                hash_integridad = calcular_hash_integridad(datos_integridad)
                
                metadata_audit = {
                    "regla_id": regla['_id'],
                    "sistema_origen": regla['sistema_origen'],
                    "sistema_destino": regla['sistema_destino'],
                    "valor_convertido": valor_convertido,
                    "materia": materia_nombre
                }
                
                #lo persistimos en la tabla de auditoría inmutable con toda la información relevante para trazabilidad y reportes futuros
                cassandra_session.execute(
                    f"""
                    INSERT INTO {CASSANDRA_KEYSPACE}.registro_auditoria
                    (id_estudiante, fecha_creacion, id_auditoria, nota_original, usuario_auditor, 
                     tipo_accion, descripcion, hash_integridad, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (str(calificacion['estudiante_id']), fecha_creacion, id_auditoria,
                     str(nota_original),
                     convertido_por,
                     'CONVERSION_APLICADA',
                     f"Conversión: {regla['sistema_origen']} → {regla['sistema_destino']}: {nota_original} → {valor_convertido}",
                     hash_integridad,
                     json.dumps(metadata_audit, default=str))
                )
                
                # Indexamos por fecha también
                cassandra_session.execute(
                    f"""
                    INSERT INTO {CASSANDRA_KEYSPACE}.auditoria_por_fecha
                    (fecha_creacion, id_auditoria, id_estudiante, tipo_accion, usuario_auditor)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (fecha_creacion, id_auditoria, str(calificacion['estudiante_id']),
                     'CONVERSION_APLICADA', convertido_por)
                )
            
            except Exception as e:
                print(f"[Cassandra] Error escribiendo conversión: {e}")
        
        return jsonify({
            "mensaje": "Conversión aplicada y persistida",
            "calificacion_id": calificacion_id,
            "valor_original": nota_original,
            "regla": codigo_regla,
            "valor_convertido": valor_convertido,
            "sistema_destino": regla['sistema_destino']
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Obtener historial de conversiones aplicadas a una calificación desde Redis para auditoría rápida - Ver
@app.route('/api/redis/conversiones/auditoria/<calificacion_id>', methods=['GET'])
def obtener_auditoria_conversiones(calificacion_id):
    """
    Obtener historial de todas las conversiones aplicadas a una calificación
    """
    try:
        # Obtener desde Redis
        auditorias = r.lrange(f"conversion_audit:{calificacion_id}", 0, -1)
        
        historial = [json.loads(audit) for audit in auditorias]
        
        return jsonify({
            "calificacion_id": calificacion_id,
            "total_conversiones": len(historial),
            "historial": historial
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# SESIONES: GESTIÓN DE ESTUDIANTES
# ==========================================

# Crear sesión de estudiante en Redis para autenticación rápida y gestión de sesiones activas.
@app.route('/api/redis/sesiones', methods=['POST'])
def crear_sesion():
    """
    Crear sesión de estudiante
    {
        "estudiante_id_mongo": "507f1f77bcf86cd799439013",
        "legajo": "2024-ARG-001234",
        "nombre": "Juan",
        "apellido": "Pérez",
        "email": "juan@example.com"
    }
    """
    datos = request.json
    
    if not datos or 'estudiante_id_mongo' not in datos:
        return jsonify({"error": "Campo obligatorio: estudiante_id_mongo"}), 400
    
    try:
        # Generar ID de sesión único
        session_id = str(uuid.uuid4())
        
        sesion_data = {
            "session_id": session_id,
            "estudiante_id_mongo": datos['estudiante_id_mongo'],
            "legajo": datos.get('legajo', ''),
            "nombre": datos.get('nombre', ''),
            "apellido": datos.get('apellido', ''),
            "email": datos.get('email', ''),
            "fecha_creacion": datetime.utcnow().isoformat(),
            "ultimo_acceso": datetime.utcnow().isoformat(),
            "estado": "ACTIVA"
        }
        
        # Guardar en Redis con expiración de 24 horas
        r.setex(
            f"session:{session_id}",
            86400,  # 24 horas
            json.dumps(sesion_data, default=str)
        )
        
        # Índice por estudiante
        r.setex(
            f"student_session:{datos['estudiante_id_mongo']}",
            86400,
            session_id
        )
        
        return jsonify({
            "mensaje": "Sesión creada",
            "session_id": session_id,
            "estudiante": datos.get('legajo'),
            "ttl": 86400
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener información de sesión activa desde Redis para verificar autenticación y mostrar datos de usuario.
@app.route('/api/redis/sesiones/<session_id>', methods=['GET'])
def obtener_sesion(session_id):
    """
    Obtener información de sesión activa
    """
    try:
        sesion_json = r.get(f"session:{session_id}")
        
        if not sesion_json:
            return jsonify({"error": "Sesión no encontrada o expirada"}), 404
        
        sesion = json.loads(sesion_json)
        
        # Actualizar último acceso
        sesion['ultimo_acceso'] = datetime.utcnow().isoformat()
        r.setex(
            f"session:{session_id}",
            86400,
            json.dumps(sesion, default=str)
        )
        
        return jsonify({
            "sesion": sesion,
            "activa": True,
            "ttl": r.ttl(f"session:{session_id}")
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Cerrar sesión eliminando el registro de Redis y el índice por estudiante.
@app.route('/api/redis/sesiones/<session_id>', methods=['DELETE'])
def cerrar_sesion(session_id):
    """
    Cerrar sesión (logout)
    """
    try:
        sesion_json = r.get(f"session:{session_id}")
        
        if not sesion_json:
            return jsonify({"error": "Sesión no encontrada"}), 404
        
        sesion = json.loads(sesion_json)
        estudiante_id = sesion['estudiante_id_mongo']
        
        # Eliminar sesión
        r.delete(f"session:{session_id}")
        r.delete(f"student_session:{estudiante_id}")
        
        return jsonify({
            "mensaje": "Sesión cerrada",
            "session_id": session_id
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener sesión activa de un estudiante desde Redis para verificar si tiene sesión iniciada y mostrar datos básicos.
@app.route('/api/redis/sesiones/estudiante/<estudiante_id_mongo>', methods=['GET'])
def obtener_sesion_por_estudiante(estudiante_id_mongo):
    """
    Obtener sesión activa de un estudiante
    """
    try:
        session_id = r.get(f"student_session:{estudiante_id_mongo}")
        
        if not session_id:
            return jsonify({"error": "No hay sesión activa para este estudiante"}), 404
        
        sesion_json = r.get(f"session:{session_id}")
        sesion = json.loads(sesion_json)
        
        return jsonify({
            "sesion": sesion,
            "activa": True
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Listar todas las sesiones activas en Redis para monitoreo y administración de sesiones.
@app.route('/api/redis/sesiones', methods=['GET'])
def listar_sesiones_activas():
    """
    Listar todas las sesiones activas
    """
    try:
        claves = r.keys("session:*")
        sesiones = []
        
        for clave in claves:
            sesion_json = r.get(clave)
            if sesion_json:
                sesion = json.loads(sesion_json)
                sesiones.append({
                    "session_id": sesion['session_id'],
                    "estudiante": sesion['legajo'],
                    "nombre": f"{sesion['nombre']} {sesion['apellido']}",
                    "ultimo_acceso": sesion['ultimo_acceso'],
                    "ttl": r.ttl(clave)
                })
        
        return jsonify({
            "total_sesiones_activas": len(sesiones),
            "sesiones": sesiones
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# CACHÉ: DATOS DE ESTUDIANTES
# ==========================================

#Carga de estudiantes en caché de Redis para acceso rápido a datos básicos y sincronización con MongoDB.
@app.route('/api/redis/estudiantes/<estudiante_id_mongo>', methods=['POST'])
def cachear_estudiante(estudiante_id_mongo):
    """
    Cachear datos de estudiante desde MongoDB
    {
        "legajo": "2024-ARG-001234",
        "nombre": "Juan",
        "apellido": "Pérez",
        "email": "juan@example.com",
        "pais": "AR"
    }
    """
    datos = request.json
    
    if not datos:
        return jsonify({"error": "Datos requeridos"}), 400
    
    try:
        estudiante_data = {
            "id_mongo": estudiante_id_mongo,
            "legajo": datos.get('legajo', ''),
            "nombre": datos.get('nombre', ''),
            "apellido": datos.get('apellido', ''),
            "email": datos.get('email', ''),
            "pais": datos.get('pais', 'AR'),
            "fecha_cache": datetime.utcnow().isoformat()
        }
        
        # Guardar con expiración de 7 días
        r.setex(
            f"student:{estudiante_id_mongo}",
            604800,
            json.dumps(estudiante_data, default=str)
        )
        
        return jsonify({
            "mensaje": "Estudiante cacheado",
            "estudiante_id": estudiante_id_mongo,
            "legajo": datos.get('legajo')
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener datos de estudiante desde caché de Redis para acceso rápido a información básica sin necesidad de consultar MongoDB.
@app.route('/api/redis/estudiantes/<estudiante_id_mongo>', methods=['GET'])
def obtener_estudiante_cache(estudiante_id_mongo):
    """
    Obtener datos de estudiante desde caché
    """
    try:
        estudiante_json = r.get(f"student:{estudiante_id_mongo}")
        
        if not estudiante_json:
            return jsonify({"error": "Estudiante no en caché", "disponible": False}), 404
        
        estudiante = json.loads(estudiante_json)
        
        return jsonify({
            "estudiante": estudiante,
            "disponible": True,
            "ttl": r.ttl(f"student:{estudiante_id_mongo}")
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Eliminar datos de estudiante del caché de Redis para forzar actualización desde MongoDB en la próxima consulta.
@app.route('/api/redis/estudiantes/<estudiante_id_mongo>', methods=['DELETE'])
def limpiar_cache_estudiante(estudiante_id_mongo):
    """
    Limpiar caché de estudiante
    """
    try:
        resultado = r.delete(f"student:{estudiante_id_mongo}")
        
        if resultado == 0:
            return jsonify({"error": "Estudiante no estaba en caché"}), 404
        
        return jsonify({"mensaje": "Caché de estudiante eliminado"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# ESTADÍSTICAS Y MONITOREO
# ==========================================

# Obtener estadísticas de uso de Redis, como número de conversiones en auditoría, sesiones activas y cantidad de estudiantes cacheados para monitoreo del sistema.
@app.route('/api/redis/estadisticas', methods=['GET'])
def estadisticas_redis():
    """
    Obtener estadísticas de uso de Redis
    """
    try:
        info = r.info()
        
        total_conversiones = len(r.keys("conversion:*"))
        total_sesiones = len(r.keys("session:*"))
        total_auditoria = len(r.keys("conversion_audit:*"))
        total_estudiantes_cache = len(r.keys("student:*"))
        
        return jsonify({
            "redis_info": {
                "version": info.get('redis_version'),
                "connected_clients": info.get('connected_clients'),
                "used_memory_human": info.get('used_memory_human'),
                "uptime_seconds": info.get('uptime_in_seconds')
            },
            "cache_stats": {
                "total_conversiones": total_conversiones,
                "total_sesiones_activas": total_sesiones,
                "total_auditoria_conversiones": total_auditoria,
                "total_estudiantes_cache": total_estudiantes_cache
            }
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# LIMPIAR CACHE (DESARROLLO)
# ==========================================

# Elimina todo el caché de Redis, incluyendo conversiones, sesiones y datos de estudiantes. 
def limpiar_cache():
    """
    ADVERTENCIA: Limpia todo el caché de Redis
    Solo usar en desarrollo
    """
    try:
        r.flushdb()
        return jsonify({"mensaje": "Caché limpiado completamente"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
