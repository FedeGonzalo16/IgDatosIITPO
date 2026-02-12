from flask import Blueprint, request, jsonify
from src.services.student_service import StudentService

student_bp = Blueprint('students', __name__)

# CREAR
@student_bp.route('/', methods=['POST'])
def create():
    try:
        uid = StudentService.create(request.json)
        return jsonify({"id": uid, "msg": "Creado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# OBTENER TODOS
@student_bp.route('/', methods=['GET'])
def get_all():
    return jsonify(StudentService.get_all())

# OBTENER POR ID
@student_bp.route('/<uid>', methods=['GET'])
def get_by_id(uid):
    student = StudentService.get_by_id(uid)
    if not student:
        return jsonify({"error": "Estudiante no encontrado"}), 404
    return jsonify(student)

# MODIFICAR
@student_bp.route('/<uid>', methods=['PUT'])
def update(uid):
    try:
        StudentService.update(uid, request.json)
        return jsonify({"msg": "Actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ELIMINAR
@student_bp.route('/<uid>', methods=['DELETE'])
def delete(uid):
    try:
        StudentService.delete(uid)
        return jsonify({"msg": "Eliminado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500