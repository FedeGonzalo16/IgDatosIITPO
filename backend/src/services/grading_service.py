from src.config.database import get_mongo, get_neo4j, get_cassandra
from bson import ObjectId
from datetime import datetime
import uuid

class GradingService:
    @staticmethod
    def registrar_calificacion(data):
        db = get_mongo()
        est_id = data['estudiante_id']
        mat_id = data['materia_id']
        nota_val = data['valor_original'] # Dict {nota: 9, tipo: FINAL}

        # 1. Mongo
        doc = {
            "estudiante_id": ObjectId(est_id),
            "materia_id": ObjectId(mat_id),
            "valor_original": nota_val,
            "fecha": datetime.utcnow(),
            "metadata": {"estado": "DEFINITIVA"}
        }
        res = db.calificaciones.insert_one(doc)
        calif_id = str(res.inserted_id)

        # 2. Neo4j: Nota en la relación
        try:
            with get_neo4j() as session:
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $est_id})
                    MATCH (m:Materia {id_mongo: $mat_id})
                    MERGE (e)-[r:CURSO]->(m)
                    SET r.nota = $nota, 
                        r.id_calificacion = $cid,
                        r.fecha = datetime()
                """, est_id=est_id, mat_id=mat_id, nota=nota_val.get('nota'), cid=calif_id)
        except Exception as e:
            print(f"[SYNC ERROR] Neo4j: {e}")

        # 3. Cassandra: Auditoría
        GradingService._audit_cassandra(est_id, "CALIFICACION_REGISTRADA", 
                                      str(nota_val.get('nota')), f"Materia {mat_id}")
        
        return calif_id

    @staticmethod
    def _audit_cassandra(est_id, accion, nota, desc):
        session = get_cassandra()
        if session:
            try:
                session.execute("""
                    INSERT INTO registro_auditoria 
                    (id_estudiante, fecha_creacion, id_auditoria, tipo_accion, nota_original, descripcion)
                    VALUES (%s, toTimestamp(now()), uuid(), %s, %s, %s)
                """, (est_id, accion, nota, desc))
            except Exception as e:
                print(f"[SYNC ERROR] Cassandra: {e}")

    @staticmethod
    def get_historial_estudiante(est_id):
        # Combina Mongo (detalle) + Neo4j (trayectoria visual)
        db = get_mongo()
        califs = list(db.calificaciones.find({"estudiante_id": ObjectId(est_id)}))
        for c in califs:
            c['_id'] = str(c['_id'])
            c['estudiante_id'] = str(c['estudiante_id'])
            c['materia_id'] = str(c['materia_id'])
        return califs