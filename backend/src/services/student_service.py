from src.config.database import get_mongo, get_neo4j
from bson import ObjectId
from datetime import datetime
from src.services.metadata_service import MetadataService

class StudentService:
    @staticmethod
    def create(data):
        db = get_mongo()
        # 1. Mongo (LIMPIO, SIN METADATOS)
        doc = {
            "legajo": data['legajo'],
            "nombre": data['nombre'],
            "apellido": data['apellido'],
            "email": data.get('email', ''),
            "institucion_id": data.get('institucion_id'),
            "pais": data.get('pais', 'AR')
        }
        res = db.estudiantes.insert_one(doc)
        mongo_id = str(res.inserted_id)
        
        print(f"[CREATE] Creado estudiante en MongoDB: {mongo_id}, nombre={data['nombre']}")

        # 2. Metadatos EXCLUSIVOS en Cassandra
        MetadataService.save_metadata('estudiante', mongo_id, 'ACTIVO')

        # 3. Neo4j Sync - Crear nodo Estudiante
        with get_neo4j() as session:
            session.run("""
                MERGE (e:Estudiante {id_mongo: $id}) 
                SET e.nombre = $nombre,
                    e.apellido = $apellido,
                    e.email = $email,
                    e.legajo = $legajo
            """, id=mongo_id, nombre=data['nombre'], apellido=data['apellido'], 
                email=data.get('email', ''), legajo=data['legajo'])
            
            print(f"[CREATE] Nodo Estudiante creado en Neo4j: {mongo_id}")
        
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

    @staticmethod
    def get_by_email(email):
        db = get_mongo()
        student = db.estudiantes.find_one({"email": email})
        if student:
            student['_id'] = str(student['_id'])
        return student

    @staticmethod
    def sync_to_neo4j(uid):
        """Sincroniza un estudiante existente en MongoDB con Neo4j"""
        db = get_mongo()
        student = db.estudiantes.find_one({"_id": ObjectId(uid)})
        
        if not student:
            raise Exception(f"Estudiante {uid} no encontrado")
        
        mongo_id = str(student['_id'])
        print(f"[SYNC] Sincronizando estudiante {mongo_id} a Neo4j")
        
        with get_neo4j() as session:
            # Crear o actualizar nodo Estudiante
            session.run("""
                MERGE (e:Estudiante {id_mongo: $id})
                SET e.nombre = $nombre,
                    e.apellido = $apellido,
                    e.email = $email,
                    e.legajo = $legajo
            """, id=mongo_id, nombre=student.get('nombre', ''), 
                apellido=student.get('apellido', ''),
                email=student.get('email', ''),
                legajo=student.get('legajo', ''))
            
            print(f"[SYNC] Estudiante {mongo_id} sincronizado en Neo4j")
        
        return True
