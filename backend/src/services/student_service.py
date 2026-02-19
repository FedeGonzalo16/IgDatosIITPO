from src.config.database import get_mongo, get_neo4j, get_cassandra
from bson import ObjectId
from datetime import datetime
from src.services.metadata_service import MetadataService

class StudentService:
    @staticmethod
    def create(data):
        db = get_mongo()
        # 1. Mongo (LIMPIO, SIN METADATOS)
        doc = {
            "legajo": data['legajo'],
            "nombre": data['nombre'],
            "apellido": data['apellido'],
            "email": data.get('email', ''),
            "activo": True,
            "metadata": {"estado": "ACTIVO"}
        }
        res = db.estudiantes.insert_one(doc)
        mongo_id = str(res.inserted_id)

        # 2. Metadatos EXCLUSIVOS en Cassandra
        MetadataService.save_metadata('estudiante', mongo_id, 'ACTIVO')

        # 3. Neo4j Sync
        with get_neo4j() as session:
            session.run("""
                MERGE (e:Estudiante {id_mongo: $id}) 
                SET e.nombre = $n, e.apellido = $a, e.activo = true
            """, id=mongo_id, n=data['nombre'], a=data.get('apellido', ''))
        
        return mongo_id

    @staticmethod
    def get_all():
        db = get_mongo()
        # Traemos todos los estudiantes (activos o con estructura vieja)
        students = list(db.estudiantes.find({
            "$or": [
                {"metadata.estado": "ACTIVO"},
                {"metadata.estado": {"$exists": False}},
                {"metadata": {"$exists": False}},
                {"activo": True}
            ]
        }))
        
        # Hacemos el "Join" manual con Neo4j para cada estudiante
        with get_neo4j() as session:
            for s in students:
                s['_id'] = str(s['_id'])
                try:
                    # Buscamos su institución actual en el grafo con todos los datos
                    result = session.run("""
                        MATCH (e:Estudiante {id_mongo: $uid})-[:PERTENECE_A]->(i:Institucion)
                        RETURN i.id_mongo AS institucion_id, 
                               i.nombre AS institucion_nombre, 
                               i.codigo AS institucion_codigo
                    """, uid=s['_id'])
                    
                    record = result.single()
                    if record:
                        s['institucion_id'] = record['institucion_id']
                        s['institucion_nombre'] = record['institucion_nombre']
                        s['institucion_codigo'] = record['institucion_codigo']
                    else:
                        s['institucion_id'] = None
                        s['institucion_nombre'] = "Sin Institución"
                except Exception as e:
                    s['institucion_nombre'] = "Error al cargar"
                    
        return students

    @staticmethod
    def get_by_id(uid):
        db = get_mongo()
        s = db.estudiantes.find_one({"_id": ObjectId(uid)})
        
        if s: 
            s['_id'] = str(s['_id'])
            # Ir a Neo4j a buscar a qué institución pertenece actualmente
            try:
                with get_neo4j() as session:
                    result = session.run("""
                        MATCH (e:Estudiante {id_mongo: $uid})-[:PERTENECE_A]->(i:Institucion)
                        RETURN i.id_mongo AS institucion_id, i.nombre AS institucion_nombre, i.codigo AS institucion_codigo
                    """, uid=uid)
                    
                    record = result.single()
                    if record:
                        s['institucion_id'] = record['institucion_id']
                        s['institucion_nombre'] = record['institucion_nombre']
                        s['institucion_codigo'] = record['institucion_codigo']
            except Exception as e:
                print(f"⚠️ Warning: No se pudo obtener la institución desde Neo4j para el alumno {uid}: {e}")
                
        return s

    @staticmethod
    def update(uid, data):
        db = get_mongo()
        db.estudiantes.update_one({"_id": ObjectId(uid)}, {"$set": data})
        
        # Sync Neo4j
        if 'nombre' in data or 'apellido' in data:
            with get_neo4j() as session:
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $id})
                    SET e.nombre = $nombre, e.apellido = $apellido
                """, id=uid, nombre=data.get('nombre', ''), apellido=data.get('apellido', ''))
        return True

    @staticmethod
    def delete(uid):
        db = get_mongo()
        # Soft Delete
        db.estudiantes.update_one({"_id": ObjectId(uid)}, {"$set": {"metadata.estado": "INACTIVO", "activo": False}})
        # Neo4j: Opcional borrar nodo o marcarlo
        with get_neo4j() as session:
            session.run("MATCH (e:Estudiante {id_mongo: $id}) DETACH DELETE e", id=uid)
        return True

    @staticmethod
    def get_by_email(email):
        db = get_mongo()
        student = db.estudiantes.find_one({"email": email})
        if student:
            student['_id'] = str(student['_id'])
        return student
    
    @staticmethod
    def cambiar_institucion(estudiante_id, nueva_institucion_id, regla_conversion_codigo):
        """
        Traslada al estudiante de institución, busca materias equivalentes, 
        aplica la conversión de notas y registra la auditoría.
        """
        db = get_mongo()
        materias_homologadas = []
        
        # 1. Obtener la regla de conversión desde MongoDB
        regla = db.reglas_conversion.find_one({"codigo_regla": regla_conversion_codigo})
        
        with get_neo4j() as session:
            # 2. Buscar materias que el alumno aprobó y que tienen equivalencia en la nueva institución
            equiv_query = """
                MATCH (e:Estudiante {id_mongo: $est_id})-[r_curso:CURSÓ]->(mat_origen:Materia)
                WHERE r_curso.estado = 'APROBADO'
                MATCH (mat_origen)-[:EQUIVALE_A]-(mat_destino:Materia)-[:PERTENECE_A]->(inst_nueva:Institucion {id_mongo: $new_inst_id})
                RETURN mat_origen.id_mongo AS id_mat_origen,
                       mat_origen.nombre AS materia_origen, 
                       r_curso.final AS nota_origen, 
                       mat_destino.id_mongo AS id_mat_destino, 
                       mat_destino.nombre AS materia_destino
            """
            equivalencias = session.run(equiv_query, est_id=estudiante_id, new_inst_id=nueva_institucion_id).data()
            
            for eq in equivalencias:
                nota_origen = eq['nota_origen']
                nota_convertida = nota_origen # Fallback por si falla la regla
                
                # 3. Aplicar conversión matemática/lógica
                if regla and 'mapeo' in regla:
                    for mapeo in regla['mapeo']:
                        # Comparamos como string para evitar fallos
                        if str(mapeo['nota_origen']) == str(nota_origen) or (isinstance(nota_origen, (int, float)) and float(mapeo['nota_origen']) == float(nota_origen)):
                            nota_convertida = mapeo['nota_destino']
                            break
                
                # 4. Registrar la nueva relación en Neo4j (Equivalencia Aprobada)
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $est_id}), (mat_destino:Materia {id_mongo: $id_mat_destino})
                    CREATE (e)-[r:CURSÓ {
                        estado: 'APROBADO (EQUIVALENCIA)',
                        final: $nota_convertida,
                        nota_original: $nota_origen,
                        fecha_cierre: $fecha,
                        metodo_conversion: $regla
                    }]->(mat_destino)
                """, est_id=estudiante_id, id_mat_destino=eq['id_mat_destino'], 
                     nota_convertida=nota_convertida, nota_origen=nota_origen, 
                     fecha=datetime.utcnow().isoformat(), regla=regla_conversion_codigo)
                
                # 5. Guardar la calificación inmutable en Mongo
                db.calificaciones.insert_one({
                    "estudiante_id": ObjectId(estudiante_id),
                    "materia_id": ObjectId(eq['id_mat_destino']),
                    "valor_original": {"nota": nota_origen, "tipo": "EQUIVALENCIA_ORIGEN"},
                    "valor_convertido": {"nota": nota_convertida, "regla": regla_conversion_codigo},
                    "estado": "APROBADO (EQUIVALENCIA)",
                    "created_at": datetime.utcnow()
                })
                
                materias_homologadas.append({
                    "materia": eq['materia_destino'],
                    "nota_original": nota_origen,
                    "nota_convertida": nota_convertida
                })

            # 6. Mover físicamente al estudiante de institución (BULLETPROOF)
            # Aseguramos que sean strings limpios sin espacios ocultos
            est_id_str = str(estudiante_id).strip()
            new_inst_id_str = str(nueva_institucion_id).strip()
            
            # PASO A: Verificar explícitamente que el Estudiante exista en Neo4j
            check_est = session.run("MATCH (e:Estudiante {id_mongo: $id}) RETURN e", id=est_id_str).single()
            if not check_est:
                raise ValueError(f"Error Neo4j: No se encontró al estudiante con ID '{est_id_str}'")
                
            # PASO B: Verificar explícitamente que la Institución exista en Neo4j
            check_inst = session.run("MATCH (i:Institucion {id_mongo: $id}) RETURN i.nombre AS nombre", id=new_inst_id_str).single()
            if not check_inst:
                raise ValueError(f"Error Neo4j: No se encontró la institución con ID '{new_inst_id_str}'")
                
            nombre_nueva_inst = check_inst['nombre']

            # PASO C: Ejecutar el borrado y creación garantizados
            res_update = session.run("""
                MATCH (e:Estudiante {id_mongo: $est_id})
                OPTIONAL MATCH (e)-[r:PERTENECE_A]->()
                DELETE r
                WITH e
                MATCH (i:Institucion {id_mongo: $new_inst_id})
                MERGE (e)-[:PERTENECE_A]->(i)
                RETURN e.id_mongo
            """, est_id=est_id_str, new_inst_id=new_inst_id_str).single()
            
            if not res_update:
                raise Exception("Error interno: Falló la escritura de la relación en el grafo.")
                
            print(f"✅ ÉXITO GRAFO: Estudiante movido a la institución {nombre_nueva_inst}")

        # 7. Asentar en la base de datos de Auditoría (Cassandra)
        try:
            cass = get_cassandra()
            if cass:
                mensaje_auditoria = f"Traslado a inst {nueva_institucion_id}. Homologadas {len(materias_homologadas)} materias bajo regla {regla_conversion_codigo}."
                cass.execute("""
                    INSERT INTO registro_auditoria (id_estudiante, fecha_creacion, id_auditoria, tipo_accion, nota_original)
                    VALUES (%s, toTimestamp(now()), uuid(), %s, %s)
                """, (estudiante_id, 'TRASLADO_Y_EQUIVALENCIAS', mensaje_auditoria))
        except Exception as e:
            print(f"⚠️ Cassandra error: {e}")

        return {
            "mensaje": "Traslado completado con éxito",
            "materias_homologadas": materias_homologadas,
            "total_homologadas": len(materias_homologadas)
        }