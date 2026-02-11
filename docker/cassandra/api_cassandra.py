from flask import Flask, request, jsonify
from cassandra.cluster import Cluster
from cassandra.util import uuid_from_time
import hashlib
import json
from datetime import datetime
import os
from uuid import UUID

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE CASSANDRA
# ==========================================

CASSANDRA_HOSTS = os.getenv('CASSANDRA_HOSTS', 'localhost').split(',')
CASSANDRA_PORT = int(os.getenv('CASSANDRA_PORT', 9042))
KEYSPACE = 'edugrade_audit'

# Conexión a Cassandra
try:
    cluster = Cluster(CASSANDRA_HOSTS, port=CASSANDRA_PORT)
    session = cluster.connect()
    print(f"[Cassandra] Conectado a {','.join(CASSANDRA_HOSTS)}")
except Exception as e:
    print(f"[Cassandra] Error de conexión: {e}")
    session = None

# ==========================================
# INICIALIZACIÓN: KEYSPACE Y TABLAS
# ==========================================

# Crear keyspace y tablas necesarias para auditoría y reportes
def inicializar_cassandra():
    """
    Crea keyspace y tablas si no existen
    """
    if not session:
        return False
    
    try:
        # Crear keyspace
        session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {KEYSPACE}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 3}}
        """)
        
        session.set_keyspace(KEYSPACE)
        
        # Tabla 1: Reportes Geográficos
        session.execute("""
            CREATE TABLE IF NOT EXISTS reportes_geograficos (
                region TEXT,
                institucion_id TEXT,
                anio_lectivo INT,
                acumulado_notas DOUBLE,
                contador_notas COUNTER,
                fecha_actualizacion TIMESTAMP,
                PRIMARY KEY ((region), institucion_id, anio_lectivo)
            ) WITH CLUSTERING ORDER BY (institucion_id ASC, anio_lectivo DESC)
        """)
        
        # Tabla 2: Reportes por Sistemas
        session.execute("""
            CREATE TABLE IF NOT EXISTS reportes_sistemas (
                sistema_educativo TEXT,
                anio_lectivo INT,
                materia_nombre TEXT,
                promedio_convertido FLOAT,
                contador_registros COUNTER,
                fecha_actualizacion TIMESTAMP,
                PRIMARY KEY ((sistema_educativo), anio_lectivo, materia_nombre)
            )
        """)
        
        # Tabla 3: Registro de Auditoría
        session.execute("""
            CREATE TABLE IF NOT EXISTS registro_auditoria (
                id_estudiante TEXT,
                fecha_creacion TIMESTAMP,
                id_auditoria TIMEUUID,
                nota_original TEXT,
                usuario_auditor TEXT,
                tipo_accion TEXT,
                descripcion TEXT,
                hash_integridad TEXT,
                metadata TEXT,
                PRIMARY KEY (id_estudiante, fecha_creacion, id_auditoria)
            ) WITH CLUSTERING ORDER BY (fecha_creacion DESC, id_auditoria DESC)
        """)
        
        # Tabla 4: Índice por fecha de auditoría (para consultas rápidas)
        session.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_por_fecha (
                fecha_creacion TIMESTAMP,
                id_auditoria TIMEUUID,
                id_estudiante TEXT,
                tipo_accion TEXT,
                usuario_auditor TEXT,
                PRIMARY KEY (fecha_creacion, id_auditoria)
            ) WITH CLUSTERING ORDER BY (id_auditoria DESC)
        """)
        
        # Tabla 5: Analytics de Aprobación
        session.execute("""
            CREATE TABLE IF NOT EXISTS analytics_aprobacion (
                pais TEXT,
                nivel_educativo TEXT,
                anio_lectivo INT,
                total_calificaciones COUNTER,
                total_aprobadas COUNTER,
                promedio_notas FLOAT,
                PRIMARY KEY ((pais, nivel_educativo), anio_lectivo)
            )
        """)
        
        # Tabla 6: Distribución de Notas
        session.execute("""
            CREATE TABLE IF NOT EXISTS distribucion_notas (
                pais TEXT,
                nivel_educativo TEXT,
                anio_lectivo INT,
                rango_nota TEXT,
                cantidad COUNTER,
                porcentaje FLOAT,
                PRIMARY KEY ((pais, nivel_educativo), anio_lectivo, rango_nota)
            )
        """)
        
        print("[Cassandra] Keyspace y tablas inicializados")
        return True
    
    except Exception as e:
        print(f"[Cassandra] Error inicializando: {e}")
        return False


