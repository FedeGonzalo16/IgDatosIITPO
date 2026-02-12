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
@grading_bp.route('/reglas', methods=['POST'])
def create_rule():
    uid = ConversionService.create_rule(request.json)
    return jsonify({"id": uid}), 201

@grading_bp.route('/convertir', methods=['POST'])
def aplicar():
    try:
        val = ConversionService.aplicar_conversion(request.json)
        return jsonify({"valor_convertido": val}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400