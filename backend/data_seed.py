import requests
import json
import time

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

def run_seed():
    print("🌱 INICIANDO SEMBRADO DE DATOS (DATA SEED)...")
    
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
    # 3. CREAR ESTUDIANTES (5)
    # ==========================================
    log("3", "Creando Estudiantes...")

    # Usuarios de demostración
    est_demo = post("estudiantes/", {
        "legajo": "DEMO-001",
        "nombre": "Student",
        "apellido": "Demo",
        "email": "student@example.com",
        "pais": "AR"
    })['id']
    print(f"   ✅ Student Demo creado (ID: {est_demo})")

    est_admin = post("estudiantes/", {
        "legajo": "ADMIN-001",
        "nombre": "Admin",
        "apellido": "User",
        "email": "admin@example.com",
        "pais": "AR"
    })['id']
    print(f"   ✅ Admin Demo creado (ID: {est_admin})")

    # Estudiante 1 (UADE - Va a recursar)
    est_fede = post("estudiantes/", {
        "legajo": "L-1001",
        "nombre": "Federico",
        "apellido": "Lopez",
        "email": "fede@mail.com",
        "pais": "AR"
    })['id']
    print(f"   ✅ Federico creado (ID: {est_fede}) - UADE")

    # Estudiante 2 (UADE - Promedio alto)
    est_ana = post("estudiantes/", {
        "legajo": "L-1002",
        "nombre": "Ana",
        "apellido": "Garcia",
        "email": "ana@mail.com",
        "pais": "AR"
    })['id']
    print(f"   ✅ Ana creada (ID: {est_ana}) - UADE")

    # Estudiante 3 (MIT - Internacional)
    est_john = post("estudiantes/", {
        "legajo": "US-9900",
        "nombre": "John",
        "apellido": "Doe",
        "email": "john@mit.edu",
        "pais": "US"
    })['id']
    print(f"   ✅ John creado (ID: {est_john}) - MIT")

    # ==========================================
    # 4. CARGAR NOTAS Y CURSADAS
    # ==========================================
    log("4", "Simulando Cursadas y Exámenes...")

    # --- CASO A: Federico RECURSA Bases de Datos ---
    print("   👉 Federico cursa Bases de Datos (1er intento: REPRUEBA)")
    # Parcial 1
    post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 2, "tipo": "PARCIAL_1"}
    })
    # Parcial 2
    post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 2, "tipo": "PARCIAL_2"}
    })
    # Final (Reprobado)
    post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 2, "tipo": "FINAL"}
    })
    
    print("   👉 Federico cursa Bases de Datos (2do intento: APRUEBA)")
    # Parcial 1
    post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 7, "tipo": "PARCIAL_1"}
    })
    # Parcial 2
    post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 8, "tipo": "PARCIAL_2"}
    })
    # Final (Aprobado)
    post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_bd,
        "valor_original": {"nota": 8, "tipo": "FINAL"}
    })

    # Federico cursa también Programación (En curso)
    print("   👉 Federico cursa Programación (En curso)")
    post("calificaciones/", {
        "estudiante_id": est_fede,
        "materia_id": mat_prog,
        "valor_original": {"nota": 6, "tipo": "PARCIAL_1"}
    })

    # --- CASO B: Ana (Estudiante Modelo) ---
    print("   👉 Ana cursa Bases de Datos (Promociona)")
    post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_bd, "valor_original": {"nota": 10, "tipo": "PARCIAL_1"}
    })
    post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_bd, "valor_original": {"nota": 9, "tipo": "PARCIAL_2"}
    })
    post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_bd, "valor_original": {"nota": 10, "tipo": "FINAL"}
    })

    print("   👉 Ana cursa Matemática II")
    post("calificaciones/", {
        "estudiante_id": est_ana, "materia_id": mat_math, "valor_original": {"nota": 8, "tipo": "FINAL"}
    })

    # --- CASO C: John (MIT - Otra escala) ---
    print("   👉 John cursa AI (Escala US)")
    post("calificaciones/", {
        "estudiante_id": est_john, "materia_id": mat_ai, "valor_original": {"nota": "A", "tipo": "FINAL_PROJECT"}
    })
    
    post("calificaciones/", {
        "estudiante_id": est_john, "materia_id": mat_robotics, "valor_original": {"nota": "B+", "tipo": "MIDTERM"}
    })

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