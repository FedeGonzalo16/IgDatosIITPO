import requests
import time
from datetime import datetime
from src.config.database import get_mongo, get_neo4j, get_redis, get_cassandra

BASE_URL = "http://localhost:5000/api/v1"
HEADERS  = {'Content-Type': 'application/json'}

def log(step, msg):
    print(f"\n[{step}] {msg}")

def post(endpoint, data=None):
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.post(url, json=data or {}, headers=HEADERS)
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
                nota_num = float(nota) if str(nota).replace('.','').isdigit() else (10 if nota in ['A','A*'] else (8 if nota == 'B' else (6 if nota == 'C' else 2)))
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


def crear_equivalencias(pares):
    """Recibe lista de tuplas (id1, id2) y crea EQUIVALE_A bidireccional."""
    q = "MATCH (a:Materia {id_mongo: $id1}), (b:Materia {id_mongo: $id2}) MERGE (a)-[:EQUIVALE_A]->(b) MERGE (b)-[:EQUIVALE_A]->(a)"
    with get_neo4j() as session:
        for id1, id2 in pares:
            session.run(q, id1=id1, id2=id2)


def vincular_estudiante_neo4j(est_id, inst_id, nombre, apellido):
    with get_neo4j() as session:
        session.run("""
            MATCH (e:Estudiante {id_mongo: $eid})
            SET e.nombre = $nom, e.apellido = $ape, e.activo = true
            WITH e
            MATCH (i:Institucion {id_mongo: $iid})
            MERGE (e)-[:PERTENECE_A]->(i)
        """, eid=est_id, iid=inst_id, nom=nombre, ape=apellido)


def agregar_materia_carrera(carrera_id, materia_id):
    post(f"academic/carreras/{carrera_id}/materias/{materia_id}")


