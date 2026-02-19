import requests
import time
from datetime import datetime
from src.config.database import get_mongo, get_neo4j, get_redis, get_cassandra

# Configuración
BASE_URL = "http://localhost:5000/api/v1"
HEADERS = {'Content-Type': 'application/json'}

def log(step, msg):
    print(f"\n[{step}] {msg}")

def post(endpoint, data):
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.post(url, json=data, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en {url}: {e}")
        return None

def clean_all_datastores():
    print("🧹 Limpiando todas las bases de datos (Mongo, Redis, Neo4j, Cassandra)...")
    try:
        db = get_mongo()
        for c in db.list_collection_names():
            db.drop_collection(c)
    except Exception as e: print(f"   ⚠️ Mongo cleanup falló: {e}")

    try:
        r = get_redis()
        r.flushdb()
    except Exception as e: print(f"   ⚠️ Redis cleanup falló: {e}")

    try:
        with get_neo4j() as session:
            session.run("MATCH (n) DETACH DELETE n")
    except Exception as e: print(f"   ⚠️ Neo4j cleanup falló: {e}")

    try:
        cass = get_cassandra()
        if cass:
            for t in ['registro_auditoria', 'certificados_emitidos', 'entity_metadata', 'historico_reglas']:
                try: cass.execute(f"TRUNCATE {t}")
                except Exception: pass
    except Exception as e: print(f"   ⚠️ Cassandra cleanup falló: {e}")


def sync_curso_relation(est_id, mat_id, tipo, nota, anio_lectivo="2025"):
    try:
        with get_neo4j() as session:
            session.run("MERGE (e:Estudiante {id_mongo: $eid}) MERGE (m:Materia {id_mongo: $mid})", eid=est_id, mid=mat_id)

            if tipo in ['PARCIAL_1', 'PARCIAL_2', 'MIDTERM']:
                prop = "primer_parcial" if tipo in ['PARCIAL_1', 'MIDTERM'] else "segundo_parcial"
                session.run(f"""
                    MATCH (e:Estudiante {{id_mongo: $eid}}), (m:Materia {{id_mongo: $mid}})
                    MERGE (e)-[r:CURSANDO {{anio: $anio}}]->(m)
                    SET r.{prop} = $nota, r.updated_at = $now
                """, eid=est_id, mid=mat_id, nota=nota, anio=anio_lectivo, now=datetime.utcnow().isoformat())

            elif tipo == 'FINAL':
                nota_num = float(nota) if str(nota).isdigit() else (10 if nota in ['A','A*'] else 2)
                estado_final = "APROBADO" if nota_num >= 6 else ("A PREVIO" if 4 <= nota_num < 6 else "RECURSA")
                
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $eid})-[r:CURSANDO]->(m:Materia {id_mongo: $mid})
                    CREATE (e)-[r2:CURSÓ]->(m)
                    SET r2 = properties(r), r2.estado = $estado, r2.final = $nota, r2.fecha_cierre = $now
                    DELETE r
                """, eid=est_id, mid=mat_id, estado=estado_final, nota=nota, now=datetime.utcnow().isoformat())

            elif tipo == 'PREVIO':
                nota_num = float(nota)
                nuevo_estado = "APROBADO" if nota_num >= 6 else "RECURSA"
                session.run("""
                    MATCH (e:Estudiante {id_mongo: $eid})-[r:CURSÓ]->(m:Materia {id_mongo: $mid})
                    SET r.previo = $nota, r.estado = $estado, r.fecha_cierre = $now
                """, eid=est_id, mid=mat_id, nota=nota, estado=nuevo_estado, now=datetime.utcnow().isoformat())
    except Exception as e:
        print(f"   ⚠️ Error en Neo4j: {e}")

def crear_equivalencias_neo4j(mat_ar, mat_us, mat_uk, mat_de):
    with get_neo4j() as session:
        queries = ["MATCH (a:Materia {id_mongo: $id1}), (b:Materia {id_mongo: $id2}) MERGE (a)-[:EQUIVALE_A]->(b) MERGE (b)-[:EQUIVALE_A]->(a)"]
        for q in queries:
            session.run(q, id1=mat_ar, id2=mat_us)
            session.run(q, id1=mat_us, id2=mat_uk)
            session.run(q, id1=mat_uk, id2=mat_de)

def vincular_estudiante_neo4j(est_id, inst_id, nombre, apellido):
    """Agrega propiedades faltantes y vincula al estudiante con su institución"""
    with get_neo4j() as session:
        session.run("""
            MATCH (e:Estudiante {id_mongo: $eid})
            SET e.nombre = $nom, e.apellido = $ape, e.activo = true
            WITH e
            MATCH (i:Institucion {id_mongo: $iid})
            MERGE (e)-[:PERTENECE_A]->(i)
        """, eid=est_id, iid=inst_id, nom=nombre, ape=apellido)


def run_seed():
    print("🌱 INICIANDO SEMBRADO DE DATOS (EDICALIFICACIONES MULTIMODELO)...")
    clean_all_datastores()
    
    # ==========================================
    # 1. INSTITUCIONES (Sistemas Educativos)
    # ==========================================
    log("1", "Creando Instituciones (AR, US, UK, DE)...")
    inst_ar = post("academic/instituciones", {"codigo": "UBA", "nombre": "Universidad de Buenos Aires", "pais": "AR", "sistema_calificacion": "Numerico 1-10"})['id']
    inst_us = post("academic/instituciones", {"codigo": "MIT", "nombre": "Mass. Institute of Technology", "pais": "US", "sistema_calificacion": "Letras A-F / GPA"})['id']
    inst_uk = post("academic/instituciones", {"codigo": "OXF", "nombre": "Oxford University", "pais": "UK", "sistema_calificacion": "Letras A*-F"})['id']
    inst_de = post("academic/instituciones", {"codigo": "TUM", "nombre": "Technical University of Munich", "pais": "DE", "sistema_calificacion": "Inverso 1.0-6.0"})['id']

    # ==========================================
    # 2. ADMIN DIRECTO EN BD Y PROFESORES
    # ==========================================
    log("2", "Creando Admin (Nodo Propio) y Profesores...")
    
    # Creando Admin directo para evitar que sea Estudiante
    db = get_mongo()
    res_admin = db.administradores.insert_one({
        "legajo": "ADMIN-001", "nombre": "Admin", "apellido": "Global", 
        "email": "admin@edugrade.com", "activo": True
    })
    admin_id = str(res_admin.inserted_id)
    with get_neo4j() as session:
        session.run("CREATE (a:Admin {id_mongo: $id, nombre: 'Admin', apellido: 'Global', activo: true})", id=admin_id)
    print("   ✅ Admin creado exitosamente como nodo (:Admin).")

    prof_ar = post("profesores/", {"legajo_docente": "P-AR1", "nombre": "Jorge", "apellido": "Borges", "especialidad": "Bases de Datos"})['id']
    prof_us = post("profesores/", {"legajo_docente": "P-US1", "nombre": "Alan", "apellido": "Turing", "especialidad": "Computer Science"})['id']

    # ==========================================
    # 3. MATERIAS
    # ==========================================
    log("3", "Creando Materias...")
    mat_bd_ar = post("academic/materias", {"codigo": "BD-AR", "nombre": "Bases de Datos I", "institucion_id": inst_ar})['id']
    mat_bd_us = post("academic/materias", {"codigo": "CS-300", "nombre": "Database Systems", "institucion_id": inst_us})['id']
    mat_bd_uk = post("academic/materias", {"codigo": "MOD-DB", "nombre": "Data Engineering", "institucion_id": inst_uk})['id']
    mat_bd_de = post("academic/materias", {"codigo": "INF-DB", "nombre": "Datenbanksysteme", "institucion_id": inst_de})['id']
    
    post(f"profesores/{prof_ar}/asignar-materia", {"materia_id": mat_bd_ar})
    post(f"profesores/{prof_us}/asignar-materia", {"materia_id": mat_bd_us})
    crear_equivalencias_neo4j(mat_bd_ar, mat_bd_us, mat_bd_uk, mat_bd_de)

    # ==========================================
    # 4. ESTUDIANTES (Con propiedades y relación PERTENECE_A)
    # ==========================================
    log("4", "Creando Estudiantes y vinculando a Instituciones...")
    est_fede = post("estudiantes/", {"legajo": "L-111", "nombre": "Federico", "apellido": "Recursante", "email": "fede@mail.com", "pais": "AR"})['id']
    vincular_estudiante_neo4j(est_fede, inst_ar, "Federico", "Recursante")

    est_ana = post("estudiantes/", {"legajo": "L-222", "nombre": "Ana", "apellido": "Aprevio", "email": "ana@mail.com", "pais": "AR"})['id']
    vincular_estudiante_neo4j(est_ana, inst_ar, "Ana", "Aprevio")

    est_john = post("estudiantes/", {"legajo": "L-333", "nombre": "John", "apellido": "Exchange", "email": "john@mail.com", "pais": "US"})['id']
    vincular_estudiante_neo4j(est_john, inst_us, "John", "Exchange")
    print("   ✅ Todos los estudiantes creados, con propiedades completas y vinculados a sus instituciones.")

    # ==========================================
    # 4b. CREAR REGLAS DE CONVERSIÓN
    # ==========================================
    log("4b", "Creando Reglas de Conversión (AR <-> US)...")

    reglas_conversion = [
        {"codigo_regla": "AR_TO_US", "nombre": "Argentina → Estados Unidos (Letras)", "mapeo": [
            {"nota_origen": 10, "nota_destino": "A"}, {"nota_origen": 9, "nota_destino": "A"},
            {"nota_origen": 8, "nota_destino": "B"}, {"nota_origen": 7, "nota_destino": "C"},
            {"nota_origen": 6, "nota_destino": "D"}, {"nota_origen": 5, "nota_destino": "F"},
            {"nota_origen": 4, "nota_destino": "F"}, {"nota_origen": 3, "nota_destino": "F"}, 
            {"nota_origen": 2, "nota_destino": "F"}, {"nota_origen": 1, "nota_destino": "F"},
        ]},
        {"codigo_regla": "US_TO_AR", "nombre": "Estados Unidos (Letras) → Argentina", "mapeo": [
            {"nota_origen": "A", "nota_destino": 10}, {"nota_origen": "A+", "nota_destino": 10}, {"nota_origen": "A-", "nota_destino": 9},
            {"nota_origen": "B", "nota_destino": 8}, {"nota_origen": "B+", "nota_destino": 8}, {"nota_origen": "B-", "nota_destino": 7},
            {"nota_origen": "C", "nota_destino": 7}, {"nota_origen": "C+", "nota_destino": 6}, {"nota_origen": "C-", "nota_destino": 6},
            {"nota_origen": "D", "nota_destino": 6}, {"nota_origen": "F", "nota_destino": 4},
        ]}
    ]
    
    db = get_mongo()
    db.reglas_conversion.insert_many(reglas_conversion)
    print("   ✅ Reglas de conversión (AR_TO_US y US_TO_AR) insertadas en MongoDB.")


    # ==========================================
    # 5. CURSADAS Y CALIFICACIONES
    # ==========================================
    log("5", "Simulando Cursadas Complejas...")

    print("   👉 Fede cursa Bases de Datos AR (Año 2024) -> RECURSA")
    sync_curso_relation(est_fede, mat_bd_ar, "PARCIAL_1", 2, "2024")
    sync_curso_relation(est_fede, mat_bd_ar, "FINAL", 2, "2024") 
    
    print("   👉 Fede RECURSA Bases de Datos AR (Año 2025) -> APRUEBA")
    sync_curso_relation(est_fede, mat_bd_ar, "PARCIAL_1", 7, "2025")
    sync_curso_relation(est_fede, mat_bd_ar, "FINAL", 8, "2025") 

    print("   👉 Ana cursa Bases de Datos AR -> Va a PREVIO (Nota 5)")
    sync_curso_relation(est_ana, mat_bd_ar, "PARCIAL_1", 6, "2025")
    sync_curso_relation(est_ana, mat_bd_ar, "FINAL", 5, "2025") 
    
    print("   👉 Ana rinde el PREVIO (recuperatorio final) y saca 7")
    sync_curso_relation(est_ana, mat_bd_ar, "PREVIO", 7, "2025") 

    print("   👉 John cursa Database Systems (US)")
    sync_curso_relation(est_john, mat_bd_us, "FINAL", "A", "2024") 
    print("   👉 John se muda a Argentina y rinde equivalencia")
    sync_curso_relation(est_john, mat_bd_ar, "FINAL", 9, "2025") 

    print("\n✅ DATA SEED FINALIZADO EXITOSAMENTE.")

if __name__ == "__main__":
    run_seed()