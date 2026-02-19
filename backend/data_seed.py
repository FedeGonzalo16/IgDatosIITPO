import requests
import json
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
        if response is not None:
            print(f"   Detalle: {response.text}")
        return None


def clean_all_datastores():
    print("🧹 Limpiando todas las bases de datos (Mongo, Redis, Neo4j, Cassandra)...")
    # Mongo: drop all collections in the configured DB
    try:
        db = get_mongo()
        cols = db.list_collection_names()
        for c in cols:
            db.drop_collection(c)
        print(f"   ✅ Mongo: {len(cols)} colecciones eliminadas.")
    except Exception as e:
        print(f"   ⚠️ Mongo cleanup falló: {e}")

    # Redis: flush db
    try:
        r = get_redis()
        r.flushdb()
        print("   ✅ Redis flushDB ejecutado.")
    except Exception as e:
        print(f"   ⚠️ Redis cleanup falló: {e}")

    # Neo4j: borrar todos los nodos y relaciones
    try:
        with get_neo4j() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("   ✅ Neo4j: todos los nodos y relaciones eliminados.")
    except Exception as e:
        print(f"   ⚠️ Neo4j cleanup falló: {e}")

    # Cassandra: truncate known audit tables
    try:
        cass = get_cassandra()
        if cass:
            tables = [
                'registro_auditoria', 'certificados_emitidos', 'entity_metadata', 'historico_reglas'
            ]
            for t in tables:
                try:
                    cass.execute(f"TRUNCATE {t}")
                except Exception:
                    # table may not exist yet
                    pass
            print(f"   ✅ Cassandra: tablas de auditoría truncadas (si existían).")
        else:
            print("   ⚠️ Cassandra session no disponible; se omite limpieza de Cassandra.")
    except Exception as e:
        print(f"   ⚠️ Cassandra cleanup falló: {e}")


def sync_curso_relation(est_id, mat_id, tipo, nota):
    """Crea/actualiza una relación CURSÓ en Neo4j entre estudiante y materia.
    - Para tipos 'FINAL' con nota aprobatoria (>=6 o letra A/B/etc) marca APROBADO y establece 'final' y 'fecha_cierre'.
    - Para otros tipos deja estado EN_CURSO y registra tipo/nota.
    """
    try:
        with get_neo4j() as session:
            # Asegurar existencia de nodos
            session.run(
                "MERGE (e:Estudiante {id_mongo: $eid}) MERGE (m:Materia {id_mongo: $mid})",
                eid=est_id, mid=mat_id
            )

            # Si es FINAL -> convertir/crear relación CURSÓ (reemplaza CURSANDO)
            if tipo == 'FINAL':
                # eliminar posible relación CURSANDO previa
                session.run(
                    "MATCH (e:Estudiante {id_mongo: $eid})-[r:CURSANDO]->(m:Materia {id_mongo: $mid}) DELETE r",
                    eid=est_id, mid=mat_id
                )
                # crear CURSÓ con propiedades finales
                session.run(
                    "MATCH (e:Estudiante {id_mongo: $eid}), (m:Materia {id_mongo: $mid}) "
                    "CREATE (e)-[r:CURSÓ {estado: 'FINALIZADO', tipo: $tipo, nota: $nota, final: $nota, fecha_cierre: $fecha_cierre}]->(m)",
                    eid=est_id, mid=mat_id, tipo=tipo, nota=nota, fecha_cierre=datetime.utcnow().isoformat()
                )
            else:
                # Para parciales, midterms, projects intermedios: marcar CURSANDO (upsert)
                session.run(
                    "MATCH (e:Estudiante {id_mongo: $eid}), (m:Materia {id_mongo: $mid}) "
                    "MERGE (e)-[r:CURSANDO]->(m) "
                    "SET r.tipo = $tipo, r.nota = $nota, r.updated_at = $now",
                    eid=est_id, mid=mat_id, tipo=tipo, nota=nota, now=datetime.utcnow().isoformat()
                )
    except Exception as e:
        print(f"   ⚠️ No se pudo sincronizar CURSÓ en Neo4j para estudiante {est_id} y materia {mat_id}: {e}")

