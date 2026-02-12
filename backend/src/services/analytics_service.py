from src.config.database import get_cassandra

class AnalyticsService:
    @staticmethod
    def get_auditoria_estudiante(est_id):
        session = get_cassandra()
        if not session: return []
        
        rows = session.execute("""
            SELECT id_auditoria, fecha_creacion, tipo_accion, descripcion 
            FROM registro_auditoria WHERE id_estudiante = %s
        """, (est_id,))
        
        return [{"fecha": r.fecha_creacion, "accion": r.tipo_accion, "desc": r.descripcion} for r in rows]

    @staticmethod
    def get_reporte_geo(region):
        session = get_cassandra()
        if not session: return []
        
        rows = session.execute("SELECT * FROM reportes_geograficos WHERE region=%s", (region,))
        return [{"inst": r.institucion_id, "promedio": r.acumulado_notas/(r.contador_notas or 1)} for r in rows]