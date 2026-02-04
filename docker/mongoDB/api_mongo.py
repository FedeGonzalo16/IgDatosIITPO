from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import datetime

app = Flask(__name__)

# --- CONEXIÓN A MONGODB ---
uri = "mongodb://root:estudiantes2026@localhost:27017/admin"
client = MongoClient(uri)
db = client["registro_academico"]
coleccion_estudiantes = db["estudiantes"]

@app.route('/api/estudiantes', methods=['POST'])
def cargar_estudiante():

    datos_recibidos = request.json
    

    if not datos_recibidos or 'dni' not in datos_recibidos:
        return jsonify({"error": "El campo 'dni' es obligatorio"}), 400

    try:
        resultado = coleccion_estudiantes.insert_one(datos_recibidos)
        
        return jsonify({
            "mensaje": "Estudiante cargado correctamente",
            "id_mongo": str(resultado.inserted_id),
            "nombre": datos_recibidos.get('nombre', ''),
            "apellido": datos_recibidos.get('apellido', ''),
            "dni": datos_recibidos.get('dni', '')
        }), 201

    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500
    
    

@app.route('/api/estudiantes/<id_estudiante>', methods=['GET'])
def obtener_estudiante(id_estudiante):
    try:
        # Buscamos por _id (ObjectId de Mongo)
        estudiante = coleccion_estudiantes.find_one({"_id": ObjectId(id_estudiante)})
        
        if not estudiante:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        # Convertimos ObjectId a string para JSON
        estudiante['_id'] = str(estudiante['_id'])
        
        return jsonify(estudiante), 200

    except Exception as e:
        return jsonify({"error": "ID inválido o error de servidor"}), 500
    

@app.route('/api/estudiantes/<id_estudiante>', methods=['PUT'])
def actualizar_estudiante(id_estudiante):
    datos_nuevos = request.json
    
    if not datos_nuevos:
        return jsonify({"error": "Sin datos para actualizar"}), 400

    try:
        # Actualizamos solo los campos que nos envíen
        resultado = coleccion_estudiantes.update_one(
            {"_id": ObjectId(id_estudiante)},
            {"$set": datos_nuevos}
        )

        if resultado.matched_count == 0:
            return jsonify({"error": "Estudiante no encontrado"}), 404

        return jsonify({"mensaje": "Datos actualizados correctamente"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)