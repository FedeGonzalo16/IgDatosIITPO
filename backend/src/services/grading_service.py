from src.config.database import get_mongo, get_neo4j, get_cassandra
from bson import ObjectId
from datetime import datetime
import uuid

class GradingService:
    
    @staticmethod
    def inscribir_alumno(est_id, mat_id, anio_lectivo):
        """
        Crea la relación CURSANDO en el grafo. Usamos CREATE (no MERGE) a propósito:
        si un alumno recursa la misma materia, debe existir una nueva arista independiente.
        """
        with get_neo4j() as session:
            session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})
                MATCH (m:Materia {id_mongo: $mat_id})
                CREATE (e)-[r:CURSANDO {
                    anio: $anio,
                    estado: 'CURSANDO'
                }]->(m)
            """, est_id=est_id, mat_id=mat_id, anio=anio_lectivo)
        return True

    @staticmethod
    def cargar_nota(est_id, mat_id, tipo_nota, valor):
        """
        Actualiza una propiedad específica de la relación CURSANDO o CURSÓ.
        tipos permitidos: 'primer_parcial', 'segundo_parcial', 'final', 'previo'
        Las notas viven en la arista del grafo, no en un documento separado.
        """
        query = f"""
            MATCH (e:Estudiante {{id_mongo: $est_id}})-[r:CURSANDO|CURSÓ]->(m:Materia {{id_mongo: $mat_id}})
            SET r.{tipo_nota} = $valor
            RETURN r
        """
        with get_neo4j() as session:
            session.run(query, est_id=est_id, mat_id=mat_id, valor=valor)

        session_cass = get_cassandra()
        if session_cass:
            session_cass.execute("""
                INSERT INTO registro_auditoria (id_estudiante, fecha_creacion, id_auditoria, tipo_accion, nota_original)
                VALUES (%s, toTimestamp(now()), uuid(), %s, %s)
            """, (est_id, f"CARGA_{tipo_nota.upper()}", str(valor)))
            
        return True

    @staticmethod
    def cerrar_cursada(est_id, mat_id):
        """
        Evalúa las notas acumuladas y convierte CURSANDO → CURSÓ con el estado final.
        La lógica de aprobación: final >= 4 OR previo >= 4. Todo en una sola query Cypher
        para evitar race conditions entre la lectura y la escritura.
        """
        with get_neo4j() as session:
            session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO]->(m:Materia {id_mongo: $mat_id})
                
                WITH e, m, r, 
                     CASE 
                        WHEN r.final >= 4 THEN 'APROBADO'
                        WHEN r.previo >= 4 THEN 'APROBADO'
                        ELSE 'REPROBADO'
                     END as estado_final
                
                CREATE (e)-[r2:CURSÓ]->(m)
                SET r2 = properties(r),
                    r2.estado = estado_final,
                    r2.fecha_cierre = datetime()
                
                DELETE r
            """, est_id=est_id, mat_id=mat_id)
        return True

    @staticmethod
    def registrar_calificacion(data):
        """
        Registra la nota en MongoDB (para consultas y conversiones futuras)
        y la sincroniza en el grafo Neo4j para que el historial de trayectoria quede actualizado.
        """
        db = get_mongo()
        
        estudiante_id = data.get('estudiante_id')
        materia_id    = data.get('materia_id')
        valor_original = data.get('valor_original', {})
        
        doc = {
            "estudiante_id": ObjectId(estudiante_id),
            "materia_id":    ObjectId(materia_id),
            "valor_original": valor_original,
            "conversiones_aplicadas": [],  # Array append-only para futuras conversiones
            "created_at": datetime.utcnow()
        }
        res = db.calificaciones.insert_one(doc)
        calif_id = str(res.inserted_id)
        
        if 'tipo' in valor_original and 'nota' in valor_original:
            tipo_nota_map = {
                'PARCIAL_1': 'primer_parcial',
                'PARCIAL_2': 'segundo_parcial',
                'FINAL': 'final',
                'FINAL_PROJECT': 'final',
                'MIDTERM': 'primer_parcial',
                'PREVIO': 'previo'
            }
            tipo_nota  = tipo_nota_map.get(valor_original['tipo'], 'final')
            nota_valor = valor_original['nota']
            
            # Normalización: si la nota viene como letra (A, B+, etc.), la convertimos a número
            try:
                if isinstance(nota_valor, str):
                    nota_map = {'A': 10, 'B+': 8, 'B': 7, 'C+': 6, 'C': 5, 'D': 4, 'F': 2}
                    nota_valor = nota_map.get(nota_valor, float(nota_valor) if nota_valor.replace('.', '').isdigit() else 0)
                nota_valor = float(nota_valor)
            except:
                nota_valor = 0
            
            GradingService.cargar_nota(estudiante_id, materia_id, tipo_nota, nota_valor)
        
        return calif_id

    @staticmethod
    def get_historial_estudiante(est_id):
        """
        Trayectoria completa desde Neo4j: materias en curso (CURSANDO) e históricas (CURSÓ),
        incluyendo datos de equivalencias para los traslados entre instituciones.
        """
        historial = []
        
        with get_neo4j() as session:
            result = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as materia_nombre, 
                       m.codigo as materia_codigo, r.anio as anio, r.estado as estado,
                       r.primer_parcial as primer_parcial,
                       r.segundo_parcial as segundo_parcial,
                       r.final as final, r.previo as previo
                ORDER BY r.anio DESC
            """, est_id=est_id)
            
            for record in result:
                historial.append({
                    "materia_id":     record["materia_id"],
                    "materia_nombre": record["materia_nombre"],
                    "materia_codigo": record["materia_codigo"],
                    "anio":           record["anio"],
                    "estado":         record["estado"],
                    "notas": {
                        "primer_parcial":  record["primer_parcial"],
                        "segundo_parcial": record["segundo_parcial"],
                        "final":           record["final"],
                        "previo":          record["previo"]
                    }
                })
            
            result_historico = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as materia_nombre,
                       m.codigo as materia_codigo, r.anio as anio, r.estado as estado,
                       r.primer_parcial as primer_parcial,
                       r.segundo_parcial as segundo_parcial,
                       r.final as final, r.previo as previo,
                       r.fecha_cierre as fecha_cierre,
                       r.nota_original as nota_original, r.metodo_conversion as metodo_conversion,
                       r.materia_origen_id as materia_origen_id, r.materia_origen_nombre as materia_origen_nombre,
                       r.fecha_conversion as fecha_conversion
                ORDER BY r.fecha_cierre DESC
            """, est_id=est_id)
            
            for record in result_historico:
                historial.append({
                    "materia_id":             record["materia_id"],
                    "materia_nombre":         record["materia_nombre"],
                    "materia_codigo":         record["materia_codigo"],
                    "anio":                   record["anio"],
                    "estado":                 record["estado"],
                    "fecha_cierre":           str(record["fecha_cierre"]) if record["fecha_cierre"] else None,
                    "es_equivalencia":        record["estado"] == "APROBADO (EQUIVALENCIA)" if record["estado"] else False,
                    "nota_original":          record["nota_original"],
                    "metodo_conversion":      record["metodo_conversion"],
                    "materia_origen_nombre":  record["materia_origen_nombre"],
                    "fecha_conversion":       str(record["fecha_conversion"]) if record["fecha_conversion"] else None,
                    "notas": {
                        "primer_parcial":  record["primer_parcial"],
                        "segundo_parcial": record["segundo_parcial"],
                        "final":           record["final"],
                        "previo":          record["previo"]
                    }
                })
        
        return historial

    @staticmethod
    def get_all():
        db = get_mongo()
        calificaciones = list(db.calificaciones.find().sort("created_at", -1).limit(100))
        for c in calificaciones:
            c['_id']           = str(c['_id'])
            c['estudiante_id'] = str(c['estudiante_id'])
            c['materia_id']    = str(c['materia_id'])
        return calificaciones

    @staticmethod
    def get_by_id(calif_id):
        db = get_mongo()
        calif = db.calificaciones.find_one({"_id": ObjectId(calif_id)})
        if calif:
            calif['_id']           = str(calif['_id'])
            calif['estudiante_id'] = str(calif['estudiante_id'])
            calif['materia_id']    = str(calif['materia_id'])
        return calif

    @staticmethod
    def update(calif_id, data):
        db = get_mongo()
        update_data = {}
        if 'valor_original' in data:
            update_data['valor_original'] = data['valor_original']
        db.calificaciones.update_one({"_id": ObjectId(calif_id)}, {"$set": update_data})
        return True

    @staticmethod
    def delete(calif_id):
        db = get_mongo()
        db.calificaciones.update_one({"_id": ObjectId(calif_id)}, {"$set": {"estado": "ELIMINADA"}})
        return True
