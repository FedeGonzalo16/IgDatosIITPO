from flask import Flask, request, jsonify
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId, json_util
from neo4j import GraphDatabase
import redis
import json
import datetime
import os

app = Flask(__name__)

# ==========================================
# CONFIGURACIÓN DE MONGODB (Documental)
# ==========================================

MONGO_URI = "mongodb://root:estudiantes2026@localhost:27017/?authSource=admin"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["edugrade_global"]

col_estudiantes = db["estudiantes"]
col_instituciones = db["instituciones"]
col_calificaciones = db["calificaciones"]
col_reglas = db["reglas_conversion"]
col_materias = db["materias"]

# ==========================================
# CONFIGURACIÓN DE NEO4J (Grafos)
# ==========================================

NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "grafos2026")
driver_neo4j = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)

# --- Funciones Auxiliares de Neo4j ---

def sincronizar_grafo(student_id, materia_data, sistema_origen):
    """
    Proyecta la relación en el grafo inmediatamente después de guardar en Mongo.
    Usa MERGE para evitar duplicados.
    """
    query = """
    MERGE (e:Estudiante {id: $sid})
    MERGE (m:Materia {codigo: $m_cod})
    ON CREATE SET m.nombre = $m_nom, m.sistema = $sistema
    MERGE (e)-[r:CURSO]->(m)
    SET r.fecha_actualizacion = datetime()
    """
    try:
        with driver_neo4j.session() as session:
            session.run(query, 
                        sid=student_id, 
                        m_cod=materia_data.get('codigo', 'GEN-001'), 
                        m_nom=materia_data.get('nombre', 'Materia Generica'),
                        sistema=sistema_origen)
            print(f" [Neo4j] Relación actualizada: {student_id} -> {materia_data.get('nombre')}")
    except Exception as e:
        print(f" [Neo4j Error] No se pudo sincronizar grafo: {e}")

# ==========================================
# CONFIGURACIÓN DE REDIS 
# ==========================================

REDIS_HOST = os.getenv('REDIS_HOST', 'redis') 
REDIS_PORT = 6379

try:
    r = redis.Redis(
        host=REDIS_HOST, 
        port=REDIS_PORT, 
        db=0, 
        decode_responses=True
    )
    # Verificamos conexión
    r.ping()
    print(" [Redis] Conexión exitosa (Docker Network).")
except Exception as e:
    print(f" [Redis Error] No se pudo conectar: {e}")
    r = None 

# ==========================================
# UTILIDADES Y CONFIGURACIÓN
# ==========================================

def parse_json(data):
    return json.loads(json_util.dumps(data))

def inicializar_indices():
    """Optimización para volumen de 1M registros"""
    try:
        col_estudiantes.create_index([("dni", ASCENDING)], unique=True)
        col_calificaciones.create_index([("student_id", ASCENDING), ("fecha_registro", DESCENDING)])
        print(" [Mongo] Índices inicializados.")
    except Exception as e:
        print(f" [Mongo] Alerta índices: {e}")

# --- ESTUDIANTES ---
@app.route('/api/estudiantes', methods=['POST'])
def crear_estudiante():
    data = request.json
    if not data or 'dni' not in data:
        return jsonify({"error": "DNI obligatorio"}), 400
    
    try:
        data['fecha_alta'] = datetime.datetime.utcnow()
        res = col_estudiantes.insert_one(data)
        
        # Crear el nodo estudiante en Neo4j
        with driver_neo4j.session() as session:
            session.run("MERGE (:Estudiante {id: $sid})", sid=str(res.inserted_id))

        return jsonify({"msg": "Estudiante creado", "id": str(res.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/estudiantes', methods=['GET'])
def listar_estudiantes():
    estudiantes = list(col_estudiantes.find().limit(50))
    return jsonify(parse_json(estudiantes)), 200

# --- INSTITUCIONES ---
@app.route('/api/instituciones', methods=['POST'])
def crear_institucion():
    res = col_instituciones.insert_one(request.json)
    return jsonify({"msg": "Institución creada", "id": str(res.inserted_id)}), 201

@app.route('/api/instituciones', methods=['GET'])
def listar_instituciones():
    data = list(col_instituciones.find())
    return jsonify(parse_json(data)), 200

# --- CALIFICACIONES ---
@app.route('/api/calificaciones', methods=['POST'])
def registrar_calificacion():
    """
    RF1: Guarda documento original en Mongo.
    RF3: Actualiza grafo en Neo4j.
    """
    data = request.json
    
    # Validaciones básicas
    if 'student_id' not in data or 'materia' not in data:
        return jsonify({"error": "Faltan datos (student_id, materia)"}), 400
    
    # Persistencia Principal (MongoDB)
    try:
        data['fecha_registro'] = datetime.datetime.utcnow()
        res = col_calificaciones.insert_one(data)
        mongo_id = str(res.inserted_id)
        
        # Persistencia de Relaciones (Neo4j)
        sincronizar_grafo(
            student_id=data['student_id'],
            materia_data=data['materia'],
            sistema_origen=data.get('sistema_origen', 'Unknown')
        )

        return jsonify({
            "status": "success",
            "mongo_id": mongo_id,
            "mensaje": "Calificación registrada y grafo actualizado"
        }), 201

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500

@app.route('/api/trayectoria/<student_id>', methods=['GET'])
def obtener_trayectoria_completa(student_id):
    """
    Endpoint Híbrido:
    1. Consulta Neo4j para ver la estructura (materias y conexiones).
    2. Consulta MongoDB para traer los detalles de las notas.
    """
    # Obtener grafo
    query_grafo = """
    MATCH (e:Estudiante {id: $sid})-[r:CURSO]->(m:Materia)
    RETURN m.codigo as codigo, m.nombre as materia, m.sistema as sistema
    """
    trayectoria_grafo = []
    try:
        with driver_neo4j.session() as session:
            result = session.run(query_grafo, sid=student_id)
            trayectoria_grafo = [record.data() for record in result]
    except Exception as e:
        print(f"Error Neo4j: {e}")

    # Obtener detalles históricos de Mongo
    detalles_mongo = list(col_calificaciones.find(
        {"student_id": student_id},
        {"_id": 0, "materia": 1, "calificacion_data": 1, "fecha_registro": 1}
    ).sort("fecha_registro", DESCENDING))

    return jsonify({
        "student_id": student_id,
        "resumen_grafo": trayectoria_grafo, # Lo que ve Neo4j
        "historial_detalle": parse_json(detalles_mongo) # Lo que ve Mongo
    }), 200

@app.route('/api/materia', methods=['POST'])
def crear_materia():
    data = request.json
    if not data or 'codigoMateria' not in data:
        return jsonify({"error": "Código de materia obligatorio"}), 400
    
    try:
        
        res = col_materias.insert_one(data)
        
        # Crear el nodo materia en Neo4j
        with driver_neo4j.session() as session:
            session.run("MERGE (:Materia {id: $sid})", sid=str(res.inserted_id))

        return jsonify({"msg": "Materia creada", "id": str(res.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ARRANQUE ---
if __name__ == '__main__':
    try:
        # Verificar conexión a Neo4j al inicio
        driver_neo4j.verify_connectivity()
        print("[Neo4j] Conexión exitosa.")
        inicializar_indices()
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"Error fatal al iniciar: {e}")