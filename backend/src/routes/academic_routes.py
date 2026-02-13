from flask import Blueprint, request, jsonify
from src.services.academic_service import AcademicService

academic_bp = Blueprint('academic', __name__)

# Instituciones
@academic_bp.route('/instituciones', methods=['POST'])
def create_inst():
    uid = AcademicService.create_institucion(request.json)
    return jsonify({"id": uid}), 201

@academic_bp.route('/instituciones', methods=['GET'])
def get_inst():
    return jsonify(AcademicService.get_instituciones())

# Materias
@academic_bp.route('/materias', methods=['POST'])
def create_mat():
    uid = AcademicService.create_materia(request.json)
    return jsonify({"id": uid}), 201

@academic_bp.route('/materias', methods=['GET'])
def get_mat():
    return jsonify(AcademicService.get_materias())

# Instituciones - CRUD completo
@academic_bp.route('/instituciones/<uid>', methods=['GET'])
def get_inst_by_id(uid):
    inst = AcademicService.get_institucion_by_id(uid)
    if not inst:
        return jsonify({"error": "Institución no encontrada"}), 404
    return jsonify(inst)

@academic_bp.route('/instituciones/<uid>', methods=['PUT'])
def update_inst(uid):
    try:
        AcademicService.update_institucion(uid, request.json)
        return jsonify({"msg": "Actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@academic_bp.route('/instituciones/<uid>', methods=['DELETE'])
def delete_inst(uid):
    try:
        AcademicService.delete_institucion(uid)
        return jsonify({"msg": "Eliminado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Materias - CRUD completo
@academic_bp.route('/materias/<uid>', methods=['GET'])
def get_mat_by_id(uid):
    materia = AcademicService.get_materia_by_id(uid)
    if not materia:
        return jsonify({"error": "Materia no encontrada"}), 404
    return jsonify(materia)

@academic_bp.route('/materias/<uid>', methods=['PUT'])
def update_mat(uid):
    try:
        AcademicService.update_materia(uid, request.json)
        return jsonify({"msg": "Actualizado correctamente"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@academic_bp.route('/materias/<uid>', methods=['DELETE'])
def delete_mat(uid):
    try:
        AcademicService.delete_materia(uid)
        return jsonify({"msg": "Eliminado"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@academic_bp.route('/materias/estudiante/<est_id>', methods=['GET'])
def get_materias_by_estudiante(est_id):
    return jsonify(AcademicService.get_materias_by_estudiante(est_id))