from flask import Flask, request, jsonify
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import os

app = Flask(__name__)

# --- CONEXIÓN A NEO4J ---
uri = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")

class Neo4jDriver:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    @staticmethod
    def _create_usuario(tx, id_mongo, nombre, apellido, dni):
        result = tx.run(
            """
            CREATE (u:Usuario {
                id_mongo: $id_mongo,
                nombre: $nombre,
                apellido: $apellido,
                dni: $dni,
                creado_en: datetime()
            })
            RETURN u
            """,
            id_mongo=id_mongo,
            nombre=nombre,
            apellido=apellido,
            dni=dni
        )
        return result.single()

driver = Neo4jDriver(uri, user, password)

# --- ENDPOINTS ---

@app.route('/api/neo4j/usuarios', methods=['POST'])
def crear_usuario():
    """
    Recibe datos de MongoDB incluyendo el id_mongo
    {
        "id_mongo": "507f1f77bcf86cd799439011",
        "nombre": "Gonzalo",
        "apellido": "Gomez",
        "dni": 12345678
    }
    """
    datos = request.json
    
    if not datos or 'id_mongo' not in datos or 'dni' not in datos:
        return jsonify({"error": "Campos obligatorios: id_mongo, dni"}), 400
    
    try:
        with driver.driver.session() as session:
            result = session.execute_write(
                driver._create_usuario,
                datos['id_mongo'],
                datos.get('nombre', ''),
                datos.get('apellido', ''),
                datos['dni']
            )
            return jsonify({
                "mensaje": "Usuario creado en Neo4j",
                "id_mongo": datos['id_mongo']
            }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/usuarios/<id_mongo>', methods=['GET'])
def obtener_usuario(id_mongo):
    """
    Busca un usuario por su id_mongo de MongoDB
    """
    try:
        with driver.driver.session() as session:
            result = session.run(
                """
                MATCH (u:Usuario {id_mongo: $id_mongo})
                RETURN u
                """,
                id_mongo=id_mongo
            )
            usuario = result.single()
            
            if not usuario:
                return jsonify({"error": "Usuario no encontrado"}), 404
            
            return jsonify(usuario['u']), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/neo4j/usuarios/<id_mongo>', methods=['PUT'])
def actualizar_usuario(id_mongo):
    """
    Actualiza propiedades del usuario
    """
    datos = request.json
    
    if not datos:
        return jsonify({"error": "Sin datos para actualizar"}), 400
    
    try:
        with driver.driver.session() as session:
            result = session.run(
                """
                MATCH (u:Usuario {id_mongo: $id_mongo})
                SET u += $datos
                RETURN u
                """,
                id_mongo=id_mongo,
                datos=datos
            )
            usuario = result.single()
            
            if not usuario:
                return jsonify({"error": "Usuario no encontrado"}), 404
            
            return jsonify({"mensaje": "Usuario actualizado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5001)