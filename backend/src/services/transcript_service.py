"""
Servicio de Certificado Analítico (Reporte Integral).
Combina datos del alumno (Mongo), materias aprobadas (Neo4j CURSÓ),
calcula promedio histórico y % de avance. Opcional: snapshot en Cassandra.
"""
from src.config.database import get_mongo, get_neo4j, get_cassandra
from bson import ObjectId
from datetime import datetime
import json
import uuid


class TranscriptService:
    @staticmethod
    def generar_certificado_analitico(estudiante_id, carrera_nombre=None, guardar_snapshot=True):
        """
        Genera el certificado analítico (reporte integral) de un estudiante.
        - Datos personales desde Mongo
        - Materias aprobadas desde Neo4j (relación CURSÓ con estado APROBADO)
        - Promedio histórico y % de avance
        - Opcional: guarda snapshot en Cassandra como documento oficial emitido
        """
        db = get_mongo()

        # 1. Datos del alumno en Mongo
        estudiante = db.estudiantes.find_one({"_id": ObjectId(estudiante_id)})
        if not estudiante:
            raise ValueError("Estudiante no encontrado")
        estudiante["_id"] = str(estudiante["_id"])

        # 2. En Neo4j: todas las relaciones CURSÓ donde estado = 'APROBADO'
        materias_aprobadas = []
        notas_para_promedio = []

        with get_neo4j() as session:
            result = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(m:Materia)
                WHERE r.estado = 'APROBADO'
                RETURN m.id_mongo as materia_id, m.nombre as materia_nombre,
                       m.codigo as materia_codigo, r.anio as anio,
                       r.final as nota_final, r.fecha_cierre as fecha_cierre
                ORDER BY r.fecha_cierre ASC
            """, est_id=estudiante_id)

            for record in result:
                nota = record["nota_final"]
                # Normalizar nota a número para el promedio (puede ser letra en algunas escalas)
                try:
                    nota_num = float(nota) if nota is not None else None
                except (TypeError, ValueError):
                    nota_num = None
                if nota_num is not None:
                    notas_para_promedio.append(nota_num)

                materias_aprobadas.append({
                    "materia_id": record["materia_id"],
                    "nombre": record["materia_nombre"],
                    "codigo": record["materia_codigo"],
                    "anio": record["anio"],
                    "nota_final": nota,
                    "fecha_cierre": str(record["fecha_cierre"]) if record["fecha_cierre"] else None,
                })

        #Calcular Promedio Histórico
        promedio_historico = None
        if notas_para_promedio:
            promedio_historico = round(sum(notas_para_promedio) / len(notas_para_promedio), 2)

        #Porcentaje de avance de la carrera (si hay carrera y total de materias)
        total_materias_carrera = None
        porcentaje_avance = None
        if carrera_nombre:
            carrera = db.carreras.find_one({"nombre": carrera_nombre, "metadata.estado": "VIGENTE"})
            if carrera:
                total_materias_carrera = len(carrera.get("materias_ids", []))
                if total_materias_carrera and total_materias_carrera > 0:
                    # Materias aprobadas que pertenecen a la carrera (por id)
                    materias_carrera_ids = {str(oid) for oid in carrera.get("materias_ids", [])}
                    aprobadas_de_carrera = sum(
                        1 for m in materias_aprobadas
                        if m.get("materia_id") in materias_carrera_ids
                    )
                    porcentaje_avance = round(
                        (aprobadas_de_carrera / total_materias_carrera) * 100, 2
                    )

        certificado = {
            "estudiante": {
                "id": estudiante_id,
                "legajo": estudiante.get("legajo"),
                "nombre": estudiante.get("nombre"),
                "apellido": estudiante.get("apellido"),
                "email": estudiante.get("email"),
            },
            "carrera_nombre": carrera_nombre,
            "materias_aprobadas": materias_aprobadas,
            "cantidad_aprobadas": len(materias_aprobadas),
            "promedio_historico": promedio_historico,
            "total_materias_carrera": total_materias_carrera,
            "porcentaje_avance": porcentaje_avance,
            "fecha_emision": datetime.utcnow().isoformat(),
        }

        #Guardar snapshot en Cassandra como documento oficial emitido
        if guardar_snapshot:
            session_cass = get_cassandra()
            if session_cass:
                try:
                    id_cert = uuid.uuid4()
                    snapshot_json = json.dumps(certificado, default=str)
                    session_cass.execute("""
                        INSERT INTO certificados_emitidos
                        (id_estudiante, id_certificado, fecha_emision, tipo, carrera_nombre, snapshot)
                        VALUES (%s, %s, toTimestamp(now()), %s, %s, %s)
                    """, (estudiante_id, id_cert, "certificado_analitico", carrera_nombre or "", snapshot_json))
                    certificado["id_certificado_emitido"] = str(id_cert)
                except Exception as e:
                    print(f"[WARNING] No se pudo guardar snapshot en Cassandra: {e}")

        return certificado
