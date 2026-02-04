import requests
import json

MONGO_API = "http://localhost:5000/api/estudiantes"
NEO4J_API = "http://localhost:5001/api/neo4j/usuarios"

def sincronizar_estudiante(datos_estudiante):
    """
    Inserta en MongoDB y luego en Neo4j
    """
    try:
        # 1. Insertar en MongoDB
        response_mongo = requests.post(MONGO_API, json=datos_estudiante)
        
        if response_mongo.status_code != 201:
            return {"error": "Fallo en MongoDB"}, 500
        
        datos_mongo = response_mongo.json()
        id_mongo = datos_mongo['id_mongo']
        
        # 2. Crear en Neo4j con el id_mongo
        datos_neo4j = {
            "id_mongo": id_mongo,
            "nombre": datos_mongo.get('nombre', ''),
            "apellido": datos_mongo.get('apellido', ''),
            "dni": datos_mongo.get('dni', '')
        }
        
        response_neo4j = requests.post(NEO4J_API, json=datos_neo4j)
        
        if response_neo4j.status_code != 201:
            return {"error": "Fallo en Neo4j", "id_mongo": id_mongo}, 500
        
        return {
            "mensaje": "Estudiante sincronizado en MongoDB y Neo4j",
            "id_mongo": id_mongo
        }, 201
        
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    # Ejemplo de uso
    estudiante = {
        "nombre": "Gonzalo",
        "apellido": "Gomez",
        "dni": 12345678,
        "carrera": "Ingenieria de Datos"
    }
    
    resultado, status = sincronizar_estudiante(estudiante)
    print(json.dumps(resultado, indent=2))
