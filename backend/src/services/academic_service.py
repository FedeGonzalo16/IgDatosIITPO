from src.config.database import get_mongo, get_neo4j
from bson import ObjectId
from datetime import datetime

class AcademicService:
    # --- INSTITUCIONES ---
    @staticmethod
    def create_institucion(data):
        db = get_mongo()
        doc = {
            "codigo": data['codigo'],
            "nombre": data['nombre'],
            "pais": data['pais'],
            "metadata": {"created_at": datetime.utcnow(), "estado": "ACTIVA"}
        }
        res = db.instituciones.insert_one(doc)
        mongo_id = str(res.inserted_id)

        with get_neo4j() as session:
            session.run("""
                MERGE (i:Institucion {id_mongo: $id})
                SET i.codigo = $codigo, i.nombre = $nombre, i.pais = $pais
            """, id=mongo_id, **data)
        return mongo_id

    @staticmethod
    def get_instituciones():
        db = get_mongo()
        data = list(db.instituciones.find({"metadata.estado": "ACTIVA"}))
        for d in data: d['_id'] = str(d['_id'])
        return data

    # --- MATERIAS ---
    @staticmethod
    def create_materia(data):
        db = get_mongo()
        doc = {
            "codigo": data['codigo'],
            "nombre": data['nombre'],
            "nivel": data.get('nivel', 'UNIVERSITARIO'),
            "institucion_id": ObjectId(data['institucion_id']) if 'institucion_id' in data else None,
            "metadata": {"created_at": datetime.utcnow(), "estado": "VIGENTE"}
        }
        res = db.materias.insert_one(doc)
        materia_id = str(res.inserted_id)

        # Sync Neo4j: Crear Materia y conectar con Institución
        with get_neo4j() as session:
            session.run("""
                MERGE (m:Materia {id_mongo: $mid})
                SET m.codigo = $codigo, m.nombre = $nombre
                WITH m
                MATCH (i:Institucion {id_mongo: $iid})
                MERGE (m)-[:PERTENECE_A]->(i)
            """, mid=materia_id, iid=str(data.get('institucion_id')), 
               codigo=data['codigo'], nombre=data['nombre'])
        return materia_id

    @staticmethod
    def get_materias():
        db = get_mongo()
        data = list(db.materias.find({"metadata.estado": "VIGENTE"}))
        for d in data: 
            d['_id'] = str(d['_id'])
            d['institucion_id'] = str(d['institucion_id']) if d.get('institucion_id') else None
        return data