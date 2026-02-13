from flask import Blueprint, request, jsonify
from src.services.professor_service import ProfessorService

professor_bp = Blueprint('professors', __name__)

# CREAR
@professor_bp.route('/', methods=['POST'])
def create():
    try:
        uid = ProfessorService.create(request.json)
        return jsonify({"id": uid, "msg": "Creado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# OBTENER TODOS
@professor_bp.route('/', methods=['GET'])
def get_all():
    return jsonify(ProfessorService.get_all())

# OBTENER POR ID
@professor_bp.route('/<uid>', methods=['GET'])
def get_by_id(uid):
    prof = ProfessorService.get_by_id(uid)
    if not prof:
        return jsonify({"error": "Profesor no encontrado"}), 404
    return jsonify(prof)

# MODIFICAR
@professor_bp.route('/<uid>', methods=['PUT'])
def update(uid):
    try:
        ProfessorService.update(uid, request.json)
        return jsonify({"msg": "Actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ELIMINAR
@professor_bp.route('/<uid>', methods=['DELETE'])
def delete(uid):
    try:
        ProfessorService.delete(uid)
        return jsonify({"msg": "Eliminado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ASIGNAR MATERIA
@professor_bp.route('/<prof_id>/asignar-materia', methods=['POST'])
def asignar_materia(prof_id):
    try:
        data = request.json
        ProfessorService.asignar_materia(prof_id, data['materia_id'], data.get('activo', True))
        return jsonify({"msg": "Materia asignada"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

