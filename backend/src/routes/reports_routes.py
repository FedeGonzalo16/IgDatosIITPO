from flask import Blueprint, request, jsonify
from src.services.analytics_service import AnalyticsService
from src.config.database import get_mongo, get_neo4j
from bson import ObjectId

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/auditoria/<est_id>', methods=['GET'])
def auditoria(est_id):
    return jsonify(AnalyticsService.get_auditoria_estudiante(est_id))

@reports_bp.route('/region/<region>', methods=['GET'])
def regional(region):
    return jsonify(AnalyticsService.get_reporte_geo(region))

@reports_bp.route('/estudiante/<est_id>', methods=['GET'])
def estudiante_report(est_id):
    """Reporte completo de un estudiante"""
    db = get_mongo()
    
    # Datos del estudiante
    estudiante = db.estudiantes.find_one({"_id": ObjectId(est_id)})
    if not estudiante:
        return jsonify({"error": "Estudiante no encontrado"}), 404
    
    estudiante['_id'] = str(estudiante['_id'])
    
    # Calificaciones
    calificaciones = list(db.calificaciones.find({"estudiante_id": ObjectId(est_id)}))
    for c in calificaciones:
        c['_id'] = str(c['_id'])
        c['estudiante_id'] = str(c['estudiante_id'])
        c['materia_id'] = str(c['materia_id'])
    
    # Estadísticas desde Neo4j
    stats = {
        "materias_en_curso": 0,
        "materias_aprobadas": 0,
        "materias_reprobadas": 0,
        "promedio_general": 0
    }
    
    with get_neo4j() as session:
        result = session.run("""
            MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO|CURSÓ]->(m:Materia)
            RETURN type(r) as tipo, r.estado as estado, r.final as final
        """, est_id=est_id)
        
        notas_finales = []
        for record in result:
            if record["tipo"] == "CURSANDO":
                stats["materias_en_curso"] += 1
            elif record["estado"] == "APROBADO":
                stats["materias_aprobadas"] += 1
                if record["final"]:
                    notas_finales.append(float(record["final"]))
            elif record["estado"] == "REPROBADO":
                stats["materias_reprobadas"] += 1
        
        if notas_finales:
            stats["promedio_general"] = sum(notas_finales) / len(notas_finales)
    
    return jsonify({
        "estudiante": estudiante,
        "calificaciones": calificaciones,
        "estadisticas": stats,
        "auditoria": AnalyticsService.get_auditoria_estudiante(est_id)
    })

@reports_bp.route('/institucion/<inst_id>', methods=['GET'])
def institucion_report(inst_id):
    """Reporte de una institución"""
    db = get_mongo()
    
    institucion = db.instituciones.find_one({"_id": ObjectId(inst_id)})
    if not institucion:
        return jsonify({"error": "Institución no encontrada"}), 404
    
    institucion['_id'] = str(institucion['_id'])
    
    # Materias de la institución
    materias = list(db.materias.find({"institucion_id": ObjectId(inst_id)}))
    for m in materias:
        m['_id'] = str(m['_id'])
        m['institucion_id'] = str(m['institucion_id'])
    
    # Estadísticas desde Neo4j
    stats = {
        "total_estudiantes": 0,
        "total_materias": len(materias),
        "materias_activas": 0
    }
    
    with get_neo4j() as session:
        result = session.run("""
            MATCH (i:Institucion {id_mongo: $inst_id})<-[:PERTENECE_A]-(m:Materia)
            OPTIONAL MATCH (e:Estudiante)-[:CURSANDO|CURSÓ]->(m)
            RETURN count(DISTINCT e) as total_estudiantes, count(DISTINCT m) as materias_activas
        """, inst_id=inst_id)
        
        record = result.single()
        if record:
            stats["total_estudiantes"] = record["total_estudiantes"] or 0
            stats["materias_activas"] = record["materias_activas"] or 0
    
    return jsonify({
        "institucion": institucion,
        "materias": materias,
        "estadisticas": stats
    })

@reports_bp.route('/calificaciones', methods=['GET'])
def calificaciones_stats():
    """Estadísticas generales de calificaciones"""
    db = get_mongo()
    
    # Parámetros de filtro
    materia_id = request.args.get('materia_id')
    estudiante_id = request.args.get('estudiante_id')
    
    query = {}
    if materia_id:
        query['materia_id'] = ObjectId(materia_id)
    if estudiante_id:
        query['estudiante_id'] = ObjectId(estudiante_id)
    
    calificaciones = list(db.calificaciones.find(query))
    
    # Calcular estadísticas
    notas = []
    for c in calificaciones:
        if 'valor_original' in c and 'nota' in c['valor_original']:
            try:
                nota = float(c['valor_original']['nota'])
                notas.append(nota)
            except:
                pass
    
    stats = {
        "total": len(calificaciones),
        "promedio": sum(notas) / len(notas) if notas else 0,
        "minima": min(notas) if notas else 0,
        "maxima": max(notas) if notas else 0,
        "aprobados": len([n for n in notas if n >= 6]),
        "reprobados": len([n for n in notas if n < 6])
    }
    
    return jsonify(stats)

@reports_bp.route('/aprobacion', methods=['GET'])
def aprobacion_stats():
    """Estadísticas de aprobación"""
    stats = {
        "tasa_aprobacion": 0,
        "total_cursadas": 0,
        "aprobadas": 0,
        "reprobadas": 0
    }
    
    with get_neo4j() as session:
        result = session.run("""
            MATCH (e:Estudiante)-[r:CURSÓ]->(m:Materia)
            RETURN r.estado as estado, count(r) as cantidad
        """)
        
        for record in result:
            stats["total_cursadas"] += record["cantidad"]
            if record["estado"] == "APROBADO":
                stats["aprobadas"] += record["cantidad"]
            else:
                stats["reprobadas"] += record["cantidad"]
        
        if stats["total_cursadas"] > 0:
            stats["tasa_aprobacion"] = (stats["aprobadas"] / stats["total_cursadas"]) * 100
    
    return jsonify(stats)