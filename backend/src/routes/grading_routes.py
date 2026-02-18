from flask import Blueprint, request, jsonify
from src.services.grading_service import GradingService
from src.services.conversion_service import ConversionService

grading_bp = Blueprint('grading', __name__)

# --- CALIFICACIONES ---
@grading_bp.route('/', methods=['POST'])
def registrar():
    try:
        uid = GradingService.registrar_calificacion(request.json)
        return jsonify({"id": uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@grading_bp.route('/estudiante/<uid>', methods=['GET'])
def historial(uid):
    return jsonify(GradingService.get_historial_estudiante(uid))

# --- CONVERSIONES ---
@grading_bp.route('/reglas', methods=['GET'])
def list_rules():
    return jsonify(ConversionService.get_all_rules())

@grading_bp.route('/reglas', methods=['POST'])
def create_rule():
    uid = ConversionService.create_rule(request.json)
    return jsonify({"id": uid}), 201

@grading_bp.route('/reglas/<regla_id>', methods=['GET'])
def get_rule(regla_id):
    regla = ConversionService.get_rule_by_id(regla_id)
    if not regla:
        return jsonify({"error": "Regla no encontrada"}), 404
    return jsonify(regla)

@grading_bp.route('/reglas/<regla_id>', methods=['PUT'])
def update_rule(regla_id):
    """Actualiza una regla; guarda el estado anterior en Cassandra (historico_reglas)."""
    try:
        data = request.json or {}
        modificado_por = data.pop('modificado_por', None)
        ConversionService.update_rule(regla_id, data, modificado_por=modificado_por)
        return jsonify({"msg": "Regla actualizada"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@grading_bp.route('/convertir', methods=['POST'])
def aplicar():
    try:
        val = ConversionService.aplicar_conversion(request.json)
        return jsonify({"valor_convertido": val}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# CRUD completo de calificaciones
@grading_bp.route('/', methods=['GET'])
def get_all():
    return jsonify(GradingService.get_all())

@grading_bp.route('/<calif_id>', methods=['GET'])
def get_by_id(calif_id):
    calif = GradingService.get_by_id(calif_id)
    if not calif:
        return jsonify({"error": "Calificación no encontrada"}), 404
    return jsonify(calif)

@grading_bp.route('/<calif_id>', methods=['PUT'])
def update(calif_id):
    try:
        GradingService.update(calif_id, request.json)
        return jsonify({"msg": "Actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@grading_bp.route('/<calif_id>', methods=['DELETE'])
def delete(calif_id):
    try:
        GradingService.delete(calif_id)
        return jsonify({"msg": "Eliminado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoints adicionales de GradingService
@grading_bp.route('/inscribir', methods=['POST'])
def inscribir():
    try:
        data = request.json
        GradingService.inscribir_alumno(data['estudiante_id'], data['materia_id'], data.get('anio_lectivo', 2024))
        return jsonify({"msg": "Inscripción realizada"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@grading_bp.route('/cargar-nota', methods=['POST'])
def cargar_nota():
    try:
        data = request.json
        GradingService.cargar_nota(data['estudiante_id'], data['materia_id'], 
                                   data['tipo_nota'], data['valor'])
        return jsonify({"msg": "Nota cargada"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@grading_bp.route('/cerrar-cursada', methods=['POST'])
def cerrar_cursada():
    try:
        data = request.json
        GradingService.cerrar_cursada(data['estudiante_id'], data['materia_id'])
        return jsonify({"msg": "Cursada cerrada"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500