def run_seed():
    print("🌱 INICIANDO SEMBRADO DE DATOS (EDUGRADE MULTIMODELO)...")
    clean_all_datastores()

    # ══════════════════════════════════════════
    # 1. INSTITUCIONES
    # ══════════════════════════════════════════
    log("1", "Creando Instituciones (AR, US, UK, DE)...")
    inst_ar = post("academic/instituciones", {"codigo": "UBA",  "nombre": "Universidad de Buenos Aires",        "pais": "AR", "sistema_calificacion": "Numerico 1-10",       "nivel": "Universitario"})['id']
    inst_us = post("academic/instituciones", {"codigo": "MIT",  "nombre": "Mass. Institute of Technology",       "pais": "US", "sistema_calificacion": "Letras A-F / GPA",    "nivel": "Universitario"})['id']
    inst_uk = post("academic/instituciones", {"codigo": "OXF",  "nombre": "Oxford University",                   "pais": "UK", "sistema_calificacion": "Letras A*-F",          "nivel": "Universitario"})['id']
    inst_de = post("academic/instituciones", {"codigo": "TUM",  "nombre": "Technical University of Munich",      "pais": "DE", "sistema_calificacion": "Inverso 1.0-6.0",      "nivel": "Universitario"})['id']
    print(f"   ✅ 4 instituciones creadas.")

    # ══════════════════════════════════════════
    # 2. ADMIN Y PROFESORES
    # ══════════════════════════════════════════
    log("2", "Creando Admin y Profesores...")
    db = get_mongo()
    res_admin = db.administradores.insert_one({
        "legajo": "ADMIN-001", "nombre": "Admin", "apellido": "Global",
        "email": "admin@edugrade.com", "activo": True
    })
    admin_id = str(res_admin.inserted_id)
    with get_neo4j() as session:
        session.run("CREATE (a:Admin {id_mongo: $id, nombre: 'Admin', apellido: 'Global', activo: true})", id=admin_id)
    print("   ✅ Admin creado.")

    prof_ar1 = post("profesores/", {"legajo_docente": "P-AR1", "nombre": "Jorge",   "apellido": "Borges",    "especialidad": "Bases de Datos",        "email": "jorge@mail.com",   "password": "123456", "rol": "profesor"})['id']
    prof_ar2 = post("profesores/", {"legajo_docente": "P-AR2", "nombre": "María",   "apellido": "García",    "especialidad": "Algoritmos",            "email": "maria@mail.com",   "password": "123456", "rol": "profesor"})['id']
    prof_ar3 = post("profesores/", {"legajo_docente": "P-AR3", "nombre": "Carlos",  "apellido": "López",     "especialidad": "Sistemas Operativos",   "email": "carlos@mail.com",  "password": "123456", "rol": "profesor"})['id']
    prof_us1 = post("profesores/", {"legajo_docente": "P-US1", "nombre": "Alan",    "apellido": "Turing",    "especialidad": "Computer Science",      "email": "alan@mail.com",    "password": "123456", "rol": "profesor"})['id']
    prof_us2 = post("profesores/", {"legajo_docente": "P-US2", "nombre": "Lisa",    "apellido": "Chen",      "especialidad": "Machine Learning",      "email": "lisa@mail.com",    "password": "123456", "rol": "profesor"})['id']
    prof_uk1 = post("profesores/", {"legajo_docente": "P-UK1", "nombre": "Ada",     "apellido": "Lovelace",  "especialidad": "Programming",           "email": "ada@mail.com",     "password": "123456", "rol": "profesor"})['id']
    prof_de1 = post("profesores/", {"legajo_docente": "P-DE1", "nombre": "Heinrich","apellido": "Müller",    "especialidad": "Informatik",            "email": "heinrich@mail.com","password": "123456", "rol": "profesor"})['id']
    print(f"   ✅ 7 profesores creados.")

    # ══════════════════════════════════════════
    # 3. MATERIAS (4-5 por institución)
    # ══════════════════════════════════════════
    log("3", "Creando Materias por institución...")

    # — UBA (Argentina, escala 1-10) —
    mat_bd_ar    = post("academic/materias", {"codigo": "BD-AR",    "nombre": "Bases de Datos I",            "institucion_id": inst_ar})['id']
    mat_algo_ar  = post("academic/materias", {"codigo": "ALGO-AR",  "nombre": "Algoritmos y Estructuras",    "institucion_id": inst_ar})['id']
    mat_so_ar    = post("academic/materias", {"codigo": "SO-AR",    "nombre": "Sistemas Operativos",         "institucion_id": inst_ar})['id']
    mat_redes_ar = post("academic/materias", {"codigo": "REDES-AR", "nombre": "Redes de Computadoras",       "institucion_id": inst_ar})['id']
    mat_prog_ar  = post("academic/materias", {"codigo": "PROG-AR",  "nombre": "Programación I",              "institucion_id": inst_ar})['id']

    # — MIT (EEUU, escala letras / GPA) —
    mat_bd_us    = post("academic/materias", {"codigo": "CS-300",   "nombre": "Database Systems",            "institucion_id": inst_us})['id']
    mat_algo_us  = post("academic/materias", {"codigo": "CS-401",   "nombre": "Algorithms",                  "institucion_id": inst_us})['id']
    mat_so_us    = post("academic/materias", {"codigo": "CS-502",   "nombre": "Operating Systems",           "institucion_id": inst_us})['id']
    mat_ml_us    = post("academic/materias", {"codigo": "CS-601",   "nombre": "Machine Learning",            "institucion_id": inst_us})['id']
    mat_prog_us  = post("academic/materias", {"codigo": "CS-201",   "nombre": "Programming Fundamentals",    "institucion_id": inst_us})['id']

    # — Oxford (UK, escala A*-F) —
    mat_bd_uk    = post("academic/materias", {"codigo": "MOD-DB",   "nombre": "Data Engineering",            "institucion_id": inst_uk})['id']
    mat_algo_uk  = post("academic/materias", {"codigo": "MOD-ALGO", "nombre": "Computational Thinking",      "institucion_id": inst_uk})['id']
    mat_so_uk    = post("academic/materias", {"codigo": "MOD-OS",   "nombre": "Advanced Operating Systems",  "institucion_id": inst_uk})['id']
    mat_ml_uk    = post("academic/materias", {"codigo": "MOD-ML",   "nombre": "Machine Learning & AI",       "institucion_id": inst_uk})['id']

    # — TUM (Alemania, escala invertida 1.0-6.0) —
    mat_bd_de    = post("academic/materias", {"codigo": "INF-DB",   "nombre": "Datenbanksysteme",             "institucion_id": inst_de})['id']
    mat_algo_de  = post("academic/materias", {"codigo": "INF-ALGO", "nombre": "Algorithmen",                  "institucion_id": inst_de})['id']
    mat_so_de    = post("academic/materias", {"codigo": "INF-OS",   "nombre": "Betriebssysteme",              "institucion_id": inst_de})['id']
    mat_redes_de = post("academic/materias", {"codigo": "INF-NET",  "nombre": "Netzwerke und Kommunikation",  "institucion_id": inst_de})['id']

    print(f"   ✅ 18 materias creadas en 4 instituciones.")

    # Asignación de materias a profesores
    post(f"profesores/{prof_ar1}/asignar-materia", {"materia_id": mat_bd_ar})
    post(f"profesores/{prof_ar2}/asignar-materia", {"materia_id": mat_algo_ar})
    post(f"profesores/{prof_ar3}/asignar-materia", {"materia_id": mat_so_ar})
    post(f"profesores/{prof_ar3}/asignar-materia", {"materia_id": mat_redes_ar})
    post(f"profesores/{prof_us1}/asignar-materia", {"materia_id": mat_bd_us})
    post(f"profesores/{prof_us1}/asignar-materia", {"materia_id": mat_algo_us})
    post(f"profesores/{prof_us2}/asignar-materia", {"materia_id": mat_ml_us})
    post(f"profesores/{prof_uk1}/asignar-materia", {"materia_id": mat_bd_uk})
    post(f"profesores/{prof_de1}/asignar-materia", {"materia_id": mat_bd_de})
    post(f"profesores/{prof_de1}/asignar-materia", {"materia_id": mat_algo_de})

    # Equivalencias entre instituciones (misma disciplina, diferente escala)
    crear_equivalencias([
        (mat_bd_ar,   mat_bd_us),   (mat_bd_us,   mat_bd_uk),   (mat_bd_uk,   mat_bd_de),
        (mat_algo_ar, mat_algo_us), (mat_algo_us, mat_algo_uk), (mat_algo_uk, mat_algo_de),
        (mat_so_ar,   mat_so_us),   (mat_so_us,   mat_so_uk),   (mat_so_uk,   mat_so_de),
        (mat_redes_ar, mat_redes_de),
    ])
    print("   ✅ Equivalencias entre instituciones creadas.")

    # ══════════════════════════════════════════
    # 4. CARRERAS
    # ══════════════════════════════════════════
    log("4", "Creando Carreras y asignando materias...")

    car_sistemas = post("academic/carreras", {"codigo": "IS-UBA",  "nombre": "Ingeniería en Sistemas"})['id']
    car_cs_us    = post("academic/carreras", {"codigo": "CS-MIT",  "nombre": "Computer Science"})['id']
    car_cs_uk    = post("academic/carreras", {"codigo": "CS-OXF",  "nombre": "Computer Science Oxford"})['id']
    car_inf_de   = post("academic/carreras", {"codigo": "INF-TUM", "nombre": "Informatik"})['id']

    # Ingeniería en Sistemas (UBA)
    for mat in [mat_bd_ar, mat_algo_ar, mat_so_ar, mat_redes_ar, mat_prog_ar]:
        agregar_materia_carrera(car_sistemas, mat)

    # Computer Science (MIT)
    for mat in [mat_bd_us, mat_algo_us, mat_so_us, mat_ml_us, mat_prog_us]:
        agregar_materia_carrera(car_cs_us, mat)

    # Computer Science (Oxford)
    for mat in [mat_bd_uk, mat_algo_uk, mat_so_uk, mat_ml_uk]:
        agregar_materia_carrera(car_cs_uk, mat)

    # Informatik (TUM)
    for mat in [mat_bd_de, mat_algo_de, mat_so_de, mat_redes_de]:
        agregar_materia_carrera(car_inf_de, mat)

    print("   ✅ 4 carreras creadas con sus materias asignadas.")

    # ══════════════════════════════════════════
    # 4b. REGLAS DE CONVERSIÓN
    # ══════════════════════════════════════════
    log("4b", "Insertando Reglas de Conversión (todas las combinaciones AR/US/UK/DE)...")

    reglas_conversion = [
        {"codigo_regla": "AR_TO_UK",     "nombre": "Argentina → Reino Unido (GCSE/A-Level)", "mapeo": [
            {"nota_origen": 10, "nota_destino": "A*"}, {"nota_origen": 9, "nota_destino": "A"},
            {"nota_origen": 8,  "nota_destino": "B"},  {"nota_origen": 7, "nota_destino": "C"},
            {"nota_origen": 6,  "nota_destino": "D"},  {"nota_origen": 5, "nota_destino": "E"},
            {"nota_origen": 4,  "nota_destino": "F"},  {"nota_origen": 3, "nota_destino": "F"},
            {"nota_origen": 2,  "nota_destino": "F"},  {"nota_origen": 1, "nota_destino": "F"},
        ]},
        {"codigo_regla": "AR_TO_US",     "nombre": "Argentina → Estados Unidos (Letras)", "mapeo": [
            {"nota_origen": 10, "nota_destino": "A"}, {"nota_origen": 9, "nota_destino": "A"},
            {"nota_origen": 8,  "nota_destino": "B"}, {"nota_origen": 7, "nota_destino": "C"},
            {"nota_origen": 6,  "nota_destino": "D"}, {"nota_origen": 5, "nota_destino": "F"},
            {"nota_origen": 4,  "nota_destino": "F"}, {"nota_origen": 3, "nota_destino": "F"},
            {"nota_origen": 2,  "nota_destino": "F"}, {"nota_origen": 1, "nota_destino": "F"},
        ]},
        {"codigo_regla": "AR_TO_US_GPA", "nombre": "Argentina → Estados Unidos (GPA 0-4)", "mapeo": [
            {"nota_origen": 10, "nota_destino": 4.0}, {"nota_origen": 9, "nota_destino": 3.5},
            {"nota_origen": 8,  "nota_destino": 3.0}, {"nota_origen": 7, "nota_destino": 2.5},
            {"nota_origen": 6,  "nota_destino": 2.0}, {"nota_origen": 5, "nota_destino": 1.0},
            {"nota_origen": 4,  "nota_destino": 0.0}, {"nota_origen": 3, "nota_destino": 0.0},
            {"nota_origen": 2,  "nota_destino": 0.0}, {"nota_origen": 1, "nota_destino": 0.0},
        ]},
        {"codigo_regla": "AR_TO_DE",     "nombre": "Argentina → Alemania (1.0-6.0)", "mapeo": [
            {"nota_origen": 10, "nota_destino": 1.0}, {"nota_origen": 9, "nota_destino": 1.3},
            {"nota_origen": 8,  "nota_destino": 2.0}, {"nota_origen": 7, "nota_destino": 2.5},
            {"nota_origen": 6,  "nota_destino": 4.0}, {"nota_origen": 5, "nota_destino": 5.0},
            {"nota_origen": 4,  "nota_destino": 6.0}, {"nota_origen": 3, "nota_destino": 6.0},
            {"nota_origen": 2,  "nota_destino": 6.0}, {"nota_origen": 1, "nota_destino": 6.0},
        ]},
        {"codigo_regla": "UK_TO_AR",     "nombre": "Reino Unido → Argentina", "mapeo": [
            {"nota_origen": "A*", "nota_destino": 10}, {"nota_origen": "A", "nota_destino": 9},
            {"nota_origen": "B",  "nota_destino": 8},  {"nota_origen": "C", "nota_destino": 7},
            {"nota_origen": "D",  "nota_destino": 6},  {"nota_origen": "E", "nota_destino": 5},
            {"nota_origen": "F",  "nota_destino": 4},
        ]},
        {"codigo_regla": "UK_TO_US",     "nombre": "Reino Unido → Estados Unidos", "mapeo": [
            {"nota_origen": "A*", "nota_destino": "A"}, {"nota_origen": "A", "nota_destino": "A"},
            {"nota_origen": "B",  "nota_destino": "B"}, {"nota_origen": "C", "nota_destino": "C"},
            {"nota_origen": "D",  "nota_destino": "D"}, {"nota_origen": "E", "nota_destino": "F"},
            {"nota_origen": "F",  "nota_destino": "F"},
        ]},
        {"codigo_regla": "UK_TO_DE",     "nombre": "Reino Unido → Alemania", "mapeo": [
            {"nota_origen": "A*", "nota_destino": 1.0}, {"nota_origen": "A", "nota_destino": 1.3},
            {"nota_origen": "B",  "nota_destino": 2.0}, {"nota_origen": "C", "nota_destino": 2.5},
            {"nota_origen": "D",  "nota_destino": 4.0}, {"nota_origen": "E", "nota_destino": 5.0},
            {"nota_origen": "F",  "nota_destino": 6.0},
        ]},
        {"codigo_regla": "US_TO_AR",     "nombre": "Estados Unidos (Letras) → Argentina", "mapeo": [
            {"nota_origen": "A",  "nota_destino": 10}, {"nota_origen": "A+", "nota_destino": 10}, {"nota_origen": "A-", "nota_destino": 9},
            {"nota_origen": "B",  "nota_destino": 8},  {"nota_origen": "B+", "nota_destino": 8},  {"nota_origen": "B-", "nota_destino": 7},
            {"nota_origen": "C",  "nota_destino": 7},  {"nota_origen": "C+", "nota_destino": 6},  {"nota_origen": "C-", "nota_destino": 6},
            {"nota_origen": "D",  "nota_destino": 6},  {"nota_origen": "F",  "nota_destino": 4},
        ]},
        {"codigo_regla": "US_TO_UK",     "nombre": "Estados Unidos → Reino Unido", "mapeo": [
            {"nota_origen": "A",  "nota_destino": "A"},  {"nota_origen": "A+", "nota_destino": "A*"}, {"nota_origen": "A-", "nota_destino": "A"},
            {"nota_origen": "B",  "nota_destino": "B"},  {"nota_origen": "B+", "nota_destino": "B"},  {"nota_origen": "B-", "nota_destino": "B"},
            {"nota_origen": "C",  "nota_destino": "C"},  {"nota_origen": "C+", "nota_destino": "C"},  {"nota_origen": "C-", "nota_destino": "C"},
            {"nota_origen": "D",  "nota_destino": "D"},  {"nota_origen": "F",  "nota_destino": "F"},
        ]},
        {"codigo_regla": "US_TO_DE",     "nombre": "Estados Unidos → Alemania", "mapeo": [
            {"nota_origen": "A",  "nota_destino": 1.0}, {"nota_origen": "A+", "nota_destino": 1.0}, {"nota_origen": "A-", "nota_destino": 1.3},
            {"nota_origen": "B",  "nota_destino": 2.0}, {"nota_origen": "B+", "nota_destino": 1.7}, {"nota_origen": "B-", "nota_destino": 2.3},
            {"nota_origen": "C",  "nota_destino": 3.0}, {"nota_origen": "C+", "nota_destino": 2.5}, {"nota_origen": "C-", "nota_destino": 3.3},
            {"nota_origen": "D",  "nota_destino": 4.0}, {"nota_origen": "F",  "nota_destino": 6.0},
        ]},
        {"codigo_regla": "US_GPA_TO_AR", "nombre": "Estados Unidos (GPA) → Argentina", "mapeo": [
            {"nota_origen": 4.0, "nota_destino": 10}, {"nota_origen": 3.5, "nota_destino": 9},
            {"nota_origen": 3.0, "nota_destino": 8},  {"nota_origen": 2.5, "nota_destino": 7},
            {"nota_origen": 2.0, "nota_destino": 6},  {"nota_origen": 1.5, "nota_destino": 5},
            {"nota_origen": 1.0, "nota_destino": 4},  {"nota_origen": 0.5, "nota_destino": 4},
            {"nota_origen": 0.0, "nota_destino": 4},
        ]},
        {"codigo_regla": "DE_TO_AR",     "nombre": "Alemania → Argentina", "mapeo": [
            {"nota_origen": 1.0, "nota_destino": 10}, {"nota_origen": 1.3, "nota_destino": 9}, {"nota_origen": 1.7, "nota_destino": 9},
            {"nota_origen": 2.0, "nota_destino": 8},  {"nota_origen": 2.3, "nota_destino": 8}, {"nota_origen": 2.7, "nota_destino": 7},
            {"nota_origen": 3.0, "nota_destino": 7},  {"nota_origen": 3.3, "nota_destino": 7}, {"nota_origen": 3.7, "nota_destino": 6},
            {"nota_origen": 4.0, "nota_destino": 6},  {"nota_origen": 4.3, "nota_destino": 5}, {"nota_origen": 4.7, "nota_destino": 5},
            {"nota_origen": 5.0, "nota_destino": 4},  {"nota_origen": 5.3, "nota_destino": 4}, {"nota_origen": 5.7, "nota_destino": 4},
            {"nota_origen": 6.0, "nota_destino": 4},
        ]},
        {"codigo_regla": "DE_TO_UK",     "nombre": "Alemania → Reino Unido", "mapeo": [
            {"nota_origen": 1.0, "nota_destino": "A*"}, {"nota_origen": 1.3, "nota_destino": "A"}, {"nota_origen": 1.7, "nota_destino": "A"},
            {"nota_origen": 2.0, "nota_destino": "B"},  {"nota_origen": 2.3, "nota_destino": "B"}, {"nota_origen": 2.7, "nota_destino": "C"},
            {"nota_origen": 3.0, "nota_destino": "C"},  {"nota_origen": 3.3, "nota_destino": "C"}, {"nota_origen": 3.7, "nota_destino": "D"},
            {"nota_origen": 4.0, "nota_destino": "D"},  {"nota_origen": 4.3, "nota_destino": "E"}, {"nota_origen": 4.7, "nota_destino": "E"},
            {"nota_origen": 5.0, "nota_destino": "F"},  {"nota_origen": 5.3, "nota_destino": "F"}, {"nota_origen": 5.7, "nota_destino": "F"},
            {"nota_origen": 6.0, "nota_destino": "F"},
        ]},
        {"codigo_regla": "DE_TO_US",     "nombre": "Alemania → Estados Unidos", "mapeo": [
            {"nota_origen": 1.0, "nota_destino": "A"}, {"nota_origen": 1.3, "nota_destino": "A"}, {"nota_origen": 1.7, "nota_destino": "A"},
            {"nota_origen": 2.0, "nota_destino": "B"}, {"nota_origen": 2.3, "nota_destino": "B"}, {"nota_origen": 2.7, "nota_destino": "C"},
            {"nota_origen": 3.0, "nota_destino": "C"}, {"nota_origen": 3.3, "nota_destino": "C"}, {"nota_origen": 3.7, "nota_destino": "D"},
            {"nota_origen": 4.0, "nota_destino": "D"}, {"nota_origen": 4.3, "nota_destino": "F"}, {"nota_origen": 4.7, "nota_destino": "F"},
            {"nota_origen": 5.0, "nota_destino": "F"}, {"nota_origen": 5.3, "nota_destino": "F"}, {"nota_origen": 5.7, "nota_destino": "F"},
            {"nota_origen": 6.0, "nota_destino": "F"},
        ]},
    ]

    db.reglas_conversion.insert_many(reglas_conversion)
    print(f"   ✅ {len(reglas_conversion)} reglas de conversión insertadas.")

    # ══════════════════════════════════════════
    # 5. ESTUDIANTES
    # ══════════════════════════════════════════
    log("5", "Creando Estudiantes y vinculando a Instituciones...")

    # Argentina (UBA)
    est_fede  = post("estudiantes/", {"legajo": "L-111", "nombre": "Federico", "apellido": "Recursante", "email": "fede@mail.com",   "pais": "AR", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_fede,  inst_ar, "Federico", "Recursante")

    est_ana   = post("estudiantes/", {"legajo": "L-222", "nombre": "Ana",      "apellido": "Aprevio",    "email": "ana@mail.com",    "pais": "AR", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_ana,   inst_ar, "Ana", "Aprevio")

    est_lucas = post("estudiantes/", {"legajo": "L-999", "nombre": "Lucas",    "apellido": "Activo",     "email": "lucas@mail.com",  "pais": "AR", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_lucas, inst_ar, "Lucas", "Activo")

    est_maria = post("estudiantes/", {"legajo": "L-444", "nombre": "María",    "apellido": "González",   "email": "mariag@mail.com", "pais": "AR", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_maria, inst_ar, "María", "González")

    est_pablo = post("estudiantes/", {"legajo": "L-555", "nombre": "Pablo",    "apellido": "Rodríguez",  "email": "pablo@mail.com",  "pais": "AR", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_pablo, inst_ar, "Pablo", "Rodríguez")

    # EEUU (MIT)
    est_john  = post("estudiantes/", {"legajo": "L-333", "nombre": "John",     "apellido": "Exchange",   "email": "john@mail.com",   "pais": "US", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_john,  inst_us, "John", "Exchange")

    est_emma  = post("estudiantes/", {"legajo": "L-888", "nombre": "Emma",     "apellido": "Current",    "email": "emma@mail.com",   "pais": "US", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_emma,  inst_us, "Emma", "Current")

    est_mike  = post("estudiantes/", {"legajo": "L-777", "nombre": "Michael",  "apellido": "Carter",     "email": "mike@mail.com",   "pais": "US", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_mike,  inst_us, "Michael", "Carter")

    # UK (Oxford)
    est_sophie = post("estudiantes/", {"legajo": "L-600", "nombre": "Sophie",  "apellido": "Williams",   "email": "sophie@mail.com", "pais": "UK", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_sophie, inst_uk, "Sophie", "Williams")

    # Alemania (TUM)
    est_klaus = post("estudiantes/", {"legajo": "L-700", "nombre": "Klaus",    "apellido": "Becker",     "email": "klaus@mail.com",  "pais": "DE", "password": "123456"})['id']
    vincular_estudiante_neo4j(est_klaus, inst_de, "Klaus", "Becker")

    print(f"   ✅ 10 estudiantes creados y vinculados.")

    # ══════════════════════════════════════════
    # 6. CURSADAS Y CALIFICACIONES
    # ══════════════════════════════════════════
    log("6", "Simulando Cursadas y Calificaciones...")

    # ── Federico: recursó BD y aprobó, tiene algo parcialmente cursada ──
    print("   👉 Federico: recursa BD (2024), aprueba en 2025; avanza en Algoritmos")
    sync_curso_relation(est_fede, mat_bd_ar,   "PARCIAL_1", 2,  "2024")
    sync_curso_relation(est_fede, mat_bd_ar,   "FINAL",     2,  "2024")
    sync_curso_relation(est_fede, mat_bd_ar,   "PARCIAL_1", 7,  "2025")
    sync_curso_relation(est_fede, mat_bd_ar,   "FINAL",     8,  "2025")
    sync_curso_relation(est_fede, mat_algo_ar, "PARCIAL_1", 6,  "2025")
    sync_curso_relation(est_fede, mat_algo_ar, "FINAL",     7,  "2025")
    sync_curso_relation(est_fede, mat_prog_ar, "PARCIAL_1", 9,  "2024")
    sync_curso_relation(est_fede, mat_prog_ar, "FINAL",     9,  "2024")

    # ── Ana: va a previo en BD, aprueba; tiene SO en curso ──
    print("   👉 Ana: previo en BD (aprueba), cursando SO")
    sync_curso_relation(est_ana, mat_bd_ar,   "PARCIAL_1", 6,  "2025")
    sync_curso_relation(est_ana, mat_bd_ar,   "FINAL",     5,  "2025")
    sync_curso_relation(est_ana, mat_bd_ar,   "PREVIO",    7,  "2025")
    sync_curso_relation(est_ana, mat_prog_ar, "PARCIAL_1", 8,  "2024")
    sync_curso_relation(est_ana, mat_prog_ar, "FINAL",     8,  "2024")
    sync_curso_relation(est_ana, mat_so_ar,   "PARCIAL_1", 7,  "2026")  # cursada activa

    # ── Lucas: cursada activa en BD ──
    print("   👉 Lucas: cursada activa en BD")
    sync_curso_relation(est_lucas, mat_bd_ar, "PARCIAL_1", 8, "2026")

    # ── María: alumna regular, varias materias aprobadas ──
    print("   👉 María: alumna regular avanzada")
    sync_curso_relation(est_maria, mat_prog_ar,  "PARCIAL_1", 10, "2023")
    sync_curso_relation(est_maria, mat_prog_ar,  "FINAL",     10, "2023")
    sync_curso_relation(est_maria, mat_algo_ar,  "PARCIAL_1", 9,  "2024")
    sync_curso_relation(est_maria, mat_algo_ar,  "FINAL",     9,  "2024")
    sync_curso_relation(est_maria, mat_bd_ar,    "PARCIAL_1", 8,  "2025")
    sync_curso_relation(est_maria, mat_bd_ar,    "FINAL",     9,  "2025")
    sync_curso_relation(est_maria, mat_redes_ar, "PARCIAL_1", 7,  "2026")  # cursada activa

    # ── Pablo: rendimiento regular, una materia reprobada ──
    print("   👉 Pablo: rendimiento mixto")
    sync_curso_relation(est_pablo, mat_prog_ar, "PARCIAL_1", 5,  "2024")
    sync_curso_relation(est_pablo, mat_prog_ar, "FINAL",     4,  "2024")
    sync_curso_relation(est_pablo, mat_prog_ar, "PREVIO",    6,  "2024")  # aprueba en previo
    sync_curso_relation(est_pablo, mat_bd_ar,   "PARCIAL_1", 4,  "2025")
    sync_curso_relation(est_pablo, mat_bd_ar,   "FINAL",     3,  "2025")  # reprueba
    sync_curso_relation(est_pablo, mat_algo_ar, "PARCIAL_1", 6,  "2026")  # cursada activa

    # ── John (EEUU → AR): aprobó materias en MIT, se traslada ──
    print("   👉 John: aprueba en MIT y rinde equivalencias en UBA")
    sync_curso_relation(est_john, mat_bd_us,   "FINAL",     "A", "2024")
    sync_curso_relation(est_john, mat_algo_us, "FINAL",     "B", "2024")
    sync_curso_relation(est_john, mat_bd_ar,   "FINAL",     9,   "2025")

    # ── Emma: cursada activa en MIT ──
    print("   👉 Emma: cursada activa en MIT")
    sync_curso_relation(est_emma, mat_bd_us,   "PARCIAL_1", "B", "2026")
    sync_curso_relation(est_emma, mat_algo_us, "PARCIAL_1", "A", "2026")

    # ── Michael: alumno avanzado en MIT ──
    print("   👉 Michael: alumno avanzado MIT")
    sync_curso_relation(est_mike, mat_prog_us, "FINAL", "A",  "2022")
    sync_curso_relation(est_mike, mat_bd_us,   "FINAL", "A",  "2023")
    sync_curso_relation(est_mike, mat_algo_us, "FINAL", "B",  "2024")
    sync_curso_relation(est_mike, mat_so_us,   "PARCIAL_1", "A", "2026")  # cursada activa

    # ── Sophie (Oxford) ──
    print("   👉 Sophie: alumna Oxford")
    sync_curso_relation(est_sophie, mat_bd_uk,   "FINAL", "A*", "2024")
    sync_curso_relation(est_sophie, mat_algo_uk, "FINAL", "A",  "2024")
    sync_curso_relation(est_sophie, mat_so_uk,   "PARCIAL_1", "B", "2026")  # activa

    # ── Klaus (TUM, escala inversa) ──
    print("   👉 Klaus: alumno TUM (escala inversa alemana)")
    sync_curso_relation(est_klaus, mat_bd_de,    "FINAL", 1.3, "2023")
    sync_curso_relation(est_klaus, mat_algo_de,  "FINAL", 2.0, "2024")
    sync_curso_relation(est_klaus, mat_redes_de, "PARCIAL_1", 1.7, "2026")  # activa

    print("\n✅ DATA SEED FINALIZADO EXITOSAMENTE.")
    print(f"   Instituciones : 5  |  Profesores : 7")
    print(f"   Materias       : 18 |  Carreras   : 4")
    print(f"   Estudiantes    : 10 |  Reglas CV  : {len(reglas_conversion)}")


if __name__ == "__main__":
    run_seed()
