import requests
import json
import random
import time

# --- CONFIGURACIÓN DE PUERTOS (APIs Python) ---
# Estos puertos vienen definidos en los .py al final de cada archivo (app.run)
API_MONGO = "http://localhost:5000/api/v1"
API_NEO4J = "http://localhost:5001/api/neo4j"
API_REDIS = "http://localhost:5002/api/redis"
API_CASSANDRA = "http://localhost:5003/api/cassandra"

def print_step(msg):
    print(f"\n{'='*50}\n{msg}\n{'='*50}")

def check(response, action):
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"[OK] {action}: {json.dumps(data, indent=2)}")
        return data
    else:
        print(f"[ERROR] {action}: {response.status_code} - {response.text}")
        return None

def run_loader():
    print_step("1. CREANDO INSTITUCIÓN (Mongo + Neo4j)")
    
    # 1.1 Crear en Mongo
    inst_data = {
        "codigo": "UADE-MSG",
        "nombre": "Universidad Argentina de la Empresa",
        "pais": "AR",
        "region": "CABA",
        "email": "info@uade.edu.ar"
    }
    resp = requests.post(f"{API_MONGO}/instituciones", json=inst_data)
    inst_mongo = check(resp, "Institución en Mongo")
    
    if not inst_mongo: return
    inst_id = inst_mongo['id']

    # 1.2 Replicar en Neo4j (Para mantener el grafo sincronizado)
    neo_inst_data = {
        "id_mongo": inst_id,
        "codigo": inst_data['codigo'],
        "nombre": inst_data['nombre'],
        "pais": inst_data['pais']
    }
    check(requests.post(f"{API_NEO4J}/instituciones", json=neo_inst_data), "Institución en Neo4j")

    # ---------------------------------------------------------
    
    print_step("2. CREANDO MATERIA (Mongo + Neo4j)")
    
    # 2.1 Crear en Mongo
    mat_data = {
        "codigo": "BD-NOSQL-2026",
        "nombre": "Bases de Datos NoSQL",
        "nivel": "UNIVERSITARIO",
        "año_cursada": 3,
        "institucion": inst_id
    }
    resp = requests.post(f"{API_MONGO}/materias", json=mat_data)
    mat_mongo = check(resp, "Materia en Mongo")
    
    if not mat_mongo: return
    mat_id = mat_mongo['id']

    # 2.2 Replicar en Neo4j y vincular a la institución
    neo_mat_data = {
        "id_mongo": mat_id,
        "codigo": mat_data['codigo'],
        "nombre": mat_data['nombre'],
        "nivel": mat_data['nivel'],
        "año_cursada": mat_data['año_cursada'],
        "institucion_id_mongo": inst_id  # Clave para la relación
    }
    check(requests.post(f"{API_NEO4J}/materias", json=neo_mat_data), "Materia en Neo4j")

    # ---------------------------------------------------------

    print_step("3. CREANDO ESTUDIANTE (Mongo + Neo4j + Redis Session)")
    
    # 3.1 Crear en Mongo
    legajo = f"L-{random.randint(10000, 99999)}"
    est_data = {
        "legajo": legajo,
        "nombre": "Martin",
        "apellido": "Gomez",
        "documento": {"tipo": "DNI", "numero": "30444555", "pais": "AR"},
        "email": "martin.gomez@mail.com"
    }
    resp = requests.post(f"{API_MONGO}/estudiantes", json=est_data)
    est_mongo = check(resp, "Estudiante en Mongo")
    
    if not est_mongo: return
    est_id = est_mongo['id']

    # 3.2 Replicar en Neo4j
    neo_est_data = {
        "id_mongo": est_id,
        "legajo": legajo,
        "nombre": est_data['nombre'],
        "apellido": est_data['apellido'],
        "pais": "AR"
    }
    check(requests.post(f"{API_NEO4J}/estudiantes", json=neo_est_data), "Estudiante en Neo4j")
    
    # 3.3 Crear Sesión en Redis (Simulación de Login)
    redis_session_data = {
        "estudiante_id_mongo": est_id,
        "legajo": legajo,
        "nombre": est_data['nombre'],
        "apellido": est_data['apellido'],
        "email": est_data['email']
    }
    check(requests.post(f"{API_REDIS}/sesiones", json=redis_session_data), "Sesión en Redis")

    # ---------------------------------------------------------
    
    print_step("4. VINCULACIÓN ACADÉMICA (Neo4j)")
    
    # 4.1 Inscribir estudiante a materia (Relación INSCRIPTO_EN)
    inscripcion_data = {
        "estudiante_id_mongo": est_id,
        "materia_id_mongo": mat_id
    }
    check(requests.post(f"{API_NEO4J}/inscripciones", json=inscripcion_data), "Inscripción en Neo4j")
    
    # 4.2 Vincular estudiante a institución (Relación ESTUDIA_EN)
    estudia_data = {
        "institucion_id_mongo": inst_id
    }
    check(requests.post(f"{API_NEO4J}/estudiantes/{est_id}/institucion", json=estudia_data), "Vinculación Estudiante-Institución")

    # ---------------------------------------------------------

    print_step("5. REGLAS DE CONVERSIÓN (Mongo -> Redis)")
    
    # Crear regla. El endpoint de Mongo se encarga de guardarla en Mongo 
    # y también intenta cachearla en Redis si está disponible.
    regla_data = {
        "codigo_regla": "AR-US-2026",
        "sistema_origen": "AR",
        "sistema_destino": "US",
        "mapeo": [
            {"nota_origen": "10", "nota_destino": "A+"},
            {"nota_origen": "9", "nota_destino": "A"},
            {"nota_origen": "8", "nota_destino": "B"},
            {"nota_origen": "7", "nota_destino": "C"},
            {"nota_origen": "4", "nota_destino": "D"},
            {"nota_origen": "2", "nota_destino": "F"}
        ]
    }
    resp = requests.post(f"{API_MONGO}/reglas-conversion", json=regla_data)
    regla_mongo = check(resp, "Regla Conversión")
    if not regla_mongo: return
    regla_id = regla_mongo['id']

    # ---------------------------------------------------------

    print_step("6. REGISTRAR CALIFICACIÓN (Mongo -> Trigger Interno -> Neo4j & Cassandra)")
    
    # Al postear aquí, tu código `endpoint-mongo.py` internamente:
    # 1. Guarda en Mongo.
    # 2. Crea nodo Calificacion en Neo4j y relaciones.
    # 3. Escribe en Cassandra (Audit y Analytics).
    calif_data = {
        "estudiante_id": est_id,
        "materia_id": mat_id,
        "valor_original": {"nota": 9, "tipo": "FINAL"},
        "anio_lectivo": 2026,
        "created_by": "profesor_api"
    }
    resp = requests.post(f"{API_MONGO}/calificaciones", json=calif_data)
    calif_mongo = check(resp, "Calificación Registrada")
    
    if not calif_mongo: return
    calif_id = calif_mongo['id']

    # ---------------------------------------------------------

    print_step("7. APLICAR CONVERSIÓN (Mongo + Redis + Cassandra)")
    
    # Esto usa Redis para buscar la regla, actualiza Mongo y escribe auditoría en Cassandra
    conv_data = {
        "calificacion_id_mongo": calif_id, # Nota: tu API Redis espera este nombre de campo
        "codigo_regla": "AR-US-2026",
        "convertido_por": "sistema_auto"
    }
    # Llamamos a la API de REDIS para aplicar la conversión (según tu arquitectura)
    # OJO: Tu endpoint `aplicar_conversion` está en `api_redis.py`
    check(requests.post(f"{API_REDIS}/conversiones/aplicar", json=conv_data), "Conversión Aplicada")

    print_step("CARGA FINALIZADA EXITOSAMENTE")

if __name__ == "__main__":
    try:
        run_loader()
    except requests.exceptions.ConnectionError as e:
        print("\n[ERROR CRÍTICO] No se pudo conectar a una de las APIs.")
        print("Asegúrate de que los 4 scripts de Python estén corriendo en terminales separadas:")
        print("1. python endpoint-mongo.py  (Puerto 5000)")
        print("2. python api_neo4j.py       (Puerto 5001)")
        print("3. python api_redis.py       (Puerto 5002)")
        print("4. python api_cassandra.py   (Puerto 5003)")
        print(f"Detalle del error: {e}")