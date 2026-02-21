from src.config.database import get_mongo, get_neo4j
from bson import ObjectId
from datetime import datetime

class AcademicService:
    # --- INSTITUCIONES ---
    NIVELES_VALIDOS = {"SECUNDARIO", "UNIVERSITARIO", "TERCIARIO"}

    @staticmethod
    def create_institucion(data):
        db = get_mongo()
        nivel = data.get('nivel', 'UNIVERSITARIO').upper()
        if nivel not in AcademicService.NIVELES_VALIDOS:
            nivel = 'UNIVERSITARIO'
        doc = {
            "codigo": data['codigo'],
            "nombre": data['nombre'],
            "pais": data['pais'],
            "nivel": nivel,
            "metadata": {"created_at": datetime.utcnow(), "estado": "ACTIVA"}
        }
        res = db.instituciones.insert_one(doc)
        mongo_id = str(res.inserted_id)

        with get_neo4j() as session:
            session.run("""
                MERGE (i:Institucion {id_mongo: $id})
                SET i.codigo = $codigo, i.nombre = $nombre, i.pais = $pais, i.nivel = $nivel
            """, id=mongo_id, codigo=data['codigo'], nombre=data['nombre'],
                pais=data['pais'], nivel=nivel)
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

    @staticmethod
    def get_institucion_by_id(uid):
        db = get_mongo()
        inst = db.instituciones.find_one({"_id": ObjectId(uid)})
        if inst:
            inst['_id'] = str(inst['_id'])
        return inst

    @staticmethod
    def update_institucion(uid, data):
        db = get_mongo()
        update_data = {}
        if 'codigo' in data:
            update_data['codigo'] = data['codigo']
        if 'nombre' in data:
            update_data['nombre'] = data['nombre']
        if 'pais' in data:
            update_data['pais'] = data['pais']
        if 'nivel' in data:
            nivel = data['nivel'].upper()
            if nivel not in AcademicService.NIVELES_VALIDOS:
                nivel = 'UNIVERSITARIO'
            update_data['nivel'] = nivel
        db.instituciones.update_one({"_id": ObjectId(uid)}, {"$set": update_data})
        
        # Sync Neo4j
        with get_neo4j() as session:
            session.run("""
                MATCH (i:Institucion {id_mongo: $id})
                SET i.codigo = $codigo, i.nombre = $nombre, i.pais = $pais, i.nivel = $nivel
            """, id=uid, codigo=data.get('codigo', ''), nombre=data.get('nombre', ''),
                pais=data.get('pais', ''), nivel=update_data.get('nivel', ''))
        return True

    @staticmethod
    def delete_institucion(uid):
        db = get_mongo()
        db.instituciones.update_one({"_id": ObjectId(uid)}, {"$set": {"metadata.estado": "INACTIVA"}})
        return True

    @staticmethod
    def get_materia_by_id(uid):
        db = get_mongo()
        materia = db.materias.find_one({"_id": ObjectId(uid)})
        if materia:
            materia['_id'] = str(materia['_id'])
            materia['institucion_id'] = str(materia['institucion_id']) if materia.get('institucion_id') else None
        return materia

    @staticmethod
    def update_materia(uid, data):
        db = get_mongo()
        update_data = {}
        if 'codigo' in data:
            update_data['codigo'] = data['codigo']
        if 'nombre' in data:
            update_data['nombre'] = data['nombre']
        if 'nivel' in data:
            update_data['nivel'] = data['nivel']
        db.materias.update_one({"_id": ObjectId(uid)}, {"$set": update_data})
        
        # Sync Neo4j
        with get_neo4j() as session:
            session.run("""
                MATCH (m:Materia {id_mongo: $id})
                SET m.codigo = $codigo, m.nombre = $nombre
            """, id=uid, codigo=data.get('codigo', ''), nombre=data.get('nombre', ''))
        return True

    @staticmethod
    def delete_materia(uid):
        db = get_mongo()
        db.materias.update_one({"_id": ObjectId(uid)}, {"$set": {"metadata.estado": "INACTIVA"}})
        return True

    @staticmethod
    def get_materias_by_estudiante(est_id):
        """Obtiene las materias de un estudiante desde Neo4j"""
        materias = []
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

    # CARRERAS (Mongo + Neo4j CONTIENE -> Materia)
    @staticmethod
    def create_carrera(data):
        """Crea entidad Carrera en Mongo y nodo en Neo4j."""
        db = get_mongo()
        doc = {
            "codigo": data.get("codigo", ""),
            "nombre": data["nombre"],
            "materias_ids": [], 
            "metadata": {"created_at": datetime.utcnow(), "estado": "VIGENTE"}
        }
        res = db.carreras.insert_one(doc)
        carrera_id = str(res.inserted_id)

        with get_neo4j() as session:
            session.run("""
                MERGE (c:Carrera {id_mongo: $id})
                SET c.codigo = $codigo, c.nombre = $nombre
            """, id=carrera_id, codigo=doc["codigo"], nombre=doc["nombre"])
        return carrera_id

    @staticmethod
    def get_carreras():
        db = get_mongo()
        data = list(db.carreras.find({"metadata.estado": "VIGENTE"}))
        for d in data:
            d["_id"] = str(d["_id"])
            d["materias_ids"] = [str(oid) for oid in d.get("materias_ids", [])]
        return data

    @staticmethod
    def get_carrera_by_id(uid):
        db = get_mongo()
        carrera = db.carreras.find_one({"_id": ObjectId(uid), "metadata.estado": "VIGENTE"})
        if carrera:
            carrera["_id"] = str(carrera["_id"])
            carrera["materias_ids"] = [str(oid) for oid in carrera.get("materias_ids", [])]
        return carrera

    @staticmethod
    def agregar_materia_a_carrera(carrera_id, materia_id):
        """Relaciona una materia a la carrera: (Carrera)-[:CONTIENE]->(Materia) en Neo4j y Mongo."""
        db = get_mongo()
        oid_materia = ObjectId(materia_id)
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

    @staticmethod
    def get_materias_de_carrera(carrera_id):
        """Materias que CONTIENE la carrera (desde Neo4j o Mongo)."""
        with get_neo4j() as session:
            result = session.run("""
                MATCH (c:Carrera {id_mongo: $carrera_id})-[:CONTIENE]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as nombre, m.codigo as codigo
            """, carrera_id=carrera_id)
            return [{"materia_id": r["materia_id"], "nombre": r["nombre"], "codigo": r["codigo"]} for r in result]

    @staticmethod
    def get_materias_faltantes_para_recibirse(est_id, carrera_id):
        """
        Compara lo que el alumno CURSÓ (APROBADO) vs lo que la carrera CONTIENE.
        Devuelve las materias que le faltan para recibirse.
        """
        with get_neo4j() as session:
            # Materias aprobadas del estudiante
            aprobadas = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(m:Materia)
                WHERE r.estado = 'APROBADO'
                RETURN m.id_mongo as materia_id
            """, est_id=est_id)
            ids_aprobadas = {r["materia_id"] for r in aprobadas}

            # Materias de la carrera
            de_carrera = session.run("""
                MATCH (c:Carrera {id_mongo: $carrera_id})-[:CONTIENE]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as nombre, m.codigo as codigo
            """, carrera_id=carrera_id)
            materias_carrera = list(de_carrera)

        faltantes = [
            {"materia_id": r["materia_id"], "nombre": r["nombre"], "codigo": r["codigo"]}
            for r in materias_carrera
            if r["materia_id"] not in ids_aprobadas
        ]
        return {
            "materias_faltantes": faltantes,
            "cantidad_faltantes": len(faltantes),
            "materias_aprobadas_de_carrera": len(ids_aprobadas & {r["materia_id"] for r in materias_carrera}),
            "total_materias_carrera": len(materias_carrera),
        }