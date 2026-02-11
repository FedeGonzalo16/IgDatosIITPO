from flask import Flask, request, jsonify
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import os
from datetime import datetime

app = Flask(__name__)

# --- CONEXIÓN A NEO4J ---
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "grafos2026")

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def get_session(self):
        return self.driver.session()

neo4j_conn = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

# ==========================================
# NODOS: INSTITUCIONES
# ==========================================

@app.route('/api/neo4j/instituciones', methods=['POST'])
def crear_institucion():
    """
    Crear nodo Institución en Neo4j
    {
        "id_mongo": "507f1f77bcf86cd799439011",
        "codigo": "AR-CNBA-001",
        "nombre": "Colegio Nacional Buenos Aires",
        "pais": "AR"
    }
    """
    datos = request.json
    
    if not datos or 'id_mongo' not in datos or 'codigo' not in datos:
        return jsonify({"error": "Campos obligatorios: id_mongo, codigo"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MERGE (i:Institucion {id_mongo: $id_mongo})
                SET i.codigo = $codigo,
                    i.nombre = $nombre,
                    i.pais = $pais,
                    i.fecha_creacion = datetime()
                RETURN i
                """,
                id_mongo=datos['id_mongo'],
                codigo=datos['codigo'],
                nombre=datos.get('nombre', ''),
                pais=datos.get('pais', 'AR')
            )
            return jsonify({"mensaje": "Institución creada", "codigo": datos['codigo']}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/instituciones/<id_mongo>', methods=['GET'])
def obtener_institucion(id_mongo):
    """
    Obtener institución por id_mongo
    """
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (i:Institucion {id_mongo: $id_mongo})
                RETURN i
                """,
                id_mongo=id_mongo
            )
            record = result.single()
            
            if not record:
                return jsonify({"error": "Institución no encontrada"}), 404
            
            return jsonify(dict(record['i'])), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# NODOS: MATERIAS
# ==========================================

@app.route('/api/neo4j/materias', methods=['POST'])
def crear_materia():
    """
    Crear nodo Materia en Neo4j
    {
        "id_mongo": "507f1f77bcf86cd799439012",
        "codigo": "AR-MAT-2024-001",
        "nombre": "Matemática",
        "nivel": "SECUNDARIO",
        "año_cursada": 4,
        "institucion_id_mongo": "507f1f77bcf86cd799439011"
    }
    """
    datos = request.json
    
    if not datos or 'id_mongo' not in datos or 'codigo' not in datos:
        return jsonify({"error": "Campos obligatorios: id_mongo, codigo"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            # Crear materia
            result = session.run(
                """
                MERGE (m:Materia {id_mongo: $id_mongo})
                SET m.codigo = $codigo,
                    m.nombre = $nombre,
                    m.nivel = $nivel,
                    m.año_cursada = $año_cursada,
                    m.fecha_creacion = datetime()
                RETURN m
                """,
                id_mongo=datos['id_mongo'],
                codigo=datos['codigo'],
                nombre=datos.get('nombre', ''),
                nivel=datos.get('nivel', 'SECUNDARIO'),
                año_cursada=datos.get('año_cursada', 1)
            )
            
            # Vincular a institución si se proporciona
            if datos.get('institucion_id_mongo'):
                session.run(
                    """
                    MATCH (m:Materia {id_mongo: $materia_id})
                    MATCH (i:Institucion {id_mongo: $institucion_id})
                    MERGE (m)-[:PERTENECE_A]->(i)
                    """,
                    materia_id=datos['id_mongo'],
                    institucion_id=datos['institucion_id_mongo']
                )
            
            return jsonify({"mensaje": "Materia creada", "codigo": datos['codigo']}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/materias/<id_mongo>', methods=['GET'])
def obtener_materia(id_mongo):
    """
    Obtener materia por id_mongo con su institución
    """
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (m:Materia {id_mongo: $id_mongo})
                OPTIONAL MATCH (m)-[:PERTENECE_A]->(i:Institucion)
                RETURN m, i
                """,
                id_mongo=id_mongo
            )
            record = result.single()
            
            if not record:
                return jsonify({"error": "Materia no encontrada"}), 404
            
            respuesta = {
                "materia": dict(record['m']),
                "institucion": dict(record['i']) if record['i'] else None
            }
            return jsonify(respuesta), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# NODOS: ESTUDIANTES
# ==========================================

@app.route('/api/neo4j/estudiantes', methods=['POST'])
def crear_estudiante():
    """
    Crear nodo Estudiante en Neo4j
    {
        "id_mongo": "507f1f77bcf86cd799439013",
        "legajo": "2024-ARG-001234",
        "nombre": "Juan",
        "apellido": "Pérez",
        "documento_numero": "12345678",
        "pais": "AR"
    }
    """
    datos = request.json
    
    if not datos or 'id_mongo' not in datos or 'legajo' not in datos:
        return jsonify({"error": "Campos obligatorios: id_mongo, legajo"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MERGE (e:Estudiante {id_mongo: $id_mongo})
                SET e.legajo = $legajo,
                    e.nombre = $nombre,
                    e.apellido = $apellido,
                    e.documento_numero = $documento_numero,
                    e.pais = $pais,
                    e.fecha_creacion = datetime()
                RETURN e
                """,
                id_mongo=datos['id_mongo'],
                legajo=datos['legajo'],
                nombre=datos.get('nombre', ''),
                apellido=datos.get('apellido', ''),
                documento_numero=datos.get('documento_numero', ''),
                pais=datos.get('pais', 'AR')
            )
            
            return jsonify({"mensaje": "Estudiante creado", "legajo": datos['legajo']}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/estudiantes/<id_mongo>', methods=['GET'])
def obtener_estudiante(id_mongo):
    """
    Obtener estudiante por id_mongo
    """
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $id_mongo})
                RETURN e
                """,
                id_mongo=id_mongo
            )
            record = result.single()
            
            if not record:
                return jsonify({"error": "Estudiante no encontrado"}), 404
            
            return jsonify(dict(record['e'])), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# RELACIONES: INSCRIPCIÓN
# ==========================================

@app.route('/api/neo4j/inscripciones', methods=['POST'])
def crear_inscripcion():
    """
    Inscribir un estudiante a una materia
    {
        "estudiante_id_mongo": "507f1f77bcf86cd799439013",
        "materia_id_mongo": "507f1f77bcf86cd799439012",
        "fecha_inscripcion": "2024-01-10",
        "estado": "ACTIVA"
    }
    """
    datos = request.json
    
    if not datos or 'estudiante_id_mongo' not in datos or 'materia_id_mongo' not in datos:
        return jsonify({"error": "Campos obligatorios: estudiante_id_mongo, materia_id_mongo"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $estudiante_id})
                MATCH (m:Materia {id_mongo: $materia_id})
                MERGE (e)-[r:INSCRIPTO_EN]->(m)
                SET r.fecha_inscripcion = $fecha_inscripcion,
                    r.estado = $estado,
                    r.fecha_relacion = datetime()
                RETURN e, m, r
                """,
                estudiante_id=datos['estudiante_id_mongo'],
                materia_id=datos['materia_id_mongo'],
                fecha_inscripcion=datos.get('fecha_inscripcion', str(datetime.now().date())),
                estado=datos.get('estado', 'ACTIVA')
            )
            
            record = result.single()
            if not record:
                return jsonify({"error": "Estudiante o materia no encontrados"}), 404
            
            return jsonify({
                "mensaje": "Inscripción creada",
                "estudiante": record['e']['legajo'],
                "materia": record['m']['codigo'],
                "estado": "ACTIVA"
            }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/inscripciones/<estudiante_id_mongo>/<materia_id_mongo>', methods=['PUT'])
def actualizar_inscripcion(estudiante_id_mongo, materia_id_mongo):
    """
    Actualizar estado de inscripción
    {
        "estado": "COMPLETADA" | "CANCELADA" | "ACTIVA"
    }
    """
    datos = request.json
    
    if not datos or 'estado' not in datos:
        return jsonify({"error": "Campo obligatorio: estado"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $estudiante_id})-[r:INSCRIPTO_EN]->(m:Materia {id_mongo: $materia_id})
                SET r.estado = $estado,
                    r.fecha_actualizacion = datetime()
                RETURN r
                """,
                estudiante_id=estudiante_id_mongo,
                materia_id=materia_id_mongo,
                estado=datos['estado']
            )
            
            if not result.single():
                return jsonify({"error": "Inscripción no encontrada"}), 404
            
            return jsonify({"mensaje": "Inscripción actualizada"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# RELACIONES: CURSADAS (Materias que cursó)
# ==========================================

@app.route('/api/neo4j/cursadas', methods=['POST'])
def registrar_cursada():
    """
    Registrar que un estudiante cursó una materia
    {
        "estudiante_id_mongo": "507f1f77bcf86cd799439013",
        "materia_id_mongo": "507f1f77bcf86cd799439012",
        "numero_intento": 1,
        "fecha_inicio": "2024-02-01"
    }
    """
    datos = request.json
    
    if not datos or 'estudiante_id_mongo' not in datos or 'materia_id_mongo' not in datos:
        return jsonify({"error": "Campos obligatorios: estudiante_id_mongo, materia_id_mongo"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $estudiante_id})
                MATCH (m:Materia {id_mongo: $materia_id})
                MERGE (e)-[r:CURSÓ]->(m)
                SET r.numero_intento = $numero_intento,
                    r.fecha_inicio = $fecha_inicio,
                    r.estado = 'EN_CURSO',
                    r.fecha_relacion = datetime()
                RETURN e, m, r
                """,
                estudiante_id=datos['estudiante_id_mongo'],
                materia_id=datos['materia_id_mongo'],
                numero_intento=datos.get('numero_intento', 1),
                fecha_inicio=datos.get('fecha_inicio', str(datetime.now().date()))
            )
            
            record = result.single()
            if not record:
                return jsonify({"error": "Estudiante o materia no encontrados"}), 404
            
            return jsonify({
                "mensaje": "Cursada registrada",
                "estudiante": record['e']['legajo'],
                "materia": record['m']['codigo'],
                "numero_intento": record['r']['numero_intento']
            }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/cursadas/<estudiante_id_mongo>/<materia_id_mongo>', methods=['GET'])
def obtener_cursada(estudiante_id_mongo, materia_id_mongo):
    """
    Obtener información de cursada de una materia
    """
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $estudiante_id})-[r:CURSÓ]->(m:Materia {id_mongo: $materia_id})
                RETURN e, m, r
                """,
                estudiante_id=estudiante_id_mongo,
                materia_id=materia_id_mongo
            )
            
            record = result.single()
            if not record:
                return jsonify({"error": "Cursada no encontrada"}), 404
            
            return jsonify({
                "estudiante": dict(record['e']),
                "materia": dict(record['m']),
                "cursada": dict(record['r'])
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/cursadas/<estudiante_id_mongo>/<materia_id_mongo>', methods=['PUT'])
def actualizar_cursada(estudiante_id_mongo, materia_id_mongo):
    """
    Actualizar estado de cursada
    {
        "estado": "EN_CURSO" | "COMPLETADA" | "APROBADA" | "REPROBADA"
    }
    """
    datos = request.json
    
    if not datos or 'estado' not in datos:
        return jsonify({"error": "Campo obligatorio: estado"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $estudiante_id})-[r:CURSÓ]->(m:Materia {id_mongo: $materia_id})
                SET r.estado = $estado,
                    r.fecha_actualizacion = datetime()
                RETURN r
                """,
                estudiante_id=estudiante_id_mongo,
                materia_id=materia_id_mongo,
                estado=datos['estado']
            )
            
            if not result.single():
                return jsonify({"error": "Cursada no encontrada"}), 404
            
            return jsonify({"mensaje": "Cursada actualizada"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# RELACIONES: ESTUDIA_EN
# ==========================================

@app.route('/api/neo4j/estudiantes/<estudiante_id_mongo>/institucion', methods=['POST'])
def vincular_estudiante_institucion(estudiante_id_mongo):
    """
    Vincular estudiante con institución donde estudia
    {
        "institucion_id_mongo": "507f1f77bcf86cd799439011",
        "fecha_inicio": "2024-01-01"
    }
    """
    datos = request.json
    
    if not datos or 'institucion_id_mongo' not in datos:
        return jsonify({"error": "Campo obligatorio: institucion_id_mongo"}), 400
    
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $estudiante_id})
                MATCH (i:Institucion {id_mongo: $institucion_id})
                MERGE (e)-[r:ESTUDIA_EN]->(i)
                SET r.fecha_inicio = $fecha_inicio,
                    r.fecha_relacion = datetime()
                RETURN e, i
                """,
                estudiante_id=estudiante_id_mongo,
                institucion_id=datos['institucion_id_mongo'],
                fecha_inicio=datos.get('fecha_inicio', str(datetime.now().date()))
            )
            
            record = result.single()
            if not record:
                return jsonify({"error": "Estudiante o institución no encontrados"}), 404
            
            return jsonify({
                "mensaje": "Víncolo institución creado",
                "estudiante": record['e']['legajo'],
                "institucion": record['i']['codigo']
            }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# CONSULTAS: TRAYECTORIA
# ==========================================

@app.route('/api/neo4j/estudiantes/<estudiante_id_mongo>/trayectoria', methods=['GET'])
def obtener_trayectoria_completa(estudiante_id_mongo):
    """
    Obtener trayectoria completa del estudiante:
    - Instituciones donde estudia
    - Materias inscritas
    - Materias cursadas
    """
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante {id_mongo: $estudiante_id})
                OPTIONAL MATCH (e)-[estudia:ESTUDIA_EN]->(i:Institucion)
                OPTIONAL MATCH (e)-[inscripto:INSCRIPTO_EN]->(m1:Materia)-[:PERTENECE_A]->(i1)
                OPTIONAL MATCH (e)-[curso:CURSÓ]->(m2:Materia)-[:PERTENECE_A]->(i2)
                RETURN e, 
                       collect({institucion: i, relacion: estudia}) as instituciones,
                       collect({materia: m1, relacion: inscripto, tipo: 'INSCRIPTO'}) as inscritos,
                       collect({materia: m2, relacion: curso, tipo: 'CURSÓ'}) as cursadas
                """,
                estudiante_id=estudiante_id_mongo
            )
            
            record = result.single()
            
            if not record or not record['e']:
                return jsonify({"error": "Estudiante no encontrado"}), 404
            
            # Limpiar nulos/None
            instituciones = [x for x in record['instituciones'] if x['institucion']]
            inscritos = [x for x in record['inscritos'] if x['materia']]
            cursadas = [x for x in record['cursadas'] if x['materia']]
            
            respuesta = {
                "estudiante": dict(record['e']),
                "instituciones": [
                    {
                        "institucion": dict(x['institucion']),
                        "fecha_inicio": x['relacion']['fecha_inicio']
                    } for x in instituciones
                ],
                "materias_inscritas": [
                    {
                        "materia": dict(x['materia']),
                        "estado": x['relacion']['estado'],
                        "fecha_inscripcion": x['relacion']['fecha_inscripcion']
                    } for x in inscritos
                ],
                "materias_cursadas": [
                    {
                        "materia": dict(x['materia']),
                        "numero_intento": x['relacion']['numero_intento'],
                        "estado": x['relacion']['estado'],
                        "fecha_inicio": x['relacion']['fecha_inicio']
                    } for x in cursadas
                ]
            }
            
            return jsonify(respuesta), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# CONSULTAS: ESTADÍSTICAS
