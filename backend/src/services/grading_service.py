from src.config.database import get_mongo, get_neo4j, get_cassandra
from bson import ObjectId
from datetime import datetime
import uuid

class GradingService:
    
    @staticmethod
    def inscribir_alumno(est_id, mat_id, anio_lectivo):
        """Crea una NUEVA relación CURSANDO. No sobreescribe si recursa."""
        print(f"[DEBUG inscribir_alumno] est_id={est_id}, mat_id={mat_id}, anio={anio_lectivo}")
        
        with get_neo4j() as session:
            # Primero verificar que existen los nodos
            estudiante_check = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})
                RETURN e
            """, est_id=est_id)
            
            if not list(estudiante_check):
                print(f"[ERROR] Estudiante {est_id} NO existe en Neo4j")
                raise Exception(f"Estudiante {est_id} no encontrado en el sistema")
            
            materia_check = session.run("""
                MATCH (m:Materia {id_mongo: $mat_id})
                RETURN m
            """, mat_id=mat_id)
            
            if not list(materia_check):
                print(f"[ERROR] Materia {mat_id} NO existe en Neo4j")
                raise Exception(f"Materia {mat_id} no encontrada en el sistema")
            
            print(f"[OK] Ambos nodos existen. Creando relación CURSANDO...")
            
            result = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})
                MATCH (m:Materia {id_mongo: $mat_id})
                // Usamos CREATE en lugar de MERGE para permitir recursadas múltiples
                CREATE (e)-[r:CURSANDO {
                    anio: $anio,
                    estado: 'EN_CURSO'
                }]->(m)
                RETURN r
            """, est_id=est_id, mat_id=mat_id, anio=anio_lectivo)
            
            rel = list(result)
            if rel:
                print(f"[OK] Relación CURSANDO creada exitosamente")
            else:
                print(f"[WARNING] Relación CURSANDO NO se creó")
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

    @staticmethod
    def registrar_calificacion(data):
        """Registra una calificación en MongoDB y sincroniza con Neo4j"""
        db = get_mongo()
        
        # Validar datos
        estudiante_id = data.get('estudiante_id')
        materia_id = data.get('materia_id')
        valor_original = data.get('valor_original', {})
        
        # Guardar en MongoDB
        doc = {
            "estudiante_id": ObjectId(estudiante_id),
            "materia_id": ObjectId(materia_id),
            "valor_original": valor_original,
            "conversiones_aplicadas": [],
            "created_at": datetime.utcnow()
        }
        res = db.calificaciones.insert_one(doc)
        calif_id = str(res.inserted_id)
        
        # Sincronizar con Neo4j si hay tipo de nota
        if 'tipo' in valor_original and 'nota' in valor_original:
            tipo_nota_map = {
                'PARCIAL_1': 'primer_parcial',
                'PARCIAL_2': 'segundo_parcial',
                'FINAL': 'final',
                'FINAL_PROJECT': 'final',
                'MIDTERM': 'primer_parcial',
                'PREVIO': 'previo'
            }
            tipo_nota = tipo_nota_map.get(valor_original['tipo'], 'final')
            nota_valor = valor_original['nota']
            
            # Convertir nota a número si es posible
            try:
                if isinstance(nota_valor, str):
                    # Mapeo básico de letras a números
                    nota_map = {'A': 10, 'B+': 8, 'B': 7, 'C+': 6, 'C': 5, 'D': 4, 'F': 2}
                    nota_valor = nota_map.get(nota_valor, float(nota_valor) if nota_valor.replace('.', '').isdigit() else 0)
                nota_valor = float(nota_valor)
            except:
                nota_valor = 0
            
            GradingService.cargar_nota(estudiante_id, materia_id, tipo_nota, nota_valor)
        
        return calif_id

    @staticmethod
    def get_historial_estudiante(est_id):
        """Obtiene el historial completo de un estudiante desde Neo4j"""
        historial = []
        
        with get_neo4j() as session:
            # Obtener materias en curso
            result = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSANDO]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as materia_nombre, 
                       m.codigo as materia_codigo, r.anio as anio, r.estado as estado,
                       r.primer_parcial as primer_parcial,
                       r.segundo_parcial as segundo_parcial,
                       r.final as final, r.previo as previo
                ORDER BY r.anio DESC
            """, est_id=est_id)
            
            for record in result:
                historial.append({
                    "materia_id": record["materia_id"],
                    "materia_nombre": record["materia_nombre"],
                    "materia_codigo": record["materia_codigo"],
                    "anio": record["anio"],
                    "estado": record["estado"],
                    "notas": {
                        "primer_parcial": record["primer_parcial"],
                        "segundo_parcial": record["segundo_parcial"],
                        "final": record["final"],
                        "previo": record["previo"]
                    }
                })
            
            # Obtener materias cursadas (histórico)
            result_historico = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(m:Materia)
                RETURN m.id_mongo as materia_id, m.nombre as materia_nombre,
                       m.codigo as materia_codigo, r.anio as anio, r.estado as estado,
                       r.primer_parcial as primer_parcial,
                       r.segundo_parcial as segundo_parcial,
                       r.final as final, r.previo as previo,
                       r.fecha_cierre as fecha_cierre
                ORDER BY r.fecha_cierre DESC
            """, est_id=est_id)
            
            for record in result_historico:
                historial.append({
                    "materia_id": record["materia_id"],
                    "materia_nombre": record["materia_nombre"],
                    "materia_codigo": record["materia_codigo"],
                    "anio": record["anio"],
                    "estado": record["estado"],
                    "fecha_cierre": str(record["fecha_cierre"]) if record["fecha_cierre"] else None,
                    "notas": {
                        "primer_parcial": record["primer_parcial"],
                        "segundo_parcial": record["segundo_parcial"],
                        "final": record["final"],
                        "previo": record["previo"]
                    }
                })
        
        return historial

    @staticmethod
    def get_all():
        """Obtiene todas las calificaciones desde MongoDB"""
        db = get_mongo()
        calificaciones = list(db.calificaciones.find().sort("created_at", -1).limit(100))
        for c in calificaciones:
            c['_id'] = str(c['_id'])
            c['estudiante_id'] = str(c['estudiante_id'])
            c['materia_id'] = str(c['materia_id'])
        return calificaciones

    @staticmethod
    def get_by_id(calif_id):
        """Obtiene una calificación por ID"""
        db = get_mongo()
        calif = db.calificaciones.find_one({"_id": ObjectId(calif_id)})
        if calif:
            calif['_id'] = str(calif['_id'])
            calif['estudiante_id'] = str(calif['estudiante_id'])
            calif['materia_id'] = str(calif['materia_id'])
        return calif

    @staticmethod
    def update(calif_id, data):
        """Actualiza una calificación"""
        db = get_mongo()
        update_data = {}
        if 'valor_original' in data:
            update_data['valor_original'] = data['valor_original']
        db.calificaciones.update_one({"_id": ObjectId(calif_id)}, {"$set": update_data})
        return True

    @staticmethod
    def delete(calif_id):
        """Elimina una calificación (soft delete)"""
        db = get_mongo()
        db.calificaciones.update_one({"_id": ObjectId(calif_id)}, {"$set": {"estado": "ELIMINADA"}})
        return True