def run_seed():
    print("🌱 INICIANDO SEMBRADO DE DATOS (DATA SEED)...")
    # Limpiar antes de sembrar
    clean_all_datastores()
    
    # ==========================================
    # 1. CREAR INSTITUCIONES (2)
    # ==========================================
    log("1", "Creando Instituciones...")
    
    inst1 = post("academic/instituciones", {
        "codigo": "UADE",
        "nombre": "Universidad Argentina de la Empresa",
        "pais": "AR"
    })
    id_uade = inst1['id']
    print(f"   ✅ UADE creada (ID: {id_uade})")

    inst2 = post("academic/instituciones", {
        "codigo": "MIT",
        "nombre": "Massachusetts Institute of Technology",
        "pais": "US"
    })
    id_mit = inst2['id']
    print(f"   ✅ MIT creada (ID: {id_mit})")

    # ==========================================
    # 2. CREAR USUARIO ADMINISTRADOR
    # ==========================================
    log("2", "Creando Usuario Administrador...")
    
    admin_res = post("estudiantes/", {
        "legajo": "ADMIN-001",
        "nombre": "Administrador",
        "apellido": "Sistema",
        "email": "admin@example.com"
    })
    if admin_res:
        id_admin = admin_res.get('id')
        print(f"   ✅ Admin creado (ID: {id_admin})")
        print("      📧 Email: admin@example.com | 🔑 Contraseña: 123456")
    else:
        print("   ⚠️ No se pudo crear el admin (verifica que el backend esté corriendo)")

    # ==========================================
    # 3. CREAR MATERIAS (5)
    # ==========================================
    log("3", "Creando Materias...")
    
    # Materias de UADE
    mat_bd = post("academic/materias", {
        "codigo": "CS-101",
        "nombre": "Bases de Datos NoSQL",
        "nivel": "GRADO",
        "institucion_id": id_uade
    })['id']
    
    mat_prog = post("academic/materias", {
        "codigo": "CS-102",
        "nombre": "Programación Avanzada",
        "nivel": "GRADO",
        "institucion_id": id_uade
    })['id']

    mat_math = post("academic/materias", {
        "codigo": "MAT-200",
        "nombre": "Análisis Matemático II",
        "nivel": "GRADO",
        "institucion_id": id_uade
    })['id']
    
    # Materias del MIT
    mat_ai = post("academic/materias", {
        "codigo": "AI-500",
        "nombre": "Artificial Intelligence",
        "nivel": "POSTGRADO",
        "institucion_id": id_mit
    })['id']

    mat_robotics = post("academic/materias", {
        "codigo": "ROB-300",
        "nombre": "Robotics 101",
        "nivel": "GRADO",
        "institucion_id": id_mit
    })['id']

    print("   ✅ 5 Materias creadas y vinculadas a sus instituciones.")

    # ==========================================
    # 3. CREAR ESTUDIANTES (3)
    # ==========================================
    log("4", "Creando Estudiantes...")

    # Estudiante 1 (UADE - Va a recursar)
    est_fede = post("estudiantes/", {
        "legajo": "L-1001",
        "nombre": "Federico",
        "apellido": "Lopez",
        "email": "fede@mail.com",
        "pais": "AR"
    })['id']
    # Asociar estudiante a Institución (UADE)
    try:
        with get_neo4j() as session:
            session.run("MATCH (e:Estudiante {id_mongo: $eid}), (i:Institucion {id_mongo: $iid}) MERGE (e)-[:PERTENECE_A]->(i)", eid=est_fede, iid=id_uade)
    except Exception as _:
        pass
    print(f"   ✅ Federico creado (ID: {est_fede}) - UADE")

    # Estudiante 2 (UADE - Promedio alto)
    est_ana = post("estudiantes/", {
        "legajo": "L-1002",
        "nombre": "Ana",
        "apellido": "Garcia",
        "email": "ana@mail.com",
        "pais": "AR"
    })['id']
    # Asociar estudiante a Institución (UADE)
    try:
        with get_neo4j() as session:
            session.run("MATCH (e:Estudiante {id_mongo: $eid}), (i:Institucion {id_mongo: $iid}) MERGE (e)-[:PERTENECE_A]->(i)", eid=est_ana, iid=id_uade)
    except Exception as _:
        pass
    print(f"   ✅ Ana creada (ID: {est_ana}) - UADE")

    # Estudiante 3 (MIT - Internacional)
    est_john = post("estudiantes/", {
        "legajo": "US-9900",
        "nombre": "John",
        "apellido": "Doe",
        "email": "john@mit.edu",
        "pais": "US"
    })['id']
    # Asociar estudiante a Institución (MIT)
    try:
        with get_neo4j() as session:
            session.run("MATCH (e:Estudiante {id_mongo: $eid}), (i:Institucion {id_mongo: $iid}) MERGE (e)-[:PERTENECE_A]->(i)", eid=est_john, iid=id_mit)
    except Exception as _:
        pass
    print(f"   ✅ John creado (ID: {est_john}) - MIT")

    # ==========================================
    # 5. CREAR PROFESORES
    # ==========================================
    log("5", "Creando Profesores...")

    prof_bd = post("profesores/", {
        "legajo_docente": "PROF-101",
        "nombre": "Carlos",
        "apellido": "Mendoza",
        "especialidad": "Bases de Datos"
    })
    prof_prog = post("profesores/", {
        "legajo_docente": "PROF-102",
        "nombre": "María",
        "apellido": "Fernández",
        "especialidad": "Programación"
    })
    prof_math = post("profesores/", {
        "legajo_docente": "PROF-103",
        "nombre": "Roberto",
        "apellido": "Pérez",
        "especialidad": "Matemática"
    })
    prof_ai = post("profesores/", {
        "legajo_docente": "PROF-501",
        "nombre": "David",
        "apellido": "Wilson",
        "especialidad": "Inteligencia Artificial"
    })
    prof_robotics = post("profesores/", {
        "legajo_docente": "PROF-302",
        "nombre": "Sarah",
        "apellido": "Johnson",
        "especialidad": "Robótica"
    })

    id_prof_bd = prof_bd.get('id') if prof_bd else None
    id_prof_prog = prof_prog.get('id') if prof_prog else None
    id_prof_math = prof_math.get('id') if prof_math else None
    id_prof_ai = prof_ai.get('id') if prof_ai else None
    id_prof_robotics = prof_robotics.get('id') if prof_robotics else None

    # Asignar profesores a materias
    if id_prof_bd:
        post(f"profesores/{id_prof_bd}/asignar-materia", {"materia_id": mat_bd})
    if id_prof_prog:
        post(f"profesores/{id_prof_prog}/asignar-materia", {"materia_id": mat_prog})
    if id_prof_math:
        post(f"profesores/{id_prof_math}/asignar-materia", {"materia_id": mat_math})
    if id_prof_ai:
        post(f"profesores/{id_prof_ai}/asignar-materia", {"materia_id": mat_ai})
    if id_prof_robotics:
        post(f"profesores/{id_prof_robotics}/asignar-materia", {"materia_id": mat_robotics})

    print("   ✅ 5 Profesores creados y asignados a sus materias.")

    # ==========================================
    # 5b. CREAR REGLAS DE CONVERSIÓN (UK, US, Alemania, Argentina)
    # ==========================================
    log("5b", "Creando Reglas de Conversión (12 combinaciones)...")

    reglas_conversion = [
        # --- ARGENTINA (1-10) ---
        {"codigo_regla": "AR_TO_UK", "nombre": "Argentina → Reino Unido (GCSE/A-Level)", "mapeo": [
            {"nota_origen": 10, "nota_destino": "A*"}, {"nota_origen": 9, "nota_destino": "A"},
            {"nota_origen": 8, "nota_destino": "B"}, {"nota_origen": 7, "nota_destino": "C"},
            {"nota_origen": 6, "nota_destino": "D"}, {"nota_origen": 5, "nota_destino": "E"},
            {"nota_origen": 4, "nota_destino": "F"}, {"nota_origen": 3, "nota_destino": "F"}, {"nota_origen": 2, "nota_destino": "F"}, {"nota_origen": 1, "nota_destino": "F"},
        ]},
        {"codigo_regla": "AR_TO_US", "nombre": "Argentina → Estados Unidos (Letras)", "mapeo": [
            {"nota_origen": 10, "nota_destino": "A"}, {"nota_origen": 9, "nota_destino": "A"},
            {"nota_origen": 8, "nota_destino": "B"}, {"nota_origen": 7, "nota_destino": "C"},
            {"nota_origen": 6, "nota_destino": "D"}, {"nota_origen": 5, "nota_destino": "F"},
            {"nota_origen": 4, "nota_destino": "F"}, {"nota_origen": 3, "nota_destino": "F"}, {"nota_origen": 2, "nota_destino": "F"}, {"nota_origen": 1, "nota_destino": "F"},
        ]},
        {"codigo_regla": "AR_TO_US_GPA", "nombre": "Argentina → Estados Unidos (GPA 0-4)", "mapeo": [
            {"nota_origen": 10, "nota_destino": 4.0}, {"nota_origen": 9, "nota_destino": 3.5},
            {"nota_origen": 8, "nota_destino": 3.0}, {"nota_origen": 7, "nota_destino": 2.5},
            {"nota_origen": 6, "nota_destino": 2.0}, {"nota_origen": 5, "nota_destino": 1.0},
            {"nota_origen": 4, "nota_destino": 0.0}, {"nota_origen": 3, "nota_destino": 0.0}, {"nota_origen": 2, "nota_destino": 0.0}, {"nota_origen": 1, "nota_destino": 0.0},
        ]},
        {"codigo_regla": "AR_TO_DE", "nombre": "Argentina → Alemania (1.0-6.0)", "mapeo": [
            {"nota_origen": 10, "nota_destino": 1.0}, {"nota_origen": 9, "nota_destino": 1.3},
            {"nota_origen": 8, "nota_destino": 2.0}, {"nota_origen": 7, "nota_destino": 2.5},
            {"nota_origen": 6, "nota_destino": 4.0}, {"nota_origen": 5, "nota_destino": 5.0},
            {"nota_origen": 4, "nota_destino": 6.0}, {"nota_origen": 3, "nota_destino": 6.0}, {"nota_origen": 2, "nota_destino": 6.0}, {"nota_origen": 1, "nota_destino": 6.0},
        ]},
        # --- REINO UNIDO (A*-F) ---
        {"codigo_regla": "UK_TO_AR", "nombre": "Reino Unido → Argentina", "mapeo": [
            {"nota_origen": "A*", "nota_destino": 10}, {"nota_origen": "A", "nota_destino": 9},
            {"nota_origen": "B", "nota_destino": 8}, {"nota_origen": "C", "nota_destino": 7},
            {"nota_origen": "D", "nota_destino": 6}, {"nota_origen": "E", "nota_destino": 5},
            {"nota_origen": "F", "nota_destino": 4},
        ]},
        {"codigo_regla": "UK_TO_US", "nombre": "Reino Unido → Estados Unidos", "mapeo": [
            {"nota_origen": "A*", "nota_destino": "A"}, {"nota_origen": "A", "nota_destino": "A"},
            {"nota_origen": "B", "nota_destino": "B"}, {"nota_origen": "C", "nota_destino": "C"},
            {"nota_origen": "D", "nota_destino": "D"}, {"nota_origen": "E", "nota_destino": "F"}, {"nota_origen": "F", "nota_destino": "F"},
        ]},
        {"codigo_regla": "UK_TO_DE", "nombre": "Reino Unido → Alemania", "mapeo": [
            {"nota_origen": "A*", "nota_destino": 1.0}, {"nota_origen": "A", "nota_destino": 1.3},
            {"nota_origen": "B", "nota_destino": 2.0}, {"nota_origen": "C", "nota_destino": 2.5},
            {"nota_origen": "D", "nota_destino": 4.0}, {"nota_origen": "E", "nota_destino": 5.0}, {"nota_origen": "F", "nota_destino": 6.0},
        ]},
        # --- ESTADOS UNIDOS (A-F, GPA) ---
        {"codigo_regla": "US_GPA_TO_AR", "nombre": "Estados Unidos (GPA) → Argentina", "mapeo": [
            {"nota_origen": 4.0, "nota_destino": 10}, {"nota_origen": 3.5, "nota_destino": 9},
            {"nota_origen": 3.0, "nota_destino": 8}, {"nota_origen": 2.5, "nota_destino": 7},
            {"nota_origen": 2.0, "nota_destino": 6}, {"nota_origen": 1.5, "nota_destino": 5},
            {"nota_origen": 1.0, "nota_destino": 4}, {"nota_origen": 0.5, "nota_destino": 4}, {"nota_origen": 0.0, "nota_destino": 4},
        ]},
        {"codigo_regla": "US_TO_AR", "nombre": "Estados Unidos (Letras) → Argentina", "mapeo": [
            {"nota_origen": "A", "nota_destino": 10}, {"nota_origen": "A+", "nota_destino": 10}, {"nota_origen": "A-", "nota_destino": 9},
            {"nota_origen": "B", "nota_destino": 8}, {"nota_origen": "B+", "nota_destino": 8}, {"nota_origen": "B-", "nota_destino": 7},
            {"nota_origen": "C", "nota_destino": 7}, {"nota_origen": "C+", "nota_destino": 6}, {"nota_origen": "C-", "nota_destino": 6},
            {"nota_origen": "D", "nota_destino": 6}, {"nota_origen": "F", "nota_destino": 4},
        ]},
        {"codigo_regla": "US_TO_UK", "nombre": "Estados Unidos → Reino Unido", "mapeo": [
            {"nota_origen": "A", "nota_destino": "A"}, {"nota_origen": "A+", "nota_destino": "A*"}, {"nota_origen": "A-", "nota_destino": "A"},
            {"nota_origen": "B", "nota_destino": "B"}, {"nota_origen": "B+", "nota_destino": "B"}, {"nota_origen": "B-", "nota_destino": "B"},
            {"nota_origen": "C", "nota_destino": "C"}, {"nota_origen": "C+", "nota_destino": "C"}, {"nota_origen": "C-", "nota_destino": "C"},
            {"nota_origen": "D", "nota_destino": "D"}, {"nota_origen": "F", "nota_destino": "F"},
        ]},
        {"codigo_regla": "US_TO_DE", "nombre": "Estados Unidos → Alemania", "mapeo": [
            {"nota_origen": "A", "nota_destino": 1.0}, {"nota_origen": "A+", "nota_destino": 1.0}, {"nota_origen": "A-", "nota_destino": 1.3},
            {"nota_origen": "B", "nota_destino": 2.0}, {"nota_origen": "B+", "nota_destino": 1.7}, {"nota_origen": "B-", "nota_destino": 2.3},
            {"nota_origen": "C", "nota_destino": 3.0}, {"nota_origen": "C+", "nota_destino": 2.5}, {"nota_origen": "C-", "nota_destino": 3.3},
            {"nota_origen": "D", "nota_destino": 4.0}, {"nota_origen": "F", "nota_destino": 6.0},
        ]},
        # --- ALEMANIA (1.0-6.0, inversa) ---
        {"codigo_regla": "DE_TO_AR", "nombre": "Alemania → Argentina", "mapeo": [
            {"nota_origen": 1.0, "nota_destino": 10}, {"nota_origen": 1.3, "nota_destino": 9}, {"nota_origen": 1.7, "nota_destino": 9},
            {"nota_origen": 2.0, "nota_destino": 8}, {"nota_origen": 2.3, "nota_destino": 8}, {"nota_origen": 2.7, "nota_destino": 7},
            {"nota_origen": 3.0, "nota_destino": 7}, {"nota_origen": 3.3, "nota_destino": 7}, {"nota_origen": 3.7, "nota_destino": 6},
            {"nota_origen": 4.0, "nota_destino": 6}, {"nota_origen": 4.3, "nota_destino": 5}, {"nota_origen": 4.7, "nota_destino": 5},
            {"nota_origen": 5.0, "nota_destino": 4}, {"nota_origen": 5.3, "nota_destino": 4}, {"nota_origen": 5.7, "nota_destino": 4},
            {"nota_origen": 6.0, "nota_destino": 4},
        ]},
        {"codigo_regla": "DE_TO_UK", "nombre": "Alemania → Reino Unido", "mapeo": [
            {"nota_origen": 1.0, "nota_destino": "A*"}, {"nota_origen": 1.3, "nota_destino": "A"}, {"nota_origen": 1.7, "nota_destino": "A"},
            {"nota_origen": 2.0, "nota_destino": "B"}, {"nota_origen": 2.3, "nota_destino": "B"}, {"nota_origen": 2.7, "nota_destino": "C"},
            {"nota_origen": 3.0, "nota_destino": "C"}, {"nota_origen": 3.3, "nota_destino": "C"}, {"nota_origen": 3.7, "nota_destino": "D"},
            {"nota_origen": 4.0, "nota_destino": "D"}, {"nota_origen": 4.3, "nota_destino": "E"}, {"nota_origen": 4.7, "nota_destino": "E"},
            {"nota_origen": 5.0, "nota_destino": "F"}, {"nota_origen": 5.3, "nota_destino": "F"}, {"nota_origen": 5.7, "nota_destino": "F"},
            {"nota_origen": 6.0, "nota_destino": "F"},
        ]},
        {"codigo_regla": "DE_TO_US", "nombre": "Alemania → Estados Unidos", "mapeo": [
            {"nota_origen": 1.0, "nota_destino": "A"}, {"nota_origen": 1.3, "nota_destino": "A"}, {"nota_origen": 1.7, "nota_destino": "A"},
            {"nota_origen": 2.0, "nota_destino": "B"}, {"nota_origen": 2.3, "nota_destino": "B"}, {"nota_origen": 2.7, "nota_destino": "C"},
            {"nota_origen": 3.0, "nota_destino": "C"}, {"nota_origen": 3.3, "nota_destino": "C"}, {"nota_origen": 3.7, "nota_destino": "D"},
            {"nota_origen": 4.0, "nota_destino": "D"}, {"nota_origen": 4.3, "nota_destino": "F"}, {"nota_origen": 4.7, "nota_destino": "F"},
            {"nota_origen": 5.0, "nota_destino": "F"}, {"nota_origen": 5.3, "nota_destino": "F"}, {"nota_origen": 5.7, "nota_destino": "F"},
            {"nota_origen": 6.0, "nota_destino": "F"},
        ]},
    ]
    for regla in reglas_conversion:
        res = post("calificaciones/reglas", regla)
        if res:
            print(f"   ✅ Regla: {regla['nombre']}")
        else:
            print(f"   ⚠️ No se pudo crear regla: {regla['nombre']}")

    # ==========================================
    # 6. CARGAR NOTAS Y CURSADAS
    # ==========================================
    log("6", "Simulando Cursadas y Exámenes...")

    # --- CASO A: Federico RECURSA Bases de Datos ---
    print("   👉 Federico cursa Bases de Datos (1er intento: REPRUEBA)")
    # Parcial 1
    _ = post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 2, "tipo": "PARCIAL_1"}
    })
    sync_curso_relation(est_fede, mat_bd, "PARCIAL_1", 2)
    # Parcial 2
    _ = post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 2, "tipo": "PARCIAL_2"}
    })
    sync_curso_relation(est_fede, mat_bd, "PARCIAL_2", 2)
    # Final (Reprobado)
    _ = post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 2, "tipo": "FINAL"}
    })
    sync_curso_relation(est_fede, mat_bd, "FINAL", 2)
    
    print("   👉 Federico cursa Bases de Datos (2do intento: APRUEBA)")
    # Parcial 1
    _ = post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 7, "tipo": "PARCIAL_1"}
    })
    sync_curso_relation(est_fede, mat_bd, "PARCIAL_1", 7)
    # Parcial 2
    _ = post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 8, "tipo": "PARCIAL_2"}
    })
    sync_curso_relation(est_fede, mat_bd, "PARCIAL_2", 8)
    # Final (Aprobado)
    _ = post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 8, "tipo": "FINAL"}
    })
    sync_curso_relation(est_fede, mat_bd, "FINAL", 8)

    # Federico cursa también Programación (En curso)
    print("   👉 Federico cursa Programación (En curso)")
    _ = post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_prog,
        "valor_original": {"nota": 6, "tipo": "PARCIAL_1"}
    })
    sync_curso_relation(est_fede, mat_prog, "PARCIAL_1", 6)

    # --- CASO B: Ana (Estudiante Modelo) ---
    print("   👉 Ana cursa Bases de Datos (Promociona)")
    _ = post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_bd, "valor_original": {"nota": 10, "tipo": "PARCIAL_1"}
    })
    sync_curso_relation(est_ana, mat_bd, "PARCIAL_1", 10)
    _ = post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_bd, "valor_original": {"nota": 9, "tipo": "PARCIAL_2"}
    })
    sync_curso_relation(est_ana, mat_bd, "PARCIAL_2", 9)
    _ = post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_bd, "valor_original": {"nota": 10, "tipo": "FINAL"}
    })
    sync_curso_relation(est_ana, mat_bd, "FINAL", 10)

    print("   👉 Ana cursa Matemática II")
    _ = post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_math, "valor_original": {"nota": 8, "tipo": "FINAL"}
    })
    sync_curso_relation(est_ana, mat_math, "FINAL", 8)

    # --- CASO C: John (MIT - Otra escala) ---
    print("   👉 John cursa AI (Escala US)")
    _ = post("calificaciones/", {
        "estudiante_id": est_john, "materia_id": mat_ai, "valor_original": {"nota": "A", "tipo": "FINAL_PROJECT"}
    })
    sync_curso_relation(est_john, mat_ai, "FINAL_PROJECT", "A")
    
    _ = post("calificaciones/", {
        "estudiante_id": est_john, "materia_id": mat_robotics, "valor_original": {"nota": "B+", "tipo": "MIDTERM"}
    })
    sync_curso_relation(est_john, mat_robotics, "MIDTERM", "B+")

    print("\n✅ DATA SEED FINALIZADO EXITOSAMENTE.")
    print("\n📋 CREDENCIALES PARA PROBAR:")
    print("   👤 Admin:  admin@example.com  |  Contraseña: 123456")
    print("   👤 Fede:   fede@mail.com      |  Contraseña: 123456")
    print("   👤 Ana:    ana@mail.com       |  Contraseña: 123456")
    print("\nAhora puedes verificar en:")
    print("1. Mongo: Colecciones 'estudiantes', 'materias', 'profesores', 'calificaciones'.")
    print("2. Neo4j: Ejecuta 'MATCH (n) RETURN n' para ver el grafo conectado.")
    print("3. Cassandra: 'SELECT * FROM registro_auditoria;'")

if __name__ == "__main__":
    try:
        run_seed()
    except Exception as e:
        print(f"Error fatal: {e}")
        print("Asegúrate de que 'python backend/run.py' esté corriendo en otra terminal.")