from flask import Blueprint, jsonify
from src.config.database import get_neo4j

trajectory_bp = Blueprint('trajectory', __name__)

@trajectory_bp.route('/estudiante/<est_id>', methods=['GET'])
def get_student_trajectory(est_id):
    """Obtiene la trayectoria completa de un estudiante"""
    trayectoria = {
        "estudiante_id": est_id,
        "materias_en_curso": [],
        "materias_aprobadas": [],
        "materias_reprobadas": [],
        "recursadas": []
    }
    
    with get_neo4j() as session:
        # Materias en curso
        result = session.run("""
            MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO]->(m:Materia)
            RETURN m.id_mongo as materia_id, m.nombre as nombre, m.codigo as codigo,
                   r.anio as anio, r.primer_parcial as p1, r.segundo_parcial as p2,
                   r.final as final, r.previo as previo
            ORDER BY r.anio DESC
        """, est_id=est_id)
        
        for record in result:
            trayectoria["materias_en_curso"].append({
                "materia_id": record["materia_id"],
                "nombre": record["nombre"],
                "codigo": record["codigo"],
                "anio": record["anio"],
                "notas": {
                    "primer_parcial": record["p1"],
                    "segundo_parcial": record["p2"],
                    "final": record["final"],
                    "previo": record["previo"]
                }
            })
        
        # Materias aprobadas/reprobadas (incluye APROBADO y APROBADO (EQUIVALENCIA))
        result_historico = session.run("""
            MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(m:Materia)
            RETURN m.id_mongo as materia_id, m.nombre as nombre, m.codigo as codigo,
                   r.estado as estado, r.anio as anio, r.fecha_cierre as fecha_cierre,
                   r.primer_parcial as p1, r.segundo_parcial as p2,
                   r.final as final, r.previo as previo,
                   r.nota_original as nota_original, r.metodo_conversion as metodo_conversion,
                   r.materia_origen_nombre as materia_origen_nombre,
                   r.fecha_conversion as fecha_conversion
            ORDER BY r.fecha_cierre DESC
        """, est_id=est_id)
        
        for record in result_historico:
            nota_final = record["final"] if record["final"] is not None else record["previo"]
            materia_data = {
                "materia_id": record["materia_id"],
                "nombre": record["nombre"],
                "codigo": record["codigo"],
                "anio": record["anio"],
                "fecha_cierre": str(record["fecha_cierre"]) if record["fecha_cierre"] else None,
                "nota_final": nota_final,
                "es_equivalencia": record["estado"] == "APROBADO (EQUIVALENCIA)" if record["estado"] else False,
                "nota_original": record["nota_original"],
                "metodo_conversion": record["metodo_conversion"],
                "materia_origen_nombre": record["materia_origen_nombre"],
                "fecha_conversion": str(record["fecha_conversion"]) if record["fecha_conversion"] else None,
                "notas": {
                    "primer_parcial": record["p1"],
                    "segundo_parcial": record["p2"],
                    "final": record["final"],
                    "previo": record["previo"]
                }
            }
            
            estado = record["estado"] or ""
            if estado == "APROBADO" or estado == "APROBADO (EQUIVALENCIA)":
                trayectoria["materias_aprobadas"].append(materia_data)
            else:
                trayectoria["materias_reprobadas"].append(materia_data)
        
        # Detectar recursadas (misma materia múltiples veces)
        result_recursadas = session.run("""
            MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ|CURSANDO]->(m:Materia)
            WITH m.codigo as codigo, m.nombre as nombre, count(r) as veces
            WHERE veces > 1
            RETURN codigo, nombre, veces
        """, est_id=est_id)
        
        for record in result_recursadas:
            trayectoria["recursadas"].append({
                "codigo": record["codigo"],
                "nombre": record["nombre"],
                "veces": record["veces"]
            })
    
    return jsonify(trayectoria)

@trajectory_bp.route('/materia/<mat_id>', methods=['GET'])
def get_subject_trajectory(mat_id):
    """Obtiene la trayectoria de una materia (todos los estudiantes que la cursaron)"""
    trayectoria = {
        "materia_id": mat_id,
        "estudiantes_en_curso": [],
        "estudiantes_aprobados": [],
        "estudiantes_reprobados": []
    }
    
    with get_neo4j() as session:
        # Estudiantes en curso
        result = session.run("""
            MATCH (e:Estudiante)-[r:CURSANDO]->(m:Materia {id_mongo: $mat_id})
            RETURN e.id_mongo as estudiante_id, e.nombre as nombre,
                   r.anio as anio, r.primer_parcial as p1, r.segundo_parcial as p2,
                   r.final as final
        """, mat_id=mat_id)
        
        for record in result:
            trayectoria["estudiantes_en_curso"].append({
                "estudiante_id": record["estudiante_id"],
                "nombre": record["nombre"],
                "anio": record["anio"],
                "notas": {
                    "primer_parcial": record["p1"],
                    "segundo_parcial": record["p2"],
                    "final": record["final"]
                }
            })
        
        # Estudiantes aprobados/reprobados
        result_historico = session.run("""
            MATCH (e:Estudiante)-[r:CURSÓ]->(m:Materia {id_mongo: $mat_id})
            RETURN e.id_mongo as estudiante_id, e.nombre as nombre,
                   r.estado as estado, r.anio as anio, r.fecha_cierre as fecha_cierre,
                   r.final as final
            ORDER BY r.fecha_cierre DESC
        """, mat_id=mat_id)
        
        for record in result_historico:
            estudiante_data = {
                "estudiante_id": record["estudiante_id"],
                "nombre": record["nombre"],
                "anio": record["anio"],
                "fecha_cierre": str(record["fecha_cierre"]) if record["fecha_cierre"] else None,
                "nota_final": record["final"]
            }
            
            if record["estado"] == "APROBADO":
                trayectoria["estudiantes_aprobados"].append(estudiante_data)
            else:
                trayectoria["estudiantes_reprobados"].append(estudiante_data)
    
    return jsonify(trayectoria)

