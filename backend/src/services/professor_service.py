from src.config.database import get_mongo, get_neo4j
from src.services.metadata_service import MetadataService
from bson import ObjectId

class ProfessorService:
    @staticmethod
    def create(data):
        db = get_mongo()
        
        # 1. Mongo (Datos puros)
        doc = {
            "legajo_docente": data['legajo_docente'],
            "nombre": data['nombre'],
            "apellido": data['apellido'],
            "especialidad": data.get('especialidad', '')
        }
        res = db.profesores.insert_one(doc)
        mongo_id = str(res.inserted_id)

        # 2. Metadatos a Cassandra
        MetadataService.save_metadata('profesor', mongo_id, 'ACTIVO')

        # 3. Neo4j: Nodo Profesor
        with get_neo4j() as session:
            session.run("""
                MERGE (p:Profesor {id_mongo: $id})
                SET p.nombre = $nombre, p.legajo = $legajo
            """, id=mongo_id, nombre=f"{data['nombre']} {data['apellido']}", legajo=data['legajo_docente'])
            
        return mongo_id

    @staticmethod
    def asignar_materia(prof_id, mat_id, activo=True):
        """Crea la relación DICTAN (activo) o DICTARON (histórico)"""
        relacion = "DICTAN" if activo else "DICTARON"
        
        query = f"""
            MATCH (p:Profesor {{id_mongo: $pid}})
            MATCH (m:Materia {{id_mongo: $mid}})
            MERGE (p)-[r:{relacion}]->(m)
            SET r.fecha_asignacion = datetime()
        """
        with get_neo4j() as session:
            session.run(query, pid=prof_id, mid=mat_id)
            
        # Opcional: Si pasa a inactivo, podríamos borrar la relación DICTAN
        if not activo:
            with get_neo4j() as session:
                session.run("""
                    MATCH (p:Profesor {id_mongo: $pid})-[r:DICTAN]->(m:Materia {id_mongo: $mid})
                    DELETE r
                """, pid=prof_id, mid=mat_id)
                
        return True