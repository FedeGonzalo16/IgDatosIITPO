import pymongo
import random
import datetime
from neo4j import GraphDatabase

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================

# MongoDB
MONGO_URI = "mongodb://root:estudiantes2026@localhost:27017/?authSource=admin"
try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client["edugrade_global"]
    col_estudiantes = db["estudiantes"]
    col_instituciones = db["instituciones"]
    col_calificaciones = db["calificaciones"]
except Exception as e:
    print(f"❌ Error Mongo: {e}")
    exit()

# Neo4j
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "grafos2026")
try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
except Exception as e:
    print(f"❌ Error Neo4j: {e}")
    exit()

# ==========================================
# 2. LÓGICA DE CARGA EN GRAFO (Cypher Complejo)
# ==========================================

def cargar_grafo_completo(tx, datos):
    query = """
    // 1. Nodo Estudiante
    MERGE (e:Estudiante {id: $sid})
    SET e.nombre = $nombre, 
        e.apellido = $apellido,
        e.nombre_completo = $nombre + ' ' + $apellido, 
        e.dni = $dni,
        e.nacionalidad = $nacionalidad
    

    // 2. Nodo Institución (Para agrupar métricas por colegio)
    MERGE (i:Institucion {id: $inst_id})
    SET i.nombre = $inst_nombre,
        i.pais = $inst_pais,
        i.sistema = $inst_sistema,
        i.tipo = $inst_tipo

    // 3. Relación: El estudiante asiste a la institución
    MERGE (e)-[a:ASISTE_A]->(i)
    SET a.desde = $fecha_ingreso,
        a.activo = true

    // 4. Nodo Materia (Vinculado a su sistema original)
    MERGE (m:Materia {
    nombre: $mat_nombre,
    institucion_id: $inst_id
            })
        ON CREATE SET 
            m.codigo = $mat_codigo,
            m.sistema = $inst_sistema

    // 5. Relación: La materia pertenece a esa institución
    MERGE (m)-[:PERTENECE_A]->(i)

    // 6. Relación CRÍTICA: La cursada (Historial académico)
    MERGE (e)-[c:CURSO {id_evento: $calif_id}]->(m)
    SET c.nota_valor = $nota_valor,
        c.nota_escala = $nota_escala,
        c.estado = $estado,
        c.anio = $anio,
        c.oportunidad = $oportunidad, // Ej: 1 (Original), 2 (Recursada)
        c.fecha = datetime($fecha_iso)
    """
    
    tx.run(query, **datos) # Pasamos el diccionario completo como kwargs

# ==========================================
# 3. GENERADORES DE DATOS
# ==========================================

CANTIDAD_ESTUDIANTES = 200
NOMBRES = ["Ana", "Lucas", "Sofia", "Mateo", "Emma", "Liam", "Olivia", "Noah", "Valentina", "Kevin"]
APELLIDOS = ["Perez", "Smith", "Muller", "Garcia", "Johnson", "Schmidt", "Lopez", "Brown", "Chen"]
MATERIAS_BASE = ["Matemática", "Historia", "Física", "Química", "Literatura", "Programación", "Economía", "Arte"]

# Sistemas Educativos con reglas simples
SISTEMAS = {
    "AR": {"pais": "Argentina", "tipo_nota": "Numérica", "min": 1, "max": 10, "pass": 6},
    "UK": {"pais": "Reino Unido", "tipo_nota": "Letra", "vals": ["A*", "A", "B", "C", "D", "E", "F"], "pass_idx": 3}, # C o mejor aprueba
    "US": {"pais": "Estados Unidos", "tipo_nota": "GPA", "min": 0.0, "max": 4.0, "pass": 2.0}
}

def generar_nota(sistema_code):
    sys_conf = SISTEMAS[sistema_code]
    aprobado = random.random() > 0.2 # 80% aprueba
    
    if sistema_code == "AR":
        val = random.randint(6, 10) if aprobado else random.randint(1, 5)
        return val, "Numérica", aprobado
    elif sistema_code == "UK":
        vals = sys_conf["vals"]
        # Si aprueba, elige entre los primeros 4 (A*-C), sino el resto
        val = random.choice(vals[:4]) if aprobado else random.choice(vals[4:])
        return val, "Letra", aprobado
    elif sistema_code == "US":
        val = round(random.uniform(2.0, 4.0), 1) if aprobado else round(random.uniform(0.0, 1.9), 1)
        return val, "GPA", aprobado
    return 0, "Unknown", False

