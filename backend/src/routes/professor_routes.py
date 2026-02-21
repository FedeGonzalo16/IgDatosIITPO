from flask import Blueprint, request, jsonify
from src.services.professor_service import ProfessorService

professor_bp = Blueprint('professors', __name__)

@professor_bp.route('/', methods=['POST'])
def create():
    try:
        uid = ProfessorService.create(request.json)
        return jsonify({"id": uid, "msg": "Creado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@professor_bp.route('/', methods=['GET'])
def get_all():
    return jsonify(ProfessorService.get_all())

@professor_bp.route('/<uid>', methods=['GET'])
def get_by_id(uid):
    prof = ProfessorService.get_by_id(uid)
    if not prof:
        return jsonify({"error": "Profesor no encontrado"}), 404
    return jsonify(prof)

# OBTENER POR EMAIL
@professor_bp.route('/email/<email>', methods=['GET'])
def get_by_email(email):
    prof = ProfessorService.get_by_email(email)
    if not prof:
        return jsonify({"error": "Profesor no encontrado"}), 404
    return jsonify(prof)

@professor_bp.route('/<uid>', methods=['PUT'])
def update(uid):
    try:
        ProfessorService.update(uid, request.json)
        return jsonify({"msg": "Actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@professor_bp.route('/<uid>', methods=['DELETE'])
def delete(uid):
    try:
        ProfessorService.delete(uid)
        return jsonify({"msg": "Eliminado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@professor_bp.route('/<prof_id>/asignar-materia', methods=['POST'])
def asignar_materia(prof_id):
    try:
        data = request.json
        ProfessorService.asignar_materia(prof_id, data['materia_id'], data.get('activo', True))
        return jsonify({"msg": "Materia asignada"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === NUEVAS RUTAS PARA EL DASHBOARD ===

@professor_bp.route('/<prof_id>/materias', methods=['GET'])
def get_materias(prof_id):
    try:
        materias = ProfessorService.get_materias_by_profesor(prof_id)
        return jsonify(materias), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@professor_bp.route('/materia/<mat_id>/alumnos', methods=['GET'])
def get_alumnos_cursando(mat_id):
    try:
        alumnos = ProfessorService.get_alumnos_by_materia(mat_id)
        return jsonify(alumnos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500