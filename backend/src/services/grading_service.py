from src.config.database import get_neo4j, get_cassandra

class GradingService:
    
    @staticmethod
    def inscribir_alumno(est_id, mat_id, anio_lectivo):
        """Crea una NUEVA relación CURSANDO. No sobreescribe si recursa."""
        with get_neo4j() as session:
            session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})
                MATCH (m:Materia {id_mongo: $mat_id})
                // Usamos CREATE en lugar de MERGE para permitir recursadas múltiples
                CREATE (e)-[r:CURSANDO {
                    anio: $anio,
                    estado: 'EN_CURSO'
                }]->(m)
            """, est_id=est_id, mat_id=mat_id, anio=anio_lectivo)
        return True

    @staticmethod
    def cargar_nota(est_id, mat_id, tipo_nota, valor):
        """
        tipos permitidos: 'primer_parcial', 'segundo_parcial', 'final', 'previo'
        """
        # 1. Actualizar SOLO en Neo4j
        query = f"""
            MATCH (e:Estudiante {{id_mongo: $est_id}})-[r:CURSANDO]->(m:Materia {{id_mongo: $mat_id}})
            SET r.{tipo_nota} = $valor
            RETURN r
        """
        with get_neo4j() as session:
            session.run(query, est_id=est_id, mat_id=mat_id, valor=valor)

        # 2. Auditoría en Cassandra (Opcional pero recomendado para el TPO)
        session_cass = get_cassandra()
        if session_cass:
            session_cass.execute("""
                INSERT INTO registro_auditoria (id_estudiante, fecha_creacion, id_auditoria, tipo_accion, nota_original)
                VALUES (%s, toTimestamp(now()), uuid(), %s, %s)
            """, (est_id, f"CARGA_{tipo_nota.upper()}", str(valor)))
            
        return True

    @staticmethod
    def cerrar_cursada(est_id, mat_id):
        """
        Evalúa las notas. Si desaprobó el final y no tiene previo (o reprobó previo),
        cambia la relación de CURSANDO a CURSÓ con estado REPROBADO o APROBADO.
        """
        with get_neo4j() as session:
            # En Neo4j no se puede renombrar una relación. Se crea una nueva, se copian propiedades y se borra la vieja.
            session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO]->(m:Materia {id_mongo: $mat_id})
                
                // Lógica de aprobación: Necesita final >= 6 o previo >= 6
                WITH e, m, r, 
                     CASE 
                        WHEN r.final >= 6 THEN 'APROBADO'
                        WHEN r.previo >= 6 THEN 'APROBADO'
                        ELSE 'REPROBADO'
                     END as estado_final
                
                // Creamos la nueva relación histórica
                CREATE (e)-[r2:CURSÓ]->(m)
                
                // Copiamos todas las notas al historial
                SET r2 = properties(r),
                    r2.estado = estado_final,
                    r2.fecha_cierre = datetime()
                
                // Borramos la relación activa
                DELETE r
            """, est_id=est_id, mat_id=mat_id)
        return True