# ==========================================

@app.route('/api/neo4j/estadisticas/estudiantes', methods=['GET'])
def estadisticas_estudiantes():
    """
    Estadísticas generales de estudiantes
    """
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (e:Estudiante)
                OPTIONAL MATCH (e)-[inscripto:INSCRIPTO_EN]->(m1:Materia)
                OPTIONAL MATCH (e)-[curso:CURSÓ]->(m2:Materia)
                RETURN count(DISTINCT e) as total_estudiantes,
                       count(DISTINCT m1) as materias_inscritas_unicas,
                       count(DISTINCT m2) as materias_cursadas_unicas,
                       count(inscripto) as total_inscripciones,
                       count(curso) as total_cursadas
                """
            )
            
            record = result.single()
            
            return jsonify({
                "total_estudiantes": record['total_estudiantes'],
                "materias_inscritas_unicas": record['materias_inscritas_unicas'],
                "materias_cursadas_unicas": record['materias_cursadas_unicas'],
                "total_inscripciones": record['total_inscripciones'],
                "total_cursadas": record['total_cursadas']
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/estadisticas/materias', methods=['GET'])
def estadisticas_materias():
    """
    Estadísticas de materias más inscriptas/cursadas
    """
    try:
        with neo4j_conn.get_session() as session:
            result = session.run(
                """
                MATCH (m:Materia)
                OPTIONAL MATCH (e1:Estudiante)-[:INSCRIPTO_EN]->(m)
                OPTIONAL MATCH (e2:Estudiante)-[:CURSÓ]->(m)
                RETURN m.codigo as codigo,
                       m.nombre as nombre,
                       count(DISTINCT e1) as inscritos,
                       count(DISTINCT e2) as cursadas
                ORDER BY inscritos DESC
                LIMIT 10
                """
            )
            
            materias = [dict(record) for record in result]
            
            return jsonify({"top_materias": materias}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# LIMPIAR BASE DE DATOS (DESARROLLO)
# ==========================================

@app.route('/api/neo4j/limpiar', methods=['DELETE'])
def limpiar_grafo():
    """
    ADVERTENCIA: Elimina todos los datos del grafo
    Solo usar en desarrollo
    """
    try:
        with neo4j_conn.get_session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            return jsonify({"mensaje": "Grafo limpiado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)