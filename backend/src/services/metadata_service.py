from src.config.database import get_cassandra

class MetadataService:
    @staticmethod
    def save_metadata(entity_type, entity_id, estado="ACTIVO"):
        """
        Registra el estado de cualquier entidad (estudiante, profesor) en Cassandra.
        Se usa en create/delete para dejar un rastro de auditoría
        """
        session = get_cassandra()
        if session:
            try:
                session.execute("""
                    INSERT INTO entity_metadata (entity_type, entity_id, estado, created_at, updated_at)
                    VALUES (%s, %s, %s, toTimestamp(now()), toTimestamp(now()))
                """, (entity_type, str(entity_id), estado))
            except Exception as e:
                print(f"[CASSANDRA ERROR] Falló al guardar metadatos: {e}")
