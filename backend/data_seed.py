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
    # 2. CREAR MATERIAS (5)
    # ==========================================
    log("2", "Creando Materias...")
    
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
    log("3", "Creando Estudiantes...")

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
    # 4. CARGAR NOTAS Y CURSADAS
    # ==========================================
    log("4", "Simulando Cursadas y Exámenes...")

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
    print("Ahora puedes verificar en:")
    print("1. Mongo: Colecciones 'estudiantes', 'materias', 'calificaciones'.")
    print("2. Neo4j: Ejecuta 'MATCH (n) RETURN n' para ver el grafo conectado.")
    print("3. Cassandra: 'SELECT * FROM registro_auditoria;'")

if __name__ == "__main__":
    try:
        run_seed()
    except Exception as e:
        print(f"Error fatal: {e}")
        print("Asegúrate de que 'python backend/run.py' esté corriendo en otra terminal.")