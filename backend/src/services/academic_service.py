from src.config.database import get_mongo, get_neo4j
from bson import ObjectId
from datetime import datetime

class AcademicService:
    # Valores permitidos para el nivel educativo de una institución
    NIVELES_VALIDOS = {"SECUNDARIO", "UNIVERSITARIO", "TERCIARIO"}

    # Creamos una institución
    @staticmethod
    def create_institucion(data):
        db = get_mongo()
        # Obtenemos el nivel de la institución
        nivel = data.get('nivel', 'UNIVERSITARIO').upper()
        # Si el nivel no es válido, seteamos el nivel por defecto
        if nivel not in AcademicService.NIVELES_VALIDOS:
            nivel = 'UNIVERSITARIO'
        # Creamos el documento de la institución en Mongo
        doc = {
            "codigo": data['codigo'],
            "nombre": data['nombre'],
            "pais": data['pais'],
            "nivel": nivel,
            "metadata": {"created_at": datetime.utcnow(), "estado": "ACTIVA"}
        }
        # Insertamos la institución en Mongo
        res = db.instituciones.insert_one(doc)
        # Obtenemos el id de la institución
        mongo_id = str(res.inserted_id)

        # El nodo en Neo4j permite luego conectar estudiantes, materias y profesores mediante relaciones
        with get_neo4j() as session:
            session.run("""
                MERGE (i:Institucion {id_mongo: $id})
                SET i.codigo = $codigo, i.nombre = $nombre, i.pais = $pais, i.nivel = $nivel
            """, id=mongo_id, codigo=data['codigo'], nombre=data['nombre'],
                pais=data['pais'], nivel=nivel)
        # Retornamos el id de la institución
        return mongo_id

    # Obtenemos todas las instituciones
    @staticmethod
    def get_instituciones():
        db = get_mongo()
        # Obtenemos todas las instituciones en Mongo
        data = list(db.instituciones.find({"metadata.estado": "ACTIVA"}))
        for d in data:
            d['_id'] = str(d['_id'])
        return data

    # --- MATERIAS ---
    
    # Creamos una materia
    @staticmethod
    def create_materia(data):
        db = get_mongo()
        # Creamos el documento de la materia en Mongo
        doc = {
            "codigo": data['codigo'],
            "nombre": data['nombre'],
            "nivel": data.get('nivel', 'UNIVERSITARIO'),
            "institucion_id": ObjectId(data['institucion_id']) if 'institucion_id' in data else None,
            "metadata": {"created_at": datetime.utcnow(), "estado": "VIGENTE"}
        }
        # Insertamos la materia en Mongo
        res = db.materias.insert_one(doc)
        # Obtenemos el id de la materia
        materia_id = str(res.inserted_id)

        # Creamos el nodo Materia y lo conectamos a su institución en el grafo
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

    # Obtenemos todas las materias
    @staticmethod
    def get_materias():
        db = get_mongo()
        # Obtenemos todas las materias en Mongo
        data = list(db.materias.find({"metadata.estado": "VIGENTE"}))
        for d in data: 
            d['_id'] = str(d['_id'])
            d['institucion_id'] = str(d['institucion_id']) if d.get('institucion_id') else None
        return data

    # Obtenemos una institución por su id
    @staticmethod
    def get_institucion_by_id(uid):
        db = get_mongo()
        # Obtenemos la institución en Mongo
        inst = db.instituciones.find_one({"_id": ObjectId(uid)})
        if inst:
            inst['_id'] = str(inst['_id'])
        return inst

    # Actualizamos una institución
    @staticmethod
    def update_institucion(uid, data):
        db = get_mongo()
        # Creamos el documento de actualización en Mongo
        update_data = {}
        if 'codigo' in data: update_data['codigo'] = data['codigo']
        if 'nombre' in data: update_data['nombre'] = data['nombre']
        if 'pais'   in data: update_data['pais']   = data['pais']
        if 'nivel'  in data:
            nivel = data['nivel'].upper()
            if nivel not in AcademicService.NIVELES_VALIDOS:
                nivel = 'UNIVERSITARIO'
            update_data['nivel'] = nivel
        # Actualizamos la institución en Mongo
        db.instituciones.update_one({"_id": ObjectId(uid)}, {"$set": update_data})
        
        # Sincronizamos los cambios al nodo de Neo4j para mantener consistencia
        with get_neo4j() as session:
            session.run("""
                MATCH (i:Institucion {id_mongo: $id})
                SET i.codigo = $codigo, i.nombre = $nombre, i.pais = $pais, i.nivel = $nivel
            """, id=uid, codigo=data.get('codigo', ''), nombre=data.get('nombre', ''),
                pais=data.get('pais', ''), nivel=update_data.get('nivel', ''))
        return True

    # Eliminamos una institución
    @staticmethod
    def delete_institucion(uid):
        db = get_mongo()
        # Soft delete: cambiamos el estado para no perder el historial de relaciones
        db.instituciones.update_one({"_id": ObjectId(uid)}, {"$set": {"metadata.estado": "INACTIVA"}})
        return True

    # Obtenemos una materia por su id
    @staticmethod
    def get_materia_by_id(uid):
        db = get_mongo()
        materia = db.materias.find_one({"_id": ObjectId(uid)})
        if materia:
            materia['_id'] = str(materia['_id'])
            materia['institucion_id'] = str(materia['institucion_id']) if materia.get('institucion_id') else None
        return materia

    # Actualizamos una materia
    @staticmethod
    def update_materia(uid, data):
        db = get_mongo()
        # Creamos el documento de actualización en Mongo
        update_data = {}
        if 'codigo' in data: update_data['codigo'] = data['codigo']
        if 'nombre' in data: update_data['nombre'] = data['nombre']
        if 'nivel'  in data: update_data['nivel']  = data['nivel']
        # Actualizamos la materia en Mongo
        db.materias.update_one({"_id": ObjectId(uid)}, {"$set": update_data})
        
        # Sincronizamos los cambios al nodo de Neo4j para mantener consistencia
        with get_neo4j() as session:
            session.run("""
                MATCH (m:Materia {id_mongo: $id})
                SET m.codigo = $codigo, m.nombre = $nombre
            """, id=uid, codigo=data.get('codigo', ''), nombre=data.get('nombre', ''))
        return True

    # Eliminamos una materia
    @staticmethod
    def delete_materia(uid):
        db = get_mongo()
        # Soft delete: cambiamos el estado para no perder el historial de relaciones
        db.materias.update_one({"_id": ObjectId(uid)}, {"$set": {"metadata.estado": "INACTIVA"}})
        return True

    # Obtenemos las materias de un estudiante
    @staticmethod
    def get_materias_by_estudiante(est_id):
        """Obtiene las materias de un estudiante navegando el grafo (CURSANDO y CURSÓ)."""
        materias = []
        # Obtenemos las materias en el grafo
        with get_neo4j() as session:
            result = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO|CURSÓ]->(m:Materia)
                RETURN DISTINCT m.id_mongo as materia_id, m.nombre as nombre, 
                       m.codigo as codigo, type(r) as tipo_relacion
            """, est_id=est_id)
            for record in result:
                materias.append({
                    "materia_id": record["materia_id"],
                    "nombre": record["nombre"],
                    "codigo": record["codigo"],
                    "tipo": record["tipo_relacion"]
                })
        return materias

    # --- CARRERAS ---

    # Creamos una carrera
    @staticmethod
    def create_carrera(data):
        """Crea entidad Carrera en Mongo y nodo en Neo4j."""
        db = get_mongo()
        # Creamos el documento de la carrera en Mongo
        doc = {
            "codigo": data.get("codigo", ""),
            "nombre": data["nombre"],
            "materias_ids": [],
            "metadata": {"created_at": datetime.utcnow(), "estado": "VIGENTE"}
        }
        # Insertamos la carrera en Mongo
        res = db.carreras.insert_one(doc)
        carrera_id = str(res.inserted_id)

        # Creamos el nodo Carrera en Neo4j
        with get_neo4j() as session:
            session.run("""
                MERGE (c:Carrera {id_mongo: $id})
                SET c.codigo = $codigo, c.nombre = $nombre
            """, id=carrera_id, codigo=doc["codigo"], nombre=doc["nombre"])
        return carrera_id

    # Obtenemos todas las carreras
    @staticmethod
    def get_carreras():
        db = get_mongo()
        # Obtenemos todas las carreras en Mongo
        data = list(db.carreras.find({"metadata.estado": "VIGENTE"}))
        for d in data:
            d["_id"] = str(d["_id"])
            d["materias_ids"] = [str(oid) for oid in d.get("materias_ids", [])]
        return data

    # Obtenemos una carrera por su id
    @staticmethod
    def get_carrera_by_id(uid):
        db = get_mongo()
        # Obtenemos la carrera en Mongo
        carrera = db.carreras.find_one({"_id": ObjectId(uid), "metadata.estado": "VIGENTE"})
        if carrera:
            carrera["_id"] = str(carrera["_id"])
            carrera["materias_ids"] = [str(oid) for oid in carrera.get("materias_ids", [])]
        return carrera

    # Agregamos una materia a una carrera
    @staticmethod
    def agregar_materia_a_carrera(carrera_id, materia_id):
        """Relaciona una materia a la carrera: (Carrera)-[:CONTIENE]->(Materia) en Neo4j y Mongo."""
        # Creamos el documento de actualización en Mongo
        db = get_mongo()
        oid_materia = ObjectId(materia_id)
        # $addToSet evita duplicados si la materia ya fue agregada
        # Actualizamos la carrera en Mongo
        db.carreras.update_one(
            {"_id": ObjectId(carrera_id), "metadata.estado": "VIGENTE"},
            {"$addToSet": {"materias_ids": oid_materia}}
        )
        with get_neo4j() as session:
            session.run("""
                MATCH (c:Carrera {id_mongo: $carrera_id})
                MATCH (m:Materia {id_mongo: $materia_id})
                MERGE (c)-[:CONTIENE]->(m)
            """, carrera_id=carrera_id, materia_id=materia_id)
        return True

    # Obtenemos las materias de una carrera
    @staticmethod
    def get_materias_de_carrera(carrera_id):
        """Materias que CONTIENE la carrera, consultadas desde Neo4j."""
        # Obtenemos las materias en el grafo
        with get_neo4j() as session:
            result = session.run("""
                MATCH (c:Carrera {id_mongo: $carrera_id})-[:CONTIENE]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as nombre, m.codigo as codigo
            """, carrera_id=carrera_id)
            return [{"materia_id": r["materia_id"], "nombre": r["nombre"], "codigo": r["codigo"]} for r in result]

    # Obtenemos las materias faltantes para recibirse
    @staticmethod
    def get_materias_faltantes_para_recibirse(est_id, carrera_id):
        """
        Compara materias aprobadas por el alumno vs materias que requiere la carrera.
        Retorna las que faltan.
        """
        # Obtenemos las materias aprobadas por el estudiante
        with get_neo4j() as session:
            aprobadas = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(m:Materia)
                WHERE r.estado = 'APROBADO'
                RETURN m.id_mongo as materia_id
            """, est_id=est_id)
            ids_aprobadas = {r["materia_id"] for r in aprobadas}

            # Obtenemos las materias de la carrera
            de_carrera = session.run("""
                MATCH (c:Carrera {id_mongo: $carrera_id})-[:CONTIENE]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as nombre, m.codigo as codigo
            """, carrera_id=carrera_id)
            materias_carrera = list(de_carrera)

        # Obtenemos las materias faltantes
        faltantes = [
            {"materia_id": r["materia_id"], "nombre": r["nombre"], "codigo": r["codigo"]}
            for r in materias_carrera
            if r["materia_id"] not in ids_aprobadas
        ]
        # Retornamos las materias faltantes
        return {
            "materias_faltantes": faltantes,
            "cantidad_faltantes": len(faltantes),
            "materias_aprobadas_de_carrera": len(ids_aprobadas & {r["materia_id"] for r in materias_carrera}),
            "total_materias_carrera": len(materias_carrera),
        }
