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
        
        with get_neo4j() as session:
            if 'nombre' in data or 'apellido' in data:
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $id})
                    SET e.nombre = $nombre, e.apellido = $apellido
                """, id=uid, nombre=data.get('nombre', ''), apellido=data.get('apellido', ''))
            if 'institucion_id' in data:
                inst_id = str(data['institucion_id']).strip()
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $est_id})
                    OPTIONAL MATCH (e)-[r:PERTENECE_A]->()
                    DELETE r
                    WITH e
                    MATCH (i:Institucion {id_mongo: $new_inst_id})
                    MERGE (e)-[:PERTENECE_A]->(i)
                """, est_id=uid, new_inst_id=inst_id)
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
        if not student:
            return None
        student['_id'] = str(student['_id'])
        # Join con Neo4j para incluir institución (igual que get_by_id)
        try:
            with get_neo4j() as session:
                result = session.run("""
                    MATCH (e:Estudiante {id_mongo: $uid})-[:PERTENECE_A]->(i:Institucion)
                    RETURN i.id_mongo AS institucion_id,
                           i.nombre   AS institucion_nombre,
                           i.codigo   AS institucion_codigo
                """, uid=student['_id'])
                record = result.single()
                if record:
                    student['institucion_id']     = record['institucion_id']
                    student['institucion_nombre'] = record['institucion_nombre']
                    student['institucion_codigo'] = record['institucion_codigo']
                else:
                    student['institucion_id']     = None
                    student['institucion_nombre'] = None
        except Exception as e:
            print(f"⚠️ Warning: No se pudo obtener la institución para el alumno {student['_id']}: {e}")
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
            # - Solo APROBADO (excluye REPROBADO; recursadas fallidas no se usan)
            # - Excluye si ya tiene CURSÓ a mat_destino (evita duplicados al cambiar 2 veces)
            # - Si hay múltiples CURSÓ a la misma materia (recursada aprobada), toma solo la más reciente
            equiv_query = """
                MATCH (e:Estudiante {id_mongo: $est_id})-[r_curso:CURSÓ]->(mat_origen:Materia)
                WHERE r_curso.estado IN ['APROBADO', 'APROBADO (EQUIVALENCIA)']
                MATCH (mat_origen)-[:EQUIVALE_A]-(mat_destino:Materia)-[:PERTENECE_A]->(inst_nueva:Institucion {id_mongo: $new_inst_id})
                WITH mat_origen, mat_destino, r_curso
                ORDER BY r_curso.fecha_cierre DESC
                WITH mat_origen, mat_destino, collect(r_curso)[0] AS r_curso
                RETURN mat_origen.id_mongo AS id_mat_origen,
                       mat_origen.nombre AS materia_origen,
                       COALESCE(r_curso.nota_original, r_curso.final) AS nota_origen,
                       mat_destino.id_mongo AS id_mat_destino,
                       mat_destino.nombre AS materia_destino
            """
            equivalencias = session.run(equiv_query, est_id=estudiante_id, new_inst_id=nueva_institucion_id).data()
            
            # Evitar procesar el mismo (origen, destino) dos veces (recursada o duplicados en grafo)
            procesados = set()
            for eq in equivalencias:
                clave = (str(eq['id_mat_origen']), str(eq['id_mat_destino']))
                if clave in procesados:
                    continue
                procesados.add(clave)
                nota_origen = eq['nota_origen']
                nota_convertida = nota_origen  # Fallback por si falla la regla
                
                # 3. Aplicar conversión matemática/lógica
                if regla and 'mapeo' in regla:
                    for mapeo in regla['mapeo']:
                        coincide = str(mapeo['nota_origen']) == str(nota_origen)
                        if not coincide:
                            try:
                                coincide = (
                                    isinstance(nota_origen, (int, float)) and
                                    float(mapeo['nota_origen']) == float(nota_origen)
                                )
                            except (ValueError, TypeError):
                                coincide = False
                        if coincide:
                            nota_convertida = mapeo['nota_destino']
                            break
                
                fecha_conv = datetime.utcnow()

                # 4. Actualizar equivalencia existente o crear una nueva en Neo4j
                # Si ya existe una relación APROBADO (EQUIVALENCIA) la actualizamos con la nueva conversión.
                # Si existe una relación APROBADO genuina (cursada en esa institución) no la pisamos.
                existe_row = session.run("""
                    MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(mat_destino:Materia {id_mongo: $id_mat_destino})
                    RETURN r.estado AS estado
                """, est_id=estudiante_id, id_mat_destino=eq['id_mat_destino']).single()

                if existe_row:
                    if existe_row['estado'] != 'APROBADO (EQUIVALENCIA)':
                        continue  # Nota genuina, no sobreescribir
                    session.run("""
                        MATCH (e:Estudiante {id_mongo: $est_id})-[r:CURSÓ]->(mat_destino:Materia {id_mongo: $id_mat_destino})
                        WHERE r.estado = 'APROBADO (EQUIVALENCIA)'
                        SET r.final = $nota_convertida,
                            r.nota_original = $nota_origen,
                            r.metodo_conversion = $regla,
                            r.materia_origen_id = $materia_origen_id,
                            r.materia_origen_nombre = $materia_origen_nombre,
                            r.fecha_conversion = $fecha_conv
                    """, est_id=estudiante_id, id_mat_destino=eq['id_mat_destino'],
                         nota_convertida=nota_convertida, nota_origen=nota_origen,
                         regla=regla_conversion_codigo, materia_origen_id=eq['id_mat_origen'],
                         materia_origen_nombre=eq['materia_origen'], fecha_conv=fecha_conv.isoformat())
                else:
                    session.run("""
                        MATCH (e:Estudiante {id_mongo: $est_id}), (mat_destino:Materia {id_mongo: $id_mat_destino})
                        CREATE (e)-[r:CURSÓ {
                            estado: 'APROBADO (EQUIVALENCIA)',
                            final: $nota_convertida,
                            nota_original: $nota_origen,
                            fecha_cierre: $fecha_conv,
                            metodo_conversion: $regla,
                            materia_origen_id: $materia_origen_id,
                            materia_origen_nombre: $materia_origen_nombre,
                            fecha_conversion: $fecha_conv
                        }]->(mat_destino)
                    """, est_id=estudiante_id, id_mat_destino=eq['id_mat_destino'],
                         nota_convertida=nota_convertida, nota_origen=nota_origen,
                         fecha_conv=fecha_conv.isoformat(), regla=regla_conversion_codigo,
                         materia_origen_id=eq['id_mat_origen'], materia_origen_nombre=eq['materia_origen'])

                # 5. Guardar o actualizar la calificación en Mongo (upsert)
                db.calificaciones.update_one(
                    {
                        "estudiante_id": ObjectId(estudiante_id),
                        "materia_id": ObjectId(eq['id_mat_destino']),
                        "estado": "APROBADO (EQUIVALENCIA)"
                    },
                    {
                        "$set": {
                            "valor_original": {
                                "nota": nota_origen,
                                "tipo": "EQUIVALENCIA_ORIGEN",
                                "materia_origen_id": eq['id_mat_origen'],
                                "materia_origen_nombre": eq['materia_origen']
                            },
                            "valor_convertido": {
                                "nota": nota_convertida,
                                "regla": regla_conversion_codigo,
                                "metodo": regla_conversion_codigo,
                                "fecha_conversion": fecha_conv
                            },
                            "estado": "APROBADO (EQUIVALENCIA)",
                            "updated_at": fecha_conv
                        },
                        "$setOnInsert": {"created_at": fecha_conv}
                    },
                    upsert=True
                )
                
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