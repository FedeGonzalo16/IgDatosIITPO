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