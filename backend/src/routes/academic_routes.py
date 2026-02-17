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

# Carreras
@academic_bp.route('/carreras', methods=['POST'])
def create_carrera():
    uid = AcademicService.create_carrera(request.json)
    return jsonify({"id": uid}), 201

@academic_bp.route('/carreras', methods=['GET'])
def get_carreras():
    return jsonify(AcademicService.get_carreras())

@academic_bp.route('/carreras/<uid>', methods=['GET'])
def get_carrera_by_id(uid):
    carrera = AcademicService.get_carrera_by_id(uid)
    if not carrera:
        return jsonify({"error": "Carrera no encontrada"}), 404
    return jsonify(carrera)

@academic_bp.route('/carreras/<carrera_id>/materias/<materia_id>', methods=['POST'])
def agregar_materia_carrera(carrera_id, materia_id):
    try:
        AcademicService.agregar_materia_a_carrera(carrera_id, materia_id)
        return jsonify({"msg": "Materia agregada a la carrera"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@academic_bp.route('/carreras/<carrera_id>/materias', methods=['GET'])
def get_materias_carrera(carrera_id):
    return jsonify(AcademicService.get_materias_de_carrera(carrera_id))

@academic_bp.route('/carreras/<carrera_id>/faltantes/<est_id>', methods=['GET'])
def get_faltantes_recibirse(carrera_id, est_id):
    """Materias que le faltan al estudiante para recibirse en la carrera."""
    return jsonify(AcademicService.get_materias_faltantes_para_recibirse(est_id, carrera_id))