# ==========================================
# UTILIDADES
# ==========================================

# Funciones auxiliares para hashing,
def calcular_hash_integridad(datos):
    """
    Calcula hash SHA256 para integridad de registros
    """
    json_str = json.dumps(datos, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()

# Función para generar un TIMEUUID basado en la hora actual
def obtener_timeuuid():
    """
    Obtiene un TIMEUUID actual
    """
    from uuid import uuid1
    return uuid1()


# ==========================================
# AUDITORÍA: REGISTRO APPEND-ONLY
# ==========================================


@app.route('/api/cassandra/auditoria', methods=['POST'])
def registrar_auditoria():
    """
    Registra un evento de auditoría (append-only, inmutable)
    {
        "id_estudiante": "507f1f77bcf86cd799439013",
        "tipo_accion": "CALIFICACION_REGISTRADA" | "CONVERSION_APLICADA" | "CAMBIO_ESTADO",
        "nota_original": "8.5",
        "usuario_auditor": "profesor_123",
        "descripcion": "Registrada calificación de Matemática",
        "metadata": { "materia": "Matemática", "fecha_emision": "2024-01-15" }
    }
    """
    datos = request.json
    
    if not datos or 'id_estudiante' not in datos or 'tipo_accion' not in datos:
        return jsonify({"error": "Campos requeridos: id_estudiante, tipo_accion"}), 400
    
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        id_estudiante = datos['id_estudiante']
        fecha_creacion = datetime.utcnow()
        id_auditoria = obtener_timeuuid()
        
        # Preparar datos para integridad
        datos_integridad = {
            "id_estudiante": id_estudiante,
            "tipo_accion": datos['tipo_accion'],
            "fecha_creacion": fecha_creacion.isoformat(),
            "usuario_auditor": datos.get('usuario_auditor', ''),
            "nota_original": datos.get('nota_original', '')
        }
        hash_integridad = calcular_hash_integridad(datos_integridad)
        
        metadata_json = json.dumps(datos.get('metadata', {}))
        
        # Insertar en tabla principal de auditoría
        session.execute(
            f"""
            INSERT INTO {KEYSPACE}.registro_auditoria
            (id_estudiante, fecha_creacion, id_auditoria, nota_original, usuario_auditor, 
             tipo_accion, descripcion, hash_integridad, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id_estudiante, fecha_creacion, id_auditoria,
             datos.get('nota_original', ''),
             datos.get('usuario_auditor', ''),
             datos['tipo_accion'],
             datos.get('descripcion', ''),
             hash_integridad,
             metadata_json)
        )
        
        # Insertar en índice por fecha (para consultas rápidas)
        session.execute(
            f"""
            INSERT INTO {KEYSPACE}.auditoria_por_fecha
            (fecha_creacion, id_auditoria, id_estudiante, tipo_accion, usuario_auditor)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fecha_creacion, id_auditoria, id_estudiante,
             datos['tipo_accion'],
             datos.get('usuario_auditor', ''))
        )
        
        return jsonify({
            "mensaje": "Evento registrado en auditoría",
            "id_auditoria": str(id_auditoria),
            "hash_integridad": hash_integridad,
            "timestamp": fecha_creacion.isoformat()
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Historial de auditoría de un estudiante (solo-inserción, inmutable)
@app.route('/api/cassandra/auditoria/estudiante/<estudiante_id>', methods=['GET'])
def obtener_auditoria_estudiante(estudiante_id):
    """
    Parámetros opcionales: limit, tipo_accion
    """
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        # Limitar resultados y filtrar por tipo de acción si se proporciona
        limit = request.args.get('limit', 100, type=int)
        tipo_accion = request.args.get('tipo_accion', None)
        
        if tipo_accion:
            query = f"""
                SELECT id_auditoria, fecha_creacion, nota_original, usuario_auditor, 
                       tipo_accion, descripcion, hash_integridad
                FROM {KEYSPACE}.registro_auditoria
                WHERE id_estudiante = ? AND tipo_accion = ?
                LIMIT ?
            """
            results = session.execute(query, (estudiante_id, tipo_accion, limit))
        else:
            query = f"""
                SELECT id_auditoria, fecha_creacion, nota_original, usuario_auditor, 
                       tipo_accion, descripcion, hash_integridad
                FROM {KEYSPACE}.registro_auditoria
                WHERE id_estudiante = ?
                LIMIT ?
            """
            results = session.execute(query, (estudiante_id, limit))
        
        eventos = []
        for row in results:
            eventos.append({
                "id_auditoria": str(row.id_auditoria),
                "fecha": row.fecha_creacion.isoformat(),
                "tipo_accion": row.tipo_accion,
                "usuario_auditor": row.usuario_auditor,
                "nota_original": row.nota_original,
                "descripcion": row.descripcion,
                "hash_integridad": row.hash_integridad
            })
        
        return jsonify({
            "estudiante_id": estudiante_id,
            "total_eventos": len(eventos),
            "eventos": eventos
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Auditoría global por rango de fecha (solo-inserción, inmutable)
@app.route('/api/cassandra/auditoria', methods=['GET'])
def obtener_auditoria_global():
    """
    Obtener auditoría por rango de fecha
    Parámetros: fecha_inicio, fecha_fin, limit
    """
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        limit = request.args.get('limit', 1000, type=int)
        
        if not fecha_inicio or not fecha_fin:
            return jsonify({"error": "Se requieren fecha_inicio y fecha_fin"}), 400
        
        # Analizar fechas
        dt_inicio = datetime.fromisoformat(fecha_inicio)
        dt_fin = datetime.fromisoformat(fecha_fin)
        
        query = f"""
            SELECT fecha_creacion, id_auditoria, id_estudiante, tipo_accion, usuario_auditor
            FROM {KEYSPACE}.auditoria_por_fecha
            WHERE fecha_creacion >= ? AND fecha_creacion <= ?
            LIMIT ?
        """
        
        results = session.execute(query, (dt_inicio, dt_fin, limit))
        
        # Construir lista de eventos con datos relevantes para auditoría global
        eventos = [
            {
                "fecha": row.fecha_creacion.isoformat(),
                "id_auditoria": str(row.id_auditoria),
                "estudiante_id": row.id_estudiante,
                "tipo_accion": row.tipo_accion,
                "usuario_auditor": row.usuario_auditor
            }
            for row in results
        ]
        
        # Respuesta con total de eventos y detalles para auditoría global
        return jsonify({
            "total_eventos": len(eventos),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "eventos": eventos
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# REPORTES: GEOGRÁFICOS 
# ==========================================

# Registrar promedio por región e institución 
@app.route('/api/cassandra/reportes/geograficos', methods=['POST'])
def registrar_promedio_geografico():
    """
    Registrar promedio por región e institución
    {
        "region": "CABA",
        "institucion_id": "507f1f...",
        "anio_lectivo": 2024,
        "nota": 8.5
    }
    """
    datos = request.json
    
    if not datos or 'region' not in datos or 'institucion_id' not in datos:
        return jsonify({"error": "Campos requeridos: region, institucion_id, anio_lectivo, nota"}), 400
    
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        region = datos['region']
        institucion_id = datos['institucion_id']
        anio_lectivo = datos['anio_lectivo']
        nota = float(datos['nota'])
        
        # Actualizar acumulado y contador de forma atómica en Cassandra
        session.execute(
            f"""
            UPDATE {KEYSPACE}.reportes_geograficos
            SET acumulado_notas = acumulado_notas + ?,
                contador_notas = contador_notas + 1,
                fecha_actualizacion = ?
            WHERE region = ? AND institucion_id = ? AND anio_lectivo = ?
            """,
            (nota, datetime.utcnow(), region, institucion_id, anio_lectivo)
        )
        
        # Respuesta con mensaje de éxito y detalles del registro
        return jsonify({
            "mensaje": "Promedio registrado",
            "region": region,
            "institucion": institucion_id,
            "anio": anio_lectivo
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Consultar promedios por región
@app.route('/api/cassandra/reportes/geograficos', methods=['GET'])
def obtener_reportes_geograficos():
    """
    Consultar promedios por región (con filtros opcionales)
    Parámetros: region, institucion_id, anio_lectivo
    """
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        region = request.args.get('region')
        institucion_id = request.args.get('institucion_id')
        anio_lectivo = request.args.get('anio_lectivo', type=int)
        
        if not region:
            return jsonify({"error": "Se requiere parámetro region"}), 400
        
        # Construir consulta con filtros opcionales para obtener promedios por región, institución y año lectivo
        if institucion_id and anio_lectivo:
            query = f"""
                SELECT region, institucion_id, anio_lectivo, acumulado_notas, contador_notas
                FROM {KEYSPACE}.reportes_geograficos
                WHERE region = ? AND institucion_id = ? AND anio_lectivo = ?
            """
            results = session.execute(query, (region, institucion_id, anio_lectivo))
        # Si solo se proporciona institución, filtrar por región e institución
        elif institucion_id:
            query = f"""
                SELECT region, institucion_id, anio_lectivo, acumulado_notas, contador_notas
                FROM {KEYSPACE}.reportes_geograficos
                WHERE region = ? AND institucion_id = ?
            """
            results = session.execute(query, (region, institucion_id))
        else:
            # Si solo se proporciona región, obtener todos los registros de esa región para mostrar promedios por institución y año lectivo
            query = f"""
                SELECT region, institucion_id, anio_lectivo, acumulado_notas, contador_notas
                FROM {KEYSPACE}.reportes_geograficos
                WHERE region = ?
            """
            results = session.execute(query, (region,))
        
        reportes = []
        for row in results:
            # Calcular promedio a partir del acumulado y contador, manejando división por cero
            promedio = row.acumulado_notas / row.contador_notas if row.contador_notas > 0 else 0
            # Agregar reporte a la lista con detalles de región, institución, año lectivo, promedio y total de registros para mostrar en la respuesta
            reportes.append({
                "region": row.region,
                "institucion_id": row.institucion_id,
                "anio_lectivo": row.anio_lectivo,
                "promedio": round(promedio, 2),
                "total_registros": row.contador_notas
            })
        
        return jsonify({
            "region": region,
            "total_instituciones": len(reportes),
            "reportes": reportes
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# REPORTES: SISTEMAS EDUCATIVOS 
# ==========================================

# Registrar promedio convertido por sistema educativo 
@app.route('/api/cassandra/reportes/sistemas', methods=['POST'])
def registrar_promedio_sistema():
    """
    {
        "sistema_educativo": "GB" | "AR" | "US",
        "anio_lectivo": 2024,
        "materia_nombre": "Matemática",
        "promedio_convertido": 8.3
    }
    """
    datos = request.json
    
    if not datos or 'sistema_educativo' not in datos or 'materia_nombre' not in datos:
        return jsonify({"error": "Campos requeridos: sistema_educativo, anio_lectivo, materia_nombre, promedio_convertido"}), 400
    
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        sistema = datos['sistema_educativo']
        anio = datos['anio_lectivo']
        materia = datos['materia_nombre']
        promedio = float(datos['promedio_convertido'])
        
        # Actualizar acumulado
        # En este caso, como solo guardamos el promedio convertido, actualizamos directamente el valor del promedio y el contador de registros para calcular un promedio general a partir de los promedios individuales registrados por cada sistema educativo, materia y año lectivo.
        session.execute(
            f"""
            UPDATE {KEYSPACE}.reportes_sistemas
            SET promedio_convertido = ?,
                contador_registros = contador_registros + 1,
                fecha_actualizacion = ?
            WHERE sistema_educativo = ? AND anio_lectivo = ? AND materia_nombre = ?
            """,
            (promedio, datetime.utcnow(), sistema, anio, materia)
        )
        
        # Respuesta con mensaje de éxito y detalles del registro para mostrar en la respuesta
        return jsonify({
            "mensaje": "Promedio del sistema registrado",
            "sistema": sistema,
            "materia": materia,
            "anio": anio
        }), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Consultar promedios por sistema educativo
@app.route('/api/cassandra/reportes/sistemas', methods=['GET'])
def obtener_reportes_sistemas():
    """
    Comparación entre sistemas educativos
    Parámetros: sistema_educativo, anio_lectivo
    """
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        sistema = request.args.get('sistema_educativo')
        anio_lectivo = request.args.get('anio_lectivo', type=int)
        
        if not sistema:
            return jsonify({"error": "Se requiere parámetro sistema_educativo"}), 400
        
        # Construir consulta con filtros opcionales para obtener promedios por sistema educativo y año lectivo, mostrando materia, promedio convertido y total de registros para cada materia registrada en el sistema educativo y año lectivo especificados.
        if anio_lectivo:
            # Si se proporciona año lectivo, filtramos por sistema educativo y año lectivo para obtener promedios específicos de ese año, mostrando materia, promedio convertido y total de registros para cada materia registrada en el sistema educativo y año lectivo especificados.
            query = f"""
                SELECT sistema_educativo, anio_lectivo, materia_nombre, promedio_convertido, contador_registros
                FROM {KEYSPACE}.reportes_sistemas
                WHERE sistema_educativo = ? AND anio_lectivo = ?
            """
            results = session.execute(query, (sistema, anio_lectivo))
        else:
            # Si no se proporciona año lectivo, obtenemos todos los registros del sistema educativo para mostrar promedios por materia y año lectivo, mostrando materia, promedio convertido y total de registros para cada materia registrada en el sistema educativo especificado.
            query = f"""
                SELECT sistema_educativo, anio_lectivo, materia_nombre, promedio_convertido, contador_registros
                FROM {KEYSPACE}.reportes_sistemas
                WHERE sistema_educativo = ?
            """
            results = session.execute(query, (sistema,))
        
        # Construir lista de reportes con detalles de sistema educativo, año lectivo, materia, promedio convertido y total de registros para mostrar en la respuesta.
        reportes = [
            {
                "sistema": row.sistema_educativo,
                "anio": row.anio_lectivo,
                "materia": row.materia_nombre,
                "promedio": row.promedio_convertido,
                "total_registros": row.contador_registros
            }
            for row in results
        ]
        
        # Respuesta con total de reportes y detalles para comparación entre sistemas educativos
        return jsonify({
            "sistema": sistema,
            "total_materias": len(reportes),
            "reportes": reportes
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# ANALYTICS: TASAS DE APROBACIÓN
# ==========================================

# Registrar estadística de aprobación por país, nivel educativo y año lectivo
@app.route('/api/cassandra/analytics/aprobacion', methods=['POST'])
def registrar_estadistica_aprobacion():
    """
    {
        "pais": "AR",
        "nivel_educativo": "SECUNDARIO",
        "anio_lectivo": 2024,
        "aprobado": true,
        "nota": 8.5
    }
    """
    datos = request.json
    
    if not datos or 'pais' not in datos or 'nivel_educativo' not in datos:
        return jsonify({"error": "Campos requeridos: pais, nivel_educativo, anio_lectivo, aprobado, nota"}), 400
    
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        pais = datos['pais']
        nivel = datos['nivel_educativo']
        anio = datos['anio_lectivo']
        aprobado = datos.get('aprobado', False)
        nota = float(datos['nota'])
        
        # Actualizar contadores de aprobación
        session.execute(
            f"""
            UPDATE {KEYSPACE}.analytics_aprobacion
            SET total_calificaciones = total_calificaciones + 1,
                total_aprobadas = total_aprobadas + ?,
                promedio_notas = ?
            WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ?
            """,
            (1 if aprobado else 0, nota, pais, nivel, anio)
        )
        
        return jsonify({"mensaje": "Estadística registrada"}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener tasas de aprobación por país y nivel educativo
@app.route('/api/cassandra/analytics/aprobacion', methods=['GET'])
def obtener_estadisticas_aprobacion():
    """
    Parámetros: pais, nivel_educativo, anio_lectivo
    """
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        pais = request.args.get('pais')
        nivel = request.args.get('nivel_educativo')
        anio = request.args.get('anio_lectivo', type=int)
        
        if not pais or not nivel:
            return jsonify({"error": "Se requieren parámetros pais y nivel_educativo"}), 400
        
        # Construir consulta con filtros opcionales para obtener estadísticas de aprobación por país, nivel educativo y año lectivo, mostrando total de calificaciones, total de aprobadas, tasa de aprobación en porcentaje y promedio de notas para el país, nivel educativo y año lectivo especificados.
        if anio:
            # Si se proporciona año lectivo, filtramos por país, nivel educativo y año lectivo para obtener estadísticas específicas de ese año, mostrando total de calificaciones, total de aprobadas, tasa de aprobación en porcentaje y promedio de notas para el país, nivel educativo y año lectivo especificados.
            query = f"""
                SELECT pais, nivel_educativo, anio_lectivo, total_calificaciones, total_aprobadas, promedio_notas
                FROM {KEYSPACE}.analytics_aprobacion
                WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ?
            """
            results = session.execute(query, (pais, nivel, anio))
        else:
            # Si no se proporciona año lectivo, obtenemos todos los registros del país y nivel educativo para mostrar estadísticas por año lectivo, mostrando total de calificaciones, total de aprobadas, tasa de aprobación en porcentaje y promedio de notas para el país, nivel educativo y cada año lectivo registrado.
            query = f"""
                SELECT pais, nivel_educativo, anio_lectivo, total_calificaciones, total_aprobadas, promedio_notas
                FROM {KEYSPACE}.analytics_aprobacion
                WHERE pais = ? AND nivel_educativo = ?
            """
            results = session.execute(query, (pais, nivel))
        
        estadisticas = []
        # Calcular tasa de aprobación en porcentaje para cada registro, manejando división por cero, y agregar a la lista de estadísticas
        for row in results:
            tasa_aprobacion = (row.total_aprobadas / row.total_calificaciones * 100) if row.total_calificaciones > 0 else 0
            estadisticas.append({
                "pais": row.pais,
                "nivel": row.nivel_educativo,
                "anio": row.anio_lectivo,
                "total_calificaciones": row.total_calificaciones,
                "total_aprobadas": row.total_aprobadas,
                "tasa_aprobacion_porcentaje": round(tasa_aprobacion, 2),
                "promedio_notas": row.promedio_notas
            })
        
        return jsonify({
            "pais": pais,
            "nivel": nivel,
            "estadisticas": estadisticas
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# ANALYTICS: DISTRIBUCIÓN DE NOTAS
# ==========================================

# Registrar distribución de notas por rango
@app.route('/api/cassandra/analytics/distribucion', methods=['POST'])
def registrar_distribucion_notas():
    """
    {
        "pais": "AR",
        "nivel_educativo": "SECUNDARIO",
        "anio_lectivo": 2024,
        "rango_nota": "8-9" | "9-10" | "6-7" | "menor_6",
        "cantidad": 1
    }
    """
    datos = request.json
    
    if not datos or 'pais' not in datos or 'rango_nota' not in datos:
        return jsonify({"error": "Campos requeridos: pais, nivel_educativo, anio_lectivo, rango_nota"}), 400
    
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        pais = datos['pais']
        nivel = datos['nivel_educativo']
        anio = datos['anio_lectivo']
        rango = datos['rango_nota']
        
        # Actualizar contador de distribución de notas para el rango especificado, incrementando la cantidad en 1 cada vez que se registre una nota que caiga dentro del rango especificado para el país, nivel educativo y año lectivo correspondientes.
        session.execute(
            f"""
            UPDATE {KEYSPACE}.distribucion_notas
            SET cantidad = cantidad + 1
            WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ? AND rango_nota = ?
            """,
            (pais, nivel, anio, rango)
        )
        
        return jsonify({"mensaje": "Distribución registrada"}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Obtener distribución de notas por país, nivel educativo y año lectivo
@app.route('/api/cassandra/analytics/distribucion', methods=['GET'])
def obtener_distribucion_notas():
    """
    Parámetros: pais, nivel_educativo, anio_lectivo
    """
    if not session:
        return jsonify({"error": "Cassandra no disponible"}), 500
    
    try:
        pais = request.args.get('pais')
        nivel = request.args.get('nivel_educativo')
        anio = request.args.get('anio_lectivo', type=int)
        
        if not pais or not nivel:
            return jsonify({"error": "Se requieren parámetros pais y nivel_educativo"}), 400
        # Construir consulta para obtener distribución de notas por país, nivel educativo y año lectivo
        query = f"""
            SELECT pais, nivel_educativo, anio_lectivo, rango_nota, cantidad
            FROM {KEYSPACE}.distribucion_notas
            WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ?
        """
        
        results = session.execute(query, (pais, nivel, anio))
        
        distribucion = []
        total_registros = 0
        
        for row in results:
            # Sumar la cantidad de registros para calcular el total y luego calcular el porcentaje de cada rango en base al total de registros
            total_registros += row.cantidad
            distribucion.append({
                "rango": row.rango_nota,
                "cantidad": row.cantidad
            })
        
        # Calcular porcentajes
        for item in distribucion:
            item['porcentaje'] = round((item['cantidad'] / total_registros * 100), 2) if total_registros > 0 else 0
        
        return jsonify({
            "pais": pais,
            "nivel": nivel,
            "anio": anio,
            "total_registros": total_registros,
            "distribucion": distribucion
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================
# INICIALIZACIÓN
# ==========================================

@app.before_first_request
def antes_primera_consulta():
    """
    Inicializar Cassandra antes de la primera consulta
    """
    inicializar_cassandra()


if __name__ == '__main__':
    inicializar_cassandra()
    app.run(debug=True, host='0.0.0.0', port=5003)