def main():
    print("🚀 Iniciando carga FULL GRAFO (Estudiantes + Instituciones + Relaciones complejas)...")
    
    # 1. Limpieza
    col_estudiantes.drop()
    col_instituciones.drop()
    col_calificaciones.drop()
    with neo4j_driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

    # 2. Crear Instituciones
    instituciones = []
    print("🏗️  Construyendo Instituciones...")
    for i, (code, data) in enumerate(SISTEMAS.items()):
        # Creamos 2 instituciones por sistema
        for j in range(2):
            inst = {
                "nombre": f"{data['pais']} School {j+1}",
                "pais": data['pais'],
                "sistema_educativo": code,
                "tipo": random.choice(["Secundaria", "Universidad"]),
                "ciudad": f"Ciudad {code}-{j}"
            }
            res = col_instituciones.insert_one(inst)
            inst["_id"] = str(res.inserted_id) # Guardamos ID string para usarlo
            instituciones.append(inst)

    # 3. Crear Alumnos y Trayectorias
    print(f"👥  Simulando vida académica de {CANTIDAD_ESTUDIANTES} estudiantes...")
    
    with neo4j_driver.session() as session:
        for _ in range(CANTIDAD_ESTUDIANTES):
            
            # A) Datos Personales
            nombre = random.choice(NOMBRES)
            apellido = random.choice(APELLIDOS)
            nacionalidad = random.choice(list(SISTEMAS.keys()))
            dni = str(random.randint(10000000, 99999999))
            
            estudiante_mongo = {
                "nombre": nombre,
                "apellido": apellido,
                "dni": dni,
                "nacionalidad": nacionalidad,
                "email": f"{nombre.lower()}.{apellido.lower()}@edu.com",
                "fecha_alta": datetime.datetime.utcnow()
            }
            res_est = col_estudiantes.insert_one(estudiante_mongo)
            student_id = str(res_est.inserted_id)

            # B) Trayectoria (Asignar materias)
            inst_actual = random.choice(instituciones) # Elige una escuela
            cant_materias = random.randint(3, 8)
            
            for k in range(cant_materias):
                materia_nombre = random.choice(MATERIAS_BASE)
                materia_codigo = f"{materia_nombre[:3].upper()}-{inst_actual['sistema_educativo']}10{k}"
                
                # Simular Nota
                nota_val, nota_tipo, is_aprobado = generar_nota(inst_actual["sistema_educativo"])
                
                # Simular Recurso (Oportunidad)
                oportunidad = 1
                if not is_aprobado and random.random() < 0.5:
                     oportunidad = 2 # Es un recursante

                anio_cursada = 2024
                
                # 1. Guardar en MongoDB (Evidencia)
                calif_doc = {
                    "student_id": student_id,
                    "institucion_id": inst_actual["_id"],
                    "materia": {"nombre": materia_nombre, "codigo": materia_codigo},
                    "nota": {"valor": nota_val, "tipo": nota_tipo},
                    "estado": "APROBADO" if is_aprobado else "REPROBADO",
                    "fecha": datetime.datetime.utcnow()
                }
                res_calif = col_calificaciones.insert_one(calif_doc)

                # 2. Preparar datos para Neo4j (Grafo Rico)
                datos_grafo = {
                    "sid": student_id,
                    "nombre": nombre,
                    "apellido": apellido,
                    "dni": dni,
                    "nacionalidad": nacionalidad,
                    "email": estudiante_mongo["email"],
                    
                    "inst_id": inst_actual["_id"],
                    "inst_nombre": inst_actual["nombre"],
                    "inst_pais": inst_actual["pais"],
                    "inst_sistema": inst_actual["sistema_educativo"],
                    "inst_tipo": inst_actual["tipo"],
                    "fecha_ingreso": "2024-03-01", # Simplificado
                    
                    "mat_codigo": materia_codigo,
                    "mat_nombre": materia_nombre,
                    
                    "calif_id": str(res_calif.inserted_id), # Link único entre Mongo y Neo
                    "nota_valor": str(nota_val),
                    "nota_escala": nota_tipo,
                    "estado": "APROBADO" if is_aprobado else "REPROBADO",
                    "anio": anio_cursada,
                    "oportunidad": oportunidad,
                    "fecha_iso": datetime.datetime.utcnow().isoformat()
                }

                # Ejecutar carga
                session.execute_write(cargar_grafo_completo, datos_grafo)

    print(f"✅ Carga completa.")
    neo4j_driver.close()
    mongo_client.close()

if __name__ == "__main__":
    main()