from src.config.database import get_cassandra

class AnalyticsService:
    @staticmethod
    def get_auditoria_estudiante(est_id):
        """
        Lee el historial de acciones de un alumno desde Cassandra.
        La tabla registro_auditoria está particionada por id_estudiante
        """
        session = get_cassandra()
        if not session:
            return []
        try:
            rows = session.execute("""
                SELECT id_auditoria, fecha_creacion, tipo_accion, nota_original
                FROM registro_auditoria WHERE id_estudiante = %s
            """, (est_id,))
            result = []
            for r in rows:
                fecha = r.fecha_creacion
                result.append({
                    "fecha":   fecha.isoformat() if hasattr(fecha, 'isoformat') else str(fecha),
                    "accion":  r.tipo_accion,
                    "detalle": r.nota_original
                })
            return result
        except Exception as e:
            print(f"[WARNING] Error al consultar auditoría en Cassandra: {e}")
            return []

    @staticmethod
    def get_reporte_geo(region):
        """
        Devuelve el promedio de notas por institución para una región dada.
        """
        session = get_cassandra()
        if not session:
            return []
        try:
            rows = session.execute("SELECT * FROM reportes_geograficos WHERE region=%s", (region,))
            return [{"inst": r.institucion_id, "promedio": r.acumulado_notas / (r.contador_notas or 1)} for r in rows]
        except Exception as e:
            print(f"[WARNING] Error al consultar reporte geo en Cassandra: {e}")
            return []
