from flask import Flask, request, jsonify
from pymongo import MongoClient, ASCENDING
from bson import ObjectId, json_util
from neo4j import GraphDatabase
from cassandra.cluster import Cluster
import redis
import json
import datetime
import hashlib
import os

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE BASES DE DATOS
# ==========================================

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:estudiantes2026@localhost:27017/?authSource=admin')
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['edugrade_global']

col_estudiantes = db['estudiantes']
col_instituciones = db['instituciones']
col_materias = db['materias']
col_calificaciones = db['calificaciones']
col_profesores = db['profesores']
col_conversiones = db['reglas_conversion']

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_AUTH = (os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASS', 'grafos2026'))
driver_neo4j = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

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

def parse_json(data):
    return json.loads(json_util.dumps(data))

def obtener_timeuuid():
    """Obtiene un TIMEUUID actual"""
    from uuid import uuid1
    return uuid1()

def calcular_hash_integridad(datos):
    """Calcula hash SHA256 para integridad de registros"""
    json_str = json.dumps(datos, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()

def registrar_auditoria_cassandra(id_estudiante, tipo_accion, nota_original, usuario, descripcion, metadata=None):
    """
    Registra un evento en el audit trail inmutable de Cassandra
    """
    if not cassandra_session:
        return
    
    try:
        fecha_creacion = datetime.datetime.utcnow()
        id_auditoria = obtener_timeuuid()
        
        # Datos para hash de integridad
        datos_integridad = {
            "id_estudiante": id_estudiante,
            "tipo_accion": tipo_accion,
            "fecha_creacion": fecha_creacion.isoformat(),
            "usuario_auditor": usuario,
            "nota_original": nota_original
        }
        hash_integridad = calcular_hash_integridad(datos_integridad)
        
        metadata_json = json.dumps(metadata or {})
        
        # Insertar en tabla principal
        cassandra_session.execute(
            f"""
            INSERT INTO {CASSANDRA_KEYSPACE}.registro_auditoria
            (id_estudiante, fecha_creacion, id_auditoria, nota_original, usuario_auditor, 
             tipo_accion, descripcion, hash_integridad, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (id_estudiante, fecha_creacion, id_auditoria,
             str(nota_original),
             usuario,
             tipo_accion,
             descripcion,
             hash_integridad,
             metadata_json)
        )
        
        # Insertar en índice por fecha
        cassandra_session.execute(
            f"""
            INSERT INTO {CASSANDRA_KEYSPACE}.auditoria_por_fecha
            (fecha_creacion, id_auditoria, id_estudiante, tipo_accion, usuario_auditor)
            VALUES (?, ?, ?, ?, ?)
            """,
            (fecha_creacion, id_auditoria, id_estudiante, tipo_accion, usuario)
        )
    
    except Exception as e:
        print(f"[Cassandra] Error registrando auditoría: {e}")

def log_cassandra(accion, tabla, documento_id, detalles):
    """Registra operaciones en Cassandra para auditoría (deprecated - usar registrar_auditoria_cassandra)"""
    registrar_auditoria_cassandra(documento_id, accion, tabla, "sistema", detalles)

def crear_indices():
    """Crea índices únicos en las colecciones"""
    try:
        col_estudiantes.create_index([("legajo", ASCENDING)], unique=True)
        col_instituciones.create_index([("codigo", ASCENDING)], unique=True)
        col_materias.create_index([("codigo", ASCENDING)], unique=True)
        col_profesores.create_index([("legajo_docente", ASCENDING)], unique=True)
        col_conversiones.create_index([("codigo_regla", ASCENDING)], unique=True)
    except Exception as e:
        print(f"[Mongo] Índices: {e}")

# ==========================================
# ESTUDIANTES
# ==========================================

@app.route('/api/v1/estudiantes', methods=['POST'])
def create_estudiante():
    # Inserta el documento en MongoDB.
    try:
        data = request.json
        
        if not data or 'legajo' not in data or 'nombre' not in data or 'apellido' not in data:
            return jsonify({'error': 'Campos requeridos: legajo, nombre, apellido'}), 400
        
        documento = data.get('documento', {})
        
        estudiante = {
            'legajo': data['legajo'],
            'nombre': data['nombre'],
            'apellido': data['apellido'],
            'documento': {
                'tipo': documento.get('tipo', 'DNI'),
                'numero': documento.get('numero', ''),
                'pais': documento.get('pais', 'AR')
            },
            'fecha_nacimiento': data.get('fecha_nacimiento', None),
            'email': data.get('email', ''),
            'metadata': {
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'estado': 'ACTIVO'
            }
        }
        
        resultado = col_estudiantes.insert_one(estudiante)
        log_cassandra('CREATE', 'estudiantes', str(resultado.inserted_id), f"Estudiante {data['legajo']} creado")
        
        return jsonify({
            'id': str(resultado.inserted_id),
            'legajo': estudiante['legajo'],
            'mensaje': 'Estudiante creado exitosamente'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/estudiantes', methods=['GET'])
def get_estudiantes():
    # Consulta a MongoDB con paginación y filtros.
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        skip = (page - 1) * per_page
        
        # Filtros opcionales
        filtro = {}
        if request.args.get('legajo'):
            filtro['legajo'] = {'$regex': request.args.get('legajo'), '$options': 'i'}
        if request.args.get('nombre'):
            filtro['nombre'] = {'$regex': request.args.get('nombre'), '$options': 'i'}
        if request.args.get('estado'):
            filtro['metadata.estado'] = request.args.get('estado')
        
        estudiantes = list(col_estudiantes.find(filtro).skip(skip).limit(per_page))
        total = col_estudiantes.count_documents(filtro)
        
        return jsonify({
            'data': parse_json(estudiantes),
            'paginacion': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'paginas': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/estudiantes/<estudiante_id>', methods=['GET'])
def get_estudiante_by_id(estudiante_id):
    # Obtiene un estudiante específico por su ID.
    try:
        if not ObjectId.is_valid(estudiante_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        estudiante = col_estudiantes.find_one({'_id': ObjectId(estudiante_id)})
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        return jsonify(parse_json(estudiante)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/estudiantes/<estudiante_id>', methods=['PUT'])
def update_estudiante(estudiante_id):
    # Actualiza datos del estudiante (Mongo) y loguea el cambio (Cassandra).
    try:
        if not ObjectId.is_valid(estudiante_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        estudiante_actual = col_estudiantes.find_one({'_id': ObjectId(estudiante_id)})
        if not estudiante_actual:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Preparar actualización
        actualizacion = {}
        if 'nombre' in data:
            actualizacion['nombre'] = data['nombre']
        if 'apellido' in data:
            actualizacion['apellido'] = data['apellido']
        if 'email' in data:
            actualizacion['email'] = data['email']
        if 'fecha_nacimiento' in data:
            actualizacion['fecha_nacimiento'] = data['fecha_nacimiento']
        if 'documento' in data:
            actualizacion['documento'] = data['documento']
        
        actualizacion['metadata.updated_at'] = datetime.datetime.utcnow()
        
        resultado = col_estudiantes.update_one(
            {'_id': ObjectId(estudiante_id)},
            {'$set': actualizacion}
        )
        
        log_cassandra('UPDATE', 'estudiantes', estudiante_id, "Estudiante actualizado")
        
        return jsonify({'mensaje': 'Estudiante actualizado', 'modificados': resultado.modified_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/estudiantes/<estudiante_id>', methods=['DELETE'])
def delete_estudiante(estudiante_id):
    # Eliminación suave (cambio de estado) en Mongo + Registro inmutable en Cassandra.
    try:
        if not ObjectId.is_valid(estudiante_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        estudiante = col_estudiantes.find_one({'_id': ObjectId(estudiante_id)})
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Eliminación suave: cambiar estado
        col_estudiantes.update_one(
            {'_id': ObjectId(estudiante_id)},
            {'$set': {
                'metadata.estado': 'INACTIVO',
                'metadata.updated_at': datetime.datetime.utcnow()
            }}
        )
        
        log_cassandra('DELETE', 'estudiantes', estudiante_id, "Estudiante marcado como inactivo")
        
        return jsonify({'mensaje': 'Estudiante eliminado (soft delete)'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/instituciones', methods=['POST'])
def create_institucion():
    try:
        data = request.json
        
        if not data or 'codigo' not in data or 'nombre' not in data or 'pais' not in data:
            return jsonify({'error': 'Campos requeridos: codigo, nombre, pais'}), 400
        
        institucion = {
            'codigo': data['codigo'],
            'nombre': data['nombre'],
            'pais': data['pais'],
            'region': data.get('region', ''),
            'email': data.get('email', ''),
            'metadata': {
                'created_at': datetime.datetime.utcnow(),
                'estado': 'ACTIVA'
            }
        }
        
        resultado = col_instituciones.insert_one(institucion)
        log_cassandra('CREATE', 'instituciones', str(resultado.inserted_id), f"Institución {data['codigo']} creada")
        
        return jsonify({
            'id': str(resultado.inserted_id),
            'codigo': institucion['codigo'],
            'mensaje': 'Institución creada exitosamente'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/instituciones', methods=['GET'])
def get_instituciones():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        skip = (page - 1) * per_page
        
        filtro = {}
        if request.args.get('codigo'):
            filtro['codigo'] = {'$regex': request.args.get('codigo'), '$options': 'i'}
        if request.args.get('nombre'):
            filtro['nombre'] = {'$regex': request.args.get('nombre'), '$options': 'i'}
        if request.args.get('pais'):
            filtro['pais'] = request.args.get('pais')
        if request.args.get('estado'):
            filtro['metadata.estado'] = request.args.get('estado')
        
        instituciones = list(col_instituciones.find(filtro).skip(skip).limit(per_page))
        total = col_instituciones.count_documents(filtro)
        
        return jsonify({
            'data': parse_json(instituciones),
            'paginacion': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'paginas': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/instituciones/<institucion_id>', methods=['GET'])
def get_institucion_by_id(institucion_id):
    try:
        if not ObjectId.is_valid(institucion_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        institucion = col_instituciones.find_one({'_id': ObjectId(institucion_id)})
        if not institucion:
            return jsonify({'error': 'Institución no encontrada'}), 404
        
        return jsonify(parse_json(institucion)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/instituciones/<institucion_id>', methods=['PUT'])
def update_institucion(institucion_id):
    try:
        if not ObjectId.is_valid(institucion_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        institucion_actual = col_instituciones.find_one({'_id': ObjectId(institucion_id)})
        if not institucion_actual:
            return jsonify({'error': 'Institución no encontrada'}), 404
        
        actualizacion = {}
        if 'nombre' in data:
            actualizacion['nombre'] = data['nombre']
        if 'region' in data:
            actualizacion['region'] = data['region']
        if 'email' in data:
            actualizacion['email'] = data['email']
        if 'pais' in data:
            actualizacion['pais'] = data['pais']
        
        resultado = col_instituciones.update_one(
            {'_id': ObjectId(institucion_id)},
            {'$set': actualizacion}
        )
        
        log_cassandra('UPDATE', 'instituciones', institucion_id, "Institución actualizada")
        
        return jsonify({'mensaje': 'Institución actualizada', 'modificados': resultado.modified_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/instituciones/<institucion_id>', methods=['DELETE'])
def delete_institucion(institucion_id):
    try:
        if not ObjectId.is_valid(institucion_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        institucion = col_instituciones.find_one({'_id': ObjectId(institucion_id)})
        if not institucion:
            return jsonify({'error': 'Institución no encontrada'}), 404
        
        resultado = col_instituciones.update_one(
            {'_id': ObjectId(institucion_id)},
            {'$set': {'metadata.estado': 'INACTIVA'}}
        )
        
        log_cassandra('DELETE', 'instituciones', institucion_id, "Institución marcada como inactiva")
        
        return jsonify({'mensaje': 'Institución eliminada (soft delete)'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/materias', methods=['POST'])
def create_materia():
    try:
        data = request.json
        
        if not data or 'codigo' not in data or 'nombre' not in data or 'nivel' not in data:
            return jsonify({'error': 'Campos requeridos: codigo, nombre, nivel'}), 400
        
        if 'institucion' in data and data['institucion']:
            if not ObjectId.is_valid(data['institucion']):
                return jsonify({'error': 'ID de institución inválido'}), 400
        
        materia = {
            'codigo': data['codigo'],
            'nombre': data['nombre'],
            'nivel': data['nivel'],
            'año_cursada': data.get('año_cursada', 1),
            'institucion': ObjectId(data['institucion']) if data.get('institucion') else None,
            'metadata': {
                'created_at': datetime.datetime.utcnow(),
                'estado': 'VIGENTE'
            }
        }
        
        resultado = col_materias.insert_one(materia)
        log_cassandra('CREATE', 'materias', str(resultado.inserted_id), f"Materia {data['codigo']} creada")
        
        return jsonify({
            'id': str(resultado.inserted_id),
            'codigo': materia['codigo'],
            'mensaje': 'Materia creada exitosamente'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/materias', methods=['GET'])
def get_materias():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        skip = (page - 1) * per_page
        
        filtro = {}
        if request.args.get('codigo'):
            filtro['codigo'] = {'$regex': request.args.get('codigo'), '$options': 'i'}
        if request.args.get('nombre'):
            filtro['nombre'] = {'$regex': request.args.get('nombre'), '$options': 'i'}
        if request.args.get('nivel'):
            filtro['nivel'] = request.args.get('nivel')
        if request.args.get('estado'):
            filtro['metadata.estado'] = request.args.get('estado')
        if request.args.get('institucion'):
            if ObjectId.is_valid(request.args.get('institucion')):
                filtro['institucion'] = ObjectId(request.args.get('institucion'))
        
        materias = list(col_materias.find(filtro).skip(skip).limit(per_page))
        total = col_materias.count_documents(filtro)
        
        return jsonify({
            'data': parse_json(materias),
            'paginacion': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'paginas': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/materias/<materia_id>', methods=['GET'])
def get_materia_by_id(materia_id):
    try:
        if not ObjectId.is_valid(materia_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        materia = col_materias.find_one({'_id': ObjectId(materia_id)})
        if not materia:
            return jsonify({'error': 'Materia no encontrada'}), 404
        
        return jsonify(parse_json(materia)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/materias/<materia_id>', methods=['PUT'])
def update_materia(materia_id):
    try:
        if not ObjectId.is_valid(materia_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        materia_actual = col_materias.find_one({'_id': ObjectId(materia_id)})
        if not materia_actual:
            return jsonify({'error': 'Materia no encontrada'}), 404
        
        actualizacion = {}
        if 'nombre' in data:
            actualizacion['nombre'] = data['nombre']
        if 'nivel' in data:
            actualizacion['nivel'] = data['nivel']
        if 'año_cursada' in data:
            actualizacion['año_cursada'] = data['año_cursada']
        if 'institucion' in data and data['institucion']:
            if ObjectId.is_valid(data['institucion']):
                actualizacion['institucion'] = ObjectId(data['institucion'])
        
        resultado = col_materias.update_one(
            {'_id': ObjectId(materia_id)},
            {'$set': actualizacion}
        )
        
        log_cassandra('UPDATE', 'materias', materia_id, "Materia actualizada")
        
        return jsonify({'mensaje': 'Materia actualizada', 'modificados': resultado.modified_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/materias/<materia_id>', methods=['DELETE'])
def delete_materia(materia_id):
    try:
        if not ObjectId.is_valid(materia_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        materia = col_materias.find_one({'_id': ObjectId(materia_id)})
        if not materia:
            return jsonify({'error': 'Materia no encontrada'}), 404
        
        resultado = col_materias.update_one(
            {'_id': ObjectId(materia_id)},
            {'$set': {'metadata.estado': 'INACTIVA'}}
        )
        
        log_cassandra('DELETE', 'materias', materia_id, "Materia marcada como inactiva")
        
        return jsonify({'mensaje': 'Materia eliminada (soft delete)'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- PROFESORES ---

@app.route('/api/v1/profesores', methods=['POST'])
def create_profesor():
    try:
        data = request.json
        
        if not data or 'legajo_docente' not in data or 'nombre' not in data or 'apellido' not in data:
            return jsonify({'error': 'Campos requeridos: legajo_docente, nombre, apellido'}), 400
        
        documento = data.get('documento', {})
        instituciones = data.get('instituciones', [])
        
        # Validar ObjectIds de instituciones
        instituciones_ids = []
        for inst_id in instituciones:
            if ObjectId.is_valid(inst_id):
                instituciones_ids.append(ObjectId(inst_id))
        
        profesor = {
            'legajo_docente': data['legajo_docente'],
            'nombre': data['nombre'],
            'apellido': data['apellido'],
            'documento': {
                'tipo': documento.get('tipo', 'DNI'),
                'numero': documento.get('numero', ''),
                'pais': documento.get('pais', 'AR')
            },
            'email': data.get('email', ''),
            'instituciones': instituciones_ids,
            'metadata': {
                'created_at': datetime.datetime.utcnow(),
                'updated_at': datetime.datetime.utcnow(),
                'estado': 'ACTIVO'
            }
        }
        
        resultado = col_profesores.insert_one(profesor)
        log_cassandra('CREATE', 'profesores', str(resultado.inserted_id), f"Profesor {data['legajo_docente']} creado")
        
        return jsonify({
            'id': str(resultado.inserted_id),
            'legajo_docente': profesor['legajo_docente'],
            'mensaje': 'Profesor creado exitosamente'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/profesores', methods=['GET'])
def get_profesores():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        skip = (page - 1) * per_page
        
        filtro = {}
        if request.args.get('legajo_docente'):
            filtro['legajo_docente'] = {'$regex': request.args.get('legajo_docente'), '$options': 'i'}
        if request.args.get('nombre'):
            filtro['nombre'] = {'$regex': request.args.get('nombre'), '$options': 'i'}
        if request.args.get('estado'):
            filtro['metadata.estado'] = request.args.get('estado')
        
        profesores = list(col_profesores.find(filtro).skip(skip).limit(per_page))
        total = col_profesores.count_documents(filtro)
        
        return jsonify({
            'data': parse_json(profesores),
            'paginacion': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'paginas': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/profesores/<profesor_id>', methods=['GET'])
def get_profesor_by_id(profesor_id):
    try:
        if not ObjectId.is_valid(profesor_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        profesor = col_profesores.find_one({'_id': ObjectId(profesor_id)})
        if not profesor:
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        return jsonify(parse_json(profesor)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/profesores/<profesor_id>', methods=['PUT'])
def update_profesor(profesor_id):
    try:
        if not ObjectId.is_valid(profesor_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        profesor_actual = col_profesores.find_one({'_id': ObjectId(profesor_id)})
        if not profesor_actual:
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        actualizacion = {}
        if 'nombre' in data:
            actualizacion['nombre'] = data['nombre']
        if 'apellido' in data:
            actualizacion['apellido'] = data['apellido']
        if 'email' in data:
            actualizacion['email'] = data['email']
        if 'documento' in data:
            actualizacion['documento'] = data['documento']
        if 'instituciones' in data:
            instituciones_ids = []
            for inst_id in data['instituciones']:
                if ObjectId.is_valid(inst_id):
                    instituciones_ids.append(ObjectId(inst_id))
            actualizacion['instituciones'] = instituciones_ids
        
        actualizacion['metadata.updated_at'] = datetime.datetime.utcnow()
        
        resultado = col_profesores.update_one(
            {'_id': ObjectId(profesor_id)},
            {'$set': actualizacion}
        )
        
        log_cassandra('UPDATE', 'profesores', profesor_id, "Profesor actualizado")
        
        return jsonify({'mensaje': 'Profesor actualizado', 'modificados': resultado.modified_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/profesores/<profesor_id>', methods=['DELETE'])
def delete_profesor(profesor_id):
    try:
        if not ObjectId.is_valid(profesor_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        profesor = col_profesores.find_one({'_id': ObjectId(profesor_id)})
        if not profesor:
            return jsonify({'error': 'Profesor no encontrado'}), 404
        
        col_profesores.update_one(
            {'_id': ObjectId(profesor_id)},
            {'$set': {
                'metadata.estado': 'INACTIVO',
                'metadata.updated_at': datetime.datetime.utcnow()
            }}
        )
        
        log_cassandra('DELETE', 'profesores', profesor_id, "Profesor marcado como inactivo")
        
        return jsonify({'mensaje': 'Profesor eliminado (soft delete)'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- REGLAS DE CONVERSIÓN ---

@app.route('/api/v1/reglas-conversion', methods=['POST'])
def create_regla_conversion():
    try:
        data = request.json
        
        if not data or 'codigo_regla' not in data or 'sistema_origen' not in data or 'sistema_destino' not in data:
            return jsonify({'error': 'Campos requeridos: codigo_regla, sistema_origen, sistema_destino'}), 400
        
        regla = {
            'codigo_regla': data['codigo_regla'],
            'sistema_origen': data['sistema_origen'],
            'sistema_destino': data['sistema_destino'],
            'version_regla': data.get('version_regla', '1.0'),
            'escala_origen': data.get('escala_origen', []),
            'escala_destino': data.get('escala_destino', {}),
            'mapeo': data.get('mapeo', []),
            'normativa_asociada': data.get('normativa_asociada', ''),
            'metadata': {
                'vigencia_desde': data.get('vigencia_desde', datetime.datetime.utcnow()),
                'vigencia_hasta': data.get('vigencia_hasta', None),
                'estado': 'VIGENTE'
            }
        }
        
        resultado = col_conversiones.insert_one(regla)
        
        # Guardar en Redis para acceso rápido
        if r:
            try:
                r.set(f"regla_conversion:{data['codigo_regla']}", json.dumps(parse_json(regla)))
            except Exception as e:
                print(f"[Redis] Error cacheando regla: {e}")
        
        log_cassandra('CREATE', 'reglas_conversion', str(resultado.inserted_id), f"Regla {data['codigo_regla']} creada")
        
        return jsonify({
            'id': str(resultado.inserted_id),
            'codigo_regla': regla['codigo_regla'],
            'mensaje': 'Regla de conversión creada'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reglas-conversion', methods=['GET'])
def get_reglas_conversion():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        skip = (page - 1) * per_page
        
        filtro = {}
        if request.args.get('codigo_regla'):
            filtro['codigo_regla'] = {'$regex': request.args.get('codigo_regla'), '$options': 'i'}
        if request.args.get('sistema_origen'):
            filtro['sistema_origen'] = request.args.get('sistema_origen')
        if request.args.get('sistema_destino'):
            filtro['sistema_destino'] = request.args.get('sistema_destino')
        if request.args.get('estado'):
            filtro['metadata.estado'] = request.args.get('estado')
        
        reglas = list(col_conversiones.find(filtro).skip(skip).limit(per_page))
        total = col_conversiones.count_documents(filtro)
        
        return jsonify({
            'data': parse_json(reglas),
            'paginacion': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'paginas': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reglas-conversion/<regla_id>', methods=['GET'])
def get_regla_conversion_by_id(regla_id):
    try:
        if not ObjectId.is_valid(regla_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        regla = col_conversiones.find_one({'_id': ObjectId(regla_id)})
        if not regla:
            return jsonify({'error': 'Regla de conversión no encontrada'}), 404
        
        return jsonify(parse_json(regla)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reglas-conversion/<regla_id>', methods=['PUT'])
def update_regla_conversion(regla_id):
    try:
        if not ObjectId.is_valid(regla_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        regla_actual = col_conversiones.find_one({'_id': ObjectId(regla_id)})
        if not regla_actual:
            return jsonify({'error': 'Regla de conversión no encontrada'}), 404
        
        actualizacion = {}
        if 'version_regla' in data:
            actualizacion['version_regla'] = data['version_regla']
        if 'escala_origen' in data:
            actualizacion['escala_origen'] = data['escala_origen']
        if 'escala_destino' in data:
            actualizacion['escala_destino'] = data['escala_destino']
        if 'mapeo' in data:
            actualizacion['mapeo'] = data['mapeo']
        if 'normativa_asociada' in data:
            actualizacion['normativa_asociada'] = data['normativa_asociada']
        if 'vigencia_hasta' in data:
            actualizacion['metadata.vigencia_hasta'] = data['vigencia_hasta']
        
        resultado = col_conversiones.update_one(
            {'_id': ObjectId(regla_id)},
            {'$set': actualizacion}
        )
        
        # Actualizar en Redis
        if r and regla_actual.get('codigo_regla'):
            try:
                regla_actualizada = col_conversiones.find_one({'_id': ObjectId(regla_id)})
                r.set(f"regla_conversion:{regla_actualizada['codigo_regla']}", json.dumps(parse_json(regla_actualizada)))
            except Exception as e:
                print(f"[Redis] Error actualizando cache: {e}")
        
        log_cassandra('UPDATE', 'reglas_conversion', regla_id, "Regla actualizada")
        
        return jsonify({'mensaje': 'Regla actualizada', 'modificados': resultado.modified_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reglas-conversion/<regla_id>', methods=['DELETE'])
def delete_regla_conversion(regla_id):
    try:
        if not ObjectId.is_valid(regla_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        regla = col_conversiones.find_one({'_id': ObjectId(regla_id)})
        if not regla:
            return jsonify({'error': 'Regla de conversión no encontrada'}), 404
        
        # Eliminación suave: marcar como inactiva
        col_conversiones.update_one(
            {'_id': ObjectId(regla_id)},
            {'$set': {'metadata.estado': 'INACTIVA'}}
        )
        
        # Limpiar cache en Redis
        if r and regla.get('codigo_regla'):
            try:
                r.delete(f"regla_conversion:{regla['codigo_regla']}")
            except Exception as e:
                print(f"[Redis] Error eliminando cache: {e}")
        
        log_cassandra('DELETE', 'reglas_conversion', regla_id, "Regla marcada como inactiva")
        
        return jsonify({'mensaje': 'Regla eliminada (soft delete)'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- CALIFICACIONES (Formato original + metadatos) ---

@app.route('/api/v1/calificaciones', methods=['POST'])
def registrar_calificacion():
    # Endpoint Obligatorio: Registrar calificación en formato original.
    # Operación: Inserta en Mongo, crea nodo/relación en Neo4j, loggea en Cassandra.
    try:
        data = request.json
        
        if not data or 'estudiante_id' not in data or 'materia_id' not in data or 'valor_original' not in data:
            return jsonify({'error': 'Campos requeridos: estudiante_id, materia_id, valor_original'}), 400
        
        if not ObjectId.is_valid(data['estudiante_id']) or not ObjectId.is_valid(data['materia_id']):
            return jsonify({'error': 'IDs de estudiante o materia inválidos'}), 400
        
        valor_original = data['valor_original']
        componentes = data.get('componentes', [])
        
        # Calcular promedio de componentes si existen
        promedio_componentes = 0
        if componentes:
            total = sum([c.get('valor', 0) for c in componentes])
            promedio_componentes = total / len(componentes) if componentes else 0
        
        # Considerar aprobado si la nota es >= 6 (escala Argentina)
        aprobado = valor_original.get('nota', 0) >= 6
        
        # Hash de integridad
        hash_data = json.dumps(valor_original, sort_keys=True, default=str)
        hash_integridad = 'sha256:' + hashlib.sha256(hash_data.encode()).hexdigest()
        
        calificacion = {
            'estudiante_id': ObjectId(data['estudiante_id']),
            'materia_id': ObjectId(data['materia_id']),
            'fecha_emision': data.get('fecha_emision', datetime.datetime.utcnow()),
            'valor_original': {
                'nota': valor_original.get('nota', 0),
                'tipo': valor_original.get('tipo', 'FINAL')
            },
            'componentes': componentes,
            'aprobado': aprobado,
            'promedio_componentes': promedio_componentes,
            'conversiones_aplicadas': [],
            'metadata': {
                'created_at': datetime.datetime.utcnow(),
                'created_by': data.get('created_by', 'sistema'),
                'updated_at': datetime.datetime.utcnow(),
                'hash_integridad': hash_integridad,
                'version': 1,
                'estado': 'DEFINITIVA'
            }
        }
        
        resultado = col_calificaciones.insert_one(calificacion)
        
        # Sincronizar en Neo4j
        try:
            with driver_neo4j.session() as session:
                session.run("""
                    MERGE (e:Estudiante {id: $est_id})
                    MERGE (m:Materia {id: $mat_id})
                    MERGE (cal:Calificacion {id: $cal_id})
                    SET cal.nota = $nota, cal.fecha = datetime()
                    MERGE (e)-[:TIENE_CALIFICACION]->(cal)
                    MERGE (cal)-[:DE_MATERIA]->(m)
                """, est_id=str(data['estudiante_id']), mat_id=str(data['materia_id']), 
                    cal_id=str(resultado.inserted_id), nota=valor_original.get('nota', 0))
        except Exception as e:
            print(f"[Neo4j] Error sinc: {e}")
        
        # ===== Escribir en Cassandra =====
        if cassandra_session:
            try:
                # Obtener información del estudiante e institución para contexto geográfico
                estudiante = col_estudiantes.find_one({'_id': ObjectId(data['estudiante_id'])})
                materia = col_materias.find_one({'_id': ObjectId(data['materia_id'])})
                
                # Obtener institución (asumiendo que la materia está asociada con una institución)
                institucion = None
                if materia and 'institucion_id' in materia:
                    institucion = col_instituciones.find_one({'_id': ObjectId(materia['institucion_id'])})
                
                # Extraer datos geográficos
                region = institucion.get('ubicacion', {}).get('region', 'DESCONOCIDA') if institucion else 'DESCONOCIDA'
                pais = institucion.get('ubicacion', {}).get('pais', 'AR') if institucion else 'AR'
                nivel = institucion.get('nivel_educativo', 'SECUNDARIO') if institucion else 'SECUNDARIO'
                anio_lectivo = data.get('anio_lectivo', datetime.datetime.utcnow().year)
                
                # 1. Registrar en reportes_geograficos (analytics)
                cassandra_session.execute(
                    f"""
                    UPDATE {CASSANDRA_KEYSPACE}.reportes_geograficos
                    SET acumulado_notas = acumulado_notas + ?,
                        contador_notas = contador_notas + 1,
                        fecha_actualizacion = ?
                    WHERE region = ? AND institucion_id = ? AND anio_lectivo = ?
                    """,
                    (valor_original.get('nota', 0), datetime.datetime.utcnow(),
                     region, str(materia['institucion_id']) if materia and 'institucion_id' in materia else 'DESCONOCIDA',
                     anio_lectivo)
                )
                
                # 2. Registrar en analytics_aprobacion
                cassandra_session.execute(
                    f"""
                    UPDATE {CASSANDRA_KEYSPACE}.analytics_aprobacion
                    SET total_calificaciones = total_calificaciones + 1,
                        total_aprobadas = total_aprobadas + ?,
                        promedio_notas = ?
                    WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ?
                    """,
                    (1 if aprobado else 0, valor_original.get('nota', 0),
                     pais, nivel, anio_lectivo)
                )
                
                # 3. Registrar distribución de notas
                def obtener_rango_nota(nota):
                    if nota < 3: return '0-3'
                    elif nota < 6: return '3-6'
                    elif nota < 7: return '6-7'
                    elif nota < 8: return '7-8'
                    elif nota < 9: return '8-9'
                    else: return '9-10'
                
                rango = obtener_rango_nota(valor_original.get('nota', 0))
                cassandra_session.execute(
                    f"""
                    UPDATE {CASSANDRA_KEYSPACE}.distribucion_notas
                    SET cantidad = cantidad + 1
                    WHERE pais = ? AND nivel_educativo = ? AND anio_lectivo = ? AND rango_nota = ?
                    """,
                    (pais, nivel, anio_lectivo, rango)
                )
                
                # 4. Registrar en audit trail
                registrar_auditoria_cassandra(
                    data['estudiante_id'],
                    'CALIFICACION_REGISTRADA',
                    valor_original.get('nota', 0),
                    data.get('created_by', 'sistema'),
                    f"Calificación registrada: {materia.get('nombre', 'N/A') if materia else 'N/A'}",
                    {
                        'materia_id': data['materia_id'],
                        'institucion_id': str(materia['institucion_id']) if materia and 'institucion_id' in materia else None,
                        'regla_evaluacion': valor_original.get('tipo', 'FINAL'),
                        'componentes': len(componentes)
                    }
                )
            
            except Exception as e:
                print(f"[Cassandra] Error escribiendo calificación: {e}")
        
        return jsonify({
            'id': str(resultado.inserted_id),
            'mensaje': 'Calificación registrada exitosamente'
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/calificaciones/<calificacion_id>', methods=['GET'])
def get_calificacion_by_id(calificacion_id):
    # Obtiene la calificación original desde MongoDB.
    try:
        if not ObjectId.is_valid(calificacion_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        calificacion = col_calificaciones.find_one({'_id': ObjectId(calificacion_id)})
        if not calificacion:
            return jsonify({'error': 'Calificación no encontrada'}), 404
        
        return jsonify(parse_json(calificacion)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/calificaciones/<calificacion_id>', methods=['PUT'])
def update_calificacion(calificacion_id):
    # Para correcciones. Genera una nueva versión en MongoDB (append-only conceptual)
    # y registra la recalificación en Cassandra para auditoría.
    try:
        if not ObjectId.is_valid(calificacion_id):
            return jsonify({'error': 'ID inválido'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'No se proporcionaron datos'}), 400
        
        calificacion = col_calificaciones.find_one({'_id': ObjectId(calificacion_id)})
        if not calificacion:
            return jsonify({'error': 'Calificación no encontrada'}), 404
        
        # Actualización con versionado
        actualizacion = {}
        if 'valor_original' in data:
            actualizacion['valor_original'] = data['valor_original']
            actualizacion['aprobado'] = data['valor_original'].get('nota', 0) >= 6
        if 'componentes' in data:
            actualizacion['componentes'] = data['componentes']
            total = sum([c.get('valor', 0) for c in data['componentes']])
            actualizacion['promedio_componentes'] = total / len(data['componentes']) if data['componentes'] else 0
        
        actualizacion['metadata.updated_at'] = datetime.datetime.utcnow()
        actualizacion['metadata.version'] = calificacion['metadata']['version'] + 1
        actualizacion['metadata.estado'] = 'CORREGIDA'
        
        # Hash de integridad actualizado
        hash_data = json.dumps(actualizacion.get('valor_original', calificacion['valor_original']), 
                               sort_keys=True, default=str)
        actualizacion['metadata.hash_integridad'] = 'sha256:' + hashlib.sha256(hash_data.encode()).hexdigest()
        
        resultado = col_calificaciones.update_one(
            {'_id': ObjectId(calificacion_id)},
            {'$set': actualizacion}
        )
        
        log_cassandra('UPDATE', 'calificaciones', calificacion_id, f"Calificación corregida - versión {actualizacion['metadata.version']}")
        
        return jsonify({'mensaje': 'Calificación actualizada', 'modificados': resultado.modified_count}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- CONVERSIONES ---

@app.route('/api/v1/conversiones', methods=['POST'])
def convertir_calificacion():
    # Endpoint Obligatorio: Convertir calificación a otra escala.
    # Operación: Lee la regla desde Redis, calcula, actualiza el array embebido 
    # en la calificación de Mongo, y loggea el evento en Cassandra.
    try:
        data = request.json
        
        if not data or 'calificacion_id' not in data or 'regla_id' not in data:
            return jsonify({'error': 'Campos requeridos: calificacion_id, regla_id'}), 400
        
        calificacion_id = data['calificacion_id']
        regla_id = data['regla_id']
        
        if not ObjectId.is_valid(calificacion_id) or not ObjectId.is_valid(regla_id):
            return jsonify({'error': 'IDs inválidos'}), 400
        
        # Obtener calificación
        calificacion = col_calificaciones.find_one({'_id': ObjectId(calificacion_id)})
        if not calificacion:
            return jsonify({'error': 'Calificación no encontrada'}), 404
        
        # Obtener regla de conversión
        regla = col_conversiones.find_one({'_id': ObjectId(regla_id)})
        if not regla:
            return jsonify({'error': 'Regla de conversión no encontrada'}), 404
        
        # Buscar equivalencia en el mapeo
        nota_original = calificacion['valor_original']['nota']
        valor_convertido = None
        
        for mapeo in regla.get('mapeo', []):
            if mapeo['nota_origen'] == str(nota_original) or mapeo['nota_origen'] == nota_original:
                valor_convertido = mapeo['nota_destino']
                break
        
        if valor_convertido is None:
            return jsonify({'error': f"No se encontró equivalencia para nota {nota_original} en la regla"}), 400
        
        # Agregar conversión al array de conversiones_aplicadas
        nueva_conversion = {
            'regla_id': ObjectId(regla_id),
            'sistema_destino': regla['sistema_destino'],
            'valor_convertido': valor_convertido,
            'fecha_conversion': datetime.datetime.utcnow(),
            'convertido_por': data.get('convertido_por', 'sistema_batch')
        }
        
        resultado = col_calificaciones.update_one(
            {'_id': ObjectId(calificacion_id)},
            {
                '$push': {'conversiones_aplicadas': nueva_conversion},
                '$set': {'metadata.updated_at': datetime.datetime.utcnow()}
            }
        )
        
        log_cassandra('CREATE', 'conversiones', str(resultado.upserted_id or calificacion_id), 
                     f"Conversión aplicada: {nota_original} -> {valor_convertido} ({regla['sistema_destino']})")
        
        return jsonify({
            'mensaje': 'Conversión aplicada exitosamente',
            'valor_original': nota_original,
            'valor_convertido': valor_convertido,
            'sistema_destino': regla['sistema_destino']
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- TRAYECTORIAS ---

@app.route('/api/v1/estudiantes/<estudiante_id>/trayectoria', methods=['GET'])
def obtener_trayectoria(estudiante_id):
    # Endpoint Obligatorio: Obtener trayectoria completa de un estudiante (incluyendo conversiones).
    # Operación: Consulta a Neo4j para mapear las relaciones/equivalencias y trae 
    # el detalle de las notas desde MongoDB.
    try:
        if not ObjectId.is_valid(estudiante_id):
            return jsonify({'error': 'ID de estudiante inválido'}), 400
        
        # Verificar que el estudiante existe
        estudiante = col_estudiantes.find_one({'_id': ObjectId(estudiante_id)})
        if not estudiante:
            return jsonify({'error': 'Estudiante no encontrado'}), 404
        
        # Obtener todas las calificaciones del estudiante desde MongoDB
        calificaciones = list(col_calificaciones.find({'estudiante_id': ObjectId(estudiante_id)}))
        
        # Enriquecer con datos de materias
        trayectoria = []
        for cal in calificaciones:
            materia = col_materias.find_one({'_id': cal['materia_id']})
            trayectoria.append({
                'calificacion_id': str(cal['_id']),
                'estudiante': {
                    'id': str(estudiante['_id']),
                    'nombre': estudiante['nombre'],
                    'apellido': estudiante['apellido'],
                    'legajo': estudiante['legajo']
                },
                'materia': parse_json(materia) if materia else None,
                'valor_original': cal['valor_original'],
                'componentes': cal.get('componentes', []),
                'aprobado': cal['aprobado'],
                'promedio_componentes': cal['promedio_componentes'],
                'conversiones': parse_json(cal.get('conversiones_aplicadas', [])),
                'fecha_emision': str(cal['fecha_emision']),
                'estado': cal['metadata']['estado']
            })
        
        return jsonify({
            'estudiante_id': estudiante_id,
            'nombre_estudiante': f"{estudiante['nombre']} {estudiante['apellido']}",
            'total_materias': len(trayectoria),
            'approved_count': sum([1 for c in trayectoria if c['aprobado']]),
            'trayectoria': trayectoria
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- REPORTES ANALÍTICOS ---

@app.route('/api/v1/reportes/promedios', methods=['GET'])
def get_reporte_promedios():
    # Endpoint Obligatorio: Reportes analíticos (promedio por país, distribución, etc.).
    # Operación: Consulta idealmente a vistas pre-calculadas en Cassandra o 
    # pipelines de agregación en MongoDB.
    try:
        pais_filter = request.args.get('pais', None)
        
        # Pipeline de agregación para calcular promedios
        pipeline = []
        
        if pais_filter:
            # Hacer join con estudiantes para habilitar filtro de país
            pipeline.append({
                '$lookup': {
                    'from': 'estudiantes',
                    'localField': 'estudiante_id',
                    'foreignField': '_id',
                    'as': 'estudiante_info'
                }
            })
            pipeline.append({
                '$match': {
                    'estudiante_info.documento.pais': pais_filter
                }
            })
        
        pipeline.extend([
            {
                '$group': {
                    '_id': None,
                    'promedio_general': {'$avg': '$valor_original.nota'},
                    'nota_maxima': {'$max': '$valor_original.nota'},
                    'nota_minima': {'$min': '$valor_original.nota'},
                    'total_calificaciones': {'$sum': 1},
                    'calificaciones_aprobadas': {
                        '$sum': {'$cond': ['$aprobado', 1, 0]}
                    }
                }
            }
        ])
        
        resultados = list(col_calificaciones.aggregate(pipeline))
        
        if resultados:
            reporte = resultados[0]
            reporte['porcentaje_aprobacion'] = (reporte['calificaciones_aprobadas'] / reporte['total_calificaciones'] * 100) if reporte['total_calificaciones'] > 0 else 0
        else:
            reporte = {
                'promedio_general': 0,
                'nota_maxima': 0,
                'nota_minima': 0,
                'total_calificaciones': 0,
                'calificaciones_aprobadas': 0,
                'porcentaje_aprobacion': 0
            }
        
        return jsonify({
            'filtro': {'pais': pais_filter} if pais_filter else {},
            'reporte': reporte
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/reportes/distribucion', methods=['GET'])
def get_reporte_distribucion():
    # Operación: Analytics de la distribución de notas a nivel global.
    try:
        # Pipeline para distribución de notas por rango
        pipeline = [
            {
                '$group': {
                    '_id': {
                        '$cond': [
                            {'$gte': ['$valor_original.nota', 9]}, '9-10',
                            {'$cond': [
                                {'$gte': ['$valor_original.nota', 7]}, '7-8',
                                {'$cond': [
                                    {'$gte': ['$valor_original.nota', 6]}, '6-7',
                                    'Menor a 6'
                                ]}
                            ]}
                        ]
                    },
                    'cantidad': {'$sum': 1},
                    'promedio': {'$avg': '$valor_original.nota'}
                }
            },
            {'$sort': {'_id': 1}}
        ]
        
        resultados = list(col_calificaciones.aggregate(pipeline))
        
        return jsonify({
            'distribucion': parse_json(resultados)
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Inicialización ---

if __name__ == '__main__':
    crear_indices()
    app.run(debug=True, host='0.0.0.0', port=5000)