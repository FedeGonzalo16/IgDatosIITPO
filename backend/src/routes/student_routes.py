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

# OBTENER POR EMAIL
@student_bp.route('/email/<email>', methods=['GET'])
def get_by_email(email):
    student = StudentService.get_by_email(email)
    if not student:
        return jsonify({"error": "Estudiante no encontrado"}), 404
    return jsonify(student)


@student_bp.route('/<id>/cambiar-institucion', methods=['POST'])
def cambiar_institucion(id):
    """
    Endpoint para cambiar de institución y homologar materias.
    Body esperado:
    {
        "nueva_institucion_id": "60d5ec49c...",
        "regla_conversion_codigo": "AR_TO_US"
    }
    """
    data = request.json or {}
    nueva_institucion_id = data.get('nueva_institucion_id')
    regla_conversion_codigo = data.get('regla_conversion_codigo') or 'AR_TO_US'
    
    if not nueva_institucion_id:
        return jsonify({"error": "Falta el parámetro 'nueva_institucion_id'"}), 400
        
    try:
        resultado = StudentService.cambiar_institucion(id, nueva_institucion_id, regla_conversion_codigo)
        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500