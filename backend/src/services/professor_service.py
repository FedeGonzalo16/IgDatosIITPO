from src.config.database import get_mongo, get_neo4j
from src.services.metadata_service import MetadataService
from bson import ObjectId

class ProfessorService:
    @staticmethod
    def create(data):
        db = get_mongo()
        doc = {
            "legajo_docente": data.get('legajo_docente', ''),
            "nombre":         data.get('nombre', ''),
            "apellido":       data.get('apellido', ''),
            "especialidad":   data.get('especialidad', ''),
            "email":          data.get('email', ''),
            "password":       data.get('password', '123456'),
            "rol":            data.get('rol', 'profesor'),
            "estado":         "ACTIVO"
        }
        res = db.profesores.insert_one(doc)
        mongo_id = str(res.inserted_id)

        MetadataService.save_metadata('profesor', mongo_id, 'ACTIVO')

        with get_neo4j() as session:
            session.run("""
                MERGE (p:Profesor {id_mongo: $id})
                SET p.nombre = $nombre, p.legajo = $legajo
            """, id=mongo_id,
                nombre=f"{data.get('nombre', '')} {data.get('apellido', '')}",
                legajo=data.get('legajo_docente', ''))
            
        return mongo_id

    @staticmethod
    def asignar_materia(prof_id, mat_id, activo=True):
        """
        Asigna o desasigna una materia a un profesor.
        activo=True  → crea DICTAN (relación vigente)
        activo=False → crea DICTARON (relación histórica) y elimina DICTAN
        """
        relacion = "DICTAN" if activo else "DICTARON"
        query = f"""
            MATCH (p:Profesor {{id_mongo: $pid}})
            MATCH (m:Materia {{id_mongo: $mid}})
            MERGE (p)-[r:{relacion}]->(m)
            SET r.fecha_asignacion = datetime()
        """
        with get_neo4j() as session:
            session.run(query, pid=prof_id, mid=mat_id)
            
        if not activo:
            # Si se desasigna, eliminamos la relación activa pero dejamos el historial en DICTARON
            with get_neo4j() as session:
                session.run("""
                    MATCH (p:Profesor {id_mongo: $pid})-[r:DICTAN]->(m:Materia {id_mongo: $mid})
                    DELETE r
                """, pid=prof_id, mid=mat_id)
                
        return True

    @staticmethod
    def get_all():
        db = get_mongo()
        profesores = list(db.profesores.find())
        for p in profesores:
            p['_id'] = str(p['_id'])
        return profesores

    @staticmethod
    def get_by_id(uid):
        db = get_mongo()
        prof = db.profesores.find_one({"_id": ObjectId(uid)})
        if prof:
            prof['_id'] = str(prof['_id'])
        return prof

    @staticmethod
    def get_by_email(email):
        db = get_mongo()
        prof = db.profesores.find_one({"email": email})
        if prof:
            prof['_id'] = str(prof['_id'])
        return prof

    @staticmethod
    def get_materias_by_profesor(prof_id):
        """Obtiene las materias que dicta actualmente (relación DICTAN en Neo4j)."""
        with get_neo4j() as session:
            result = session.run("""
                MATCH (p:Profesor {id_mongo: $pid})-[r:DICTAN]->(m:Materia)
                RETURN m.id_mongo AS materia_id, m.nombre AS nombre, m.codigo AS codigo
            """, pid=prof_id)
            return [{"materia_id": r["materia_id"], "nombre": r["nombre"], "codigo": r["codigo"]} for r in result]

    @staticmethod
    def get_alumnos_by_materia(mat_id):
        """
        Devuelve los alumnos que están cursando una materia junto con sus notas parciales.
        Útil para que el profesor vea el estado del aula en tiempo real.
        """
        with get_neo4j() as session:
            result = session.run("""
                MATCH (e:Estudiante)-[r:CURSANDO]->(m:Materia {id_mongo: $mid})
                RETURN e.id_mongo AS estudiante_id, e.nombre AS nombre, e.apellido AS apellido,
                       r.primer_parcial AS primer_parcial, r.segundo_parcial AS segundo_parcial,
                       r.final AS final, r.previo AS previo, r.estado AS estado
            """, mid=mat_id)
            
            alumnos = []
            for r in result:
                alumnos.append({
                    "estudiante_id":  r["estudiante_id"],
                    "nombre_completo": f"{r['nombre']} {r['apellido']}".strip(),
                    "notas": {
                        "primer_parcial":  r["primer_parcial"],
                        "segundo_parcial": r["segundo_parcial"],
                        "final":           r["final"],
                        "previo":          r["previo"]
                    },
                    "estado": r["estado"]
                })
            return alumnos

    @staticmethod
    def update(uid, data):
        db = get_mongo()
        update_data = {}
        if 'nombre'        in data: update_data['nombre']        = data['nombre']
        if 'apellido'      in data: update_data['apellido']      = data['apellido']
        if 'legajo_docente' in data: update_data['legajo_docente'] = data['legajo_docente']
        if 'especialidad'  in data: update_data['especialidad']  = data['especialidad']
        
        db.profesores.update_one({"_id": ObjectId(uid)}, {"$set": update_data})
        
        with get_neo4j() as session:
            session.run("""
                MATCH (p:Profesor {id_mongo: $id})
                SET p.nombre = $nombre, p.legajo = $legajo
            """, id=uid,
                nombre=f"{data.get('nombre', '')} {data.get('apellido', '')}",
                legajo=data.get('legajo_docente', ''))
        return True

    @staticmethod
    def delete(uid):
        db = get_mongo()
        # Soft delete en Mongo + Cassandra; hard delete en Neo4j para limpiar el grafo
        db.profesores.update_one({"_id": ObjectId(uid)}, {"$set": {"estado": "INACTIVO"}})
        MetadataService.save_metadata('profesor', uid, 'INACTIVO')
        with get_neo4j() as session:
            session.run("MATCH (p:Profesor {id_mongo: $id}) DETACH DELETE p", id=uid)
        return True
