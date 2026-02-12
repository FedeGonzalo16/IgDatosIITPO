from src.config.database import get_mongo, get_neo4j
from bson import ObjectId
from datetime import datetime

class StudentService:
    @staticmethod
    def create(data):
        db = get_mongo()
        # 1. Mongo
        doc = {
            "legajo": data['legajo'],
            "nombre": data['nombre'],
            "apellido": data['apellido'],
            "email": data.get('email', ''),
            "pais": data.get('pais', 'AR'),
            "metadata": {"created_at": datetime.utcnow(), "estado": "ACTIVO"}
        }
        res = db.estudiantes.insert_one(doc)
        mongo_id = str(res.inserted_id)

        # 2. Neo4j Sync
        try:
            with get_neo4j() as session:
                session.run("""
                    MERGE (e:Estudiante {id_mongo: $id})
                    SET e.legajo = $legajo, e.nombre = $nombre, e.pais = $pais
                """, id=mongo_id, legajo=data['legajo'], 
                   nombre=f"{data['nombre']} {data['apellido']}", pais=data.get('pais', 'AR'))
        except Exception as e:
            print(f"[SYNC ERROR] Neo4j: {e}")
        return mongo_id

    @staticmethod
    def get_all():
        db = get_mongo()
        students = list(db.estudiantes.find({"metadata.estado": "ACTIVO"}))
        for s in students: s['_id'] = str(s['_id'])
        return students

    @staticmethod
    def get_by_id(uid):
        db = get_mongo()
        s = db.estudiantes.find_one({"_id": ObjectId(uid)})
        if s: s['_id'] = str(s['_id'])
        return s

    @staticmethod
    def update(uid, data):
        db = get_mongo()
        db.estudiantes.update_one({"_id": ObjectId(uid)}, {"$set": data})
        
        # Sync Neo4j
        if 'nombre' in data or 'apellido' in data:
            with get_neo4j() as session:
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $id})
                    SET e.nombre = $nombre
                """, id=uid, nombre=f"{data.get('nombre', '')} {data.get('apellido', '')}")
        return True

    @staticmethod
    def delete(uid):
        db = get_mongo()
        # Soft Delete
        db.estudiantes.update_one({"_id": ObjectId(uid)}, {"$set": {"metadata.estado": "INACTIVO"}})
        # Neo4j: Opcional borrar nodo o marcarlo
        with get_neo4j() as session:
            session.run("MATCH (e:Estudiante {id_mongo: $id}) DETACH DELETE e", id=uid)
        return True