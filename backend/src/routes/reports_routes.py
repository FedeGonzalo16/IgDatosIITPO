from flask import Blueprint, request, jsonify
from src.services.analytics_service import AnalyticsService

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/auditoria/<est_id>', methods=['GET'])
def auditoria(est_id):
    return jsonify(AnalyticsService.get_auditoria_estudiante(est_id))

@reports_bp.route('/region/<region>', methods=['GET'])
def regional(region):
    return jsonify(AnalyticsService.get_reporte_geo(region))