import random
import uuid
import time
from datetime import datetime
from faker import Faker
from pymongo import MongoClient
from cassandra.cluster import Cluster
from neo4j import GraphDatabase

# Configuración
fake = Faker()
TOTAL_RECORDS = 1_000_000
BATCH_SIZE = 5000 

def generate_grade_data():
    country = random.choice(['UK', 'US', 'DE', 'AR'])
    student_id = str(uuid.uuid4())
    
    # Lógica según requerimientos de escalas 
    if country == 'UK':
        original_grade = random.choice(['A*', 'A', 'B', 'C', 'D', 'E', 'F'])
        metadata = {"type": "GCSE", "component": "Exam"}
    elif country == 'US':
        original_grade = round(random.uniform(0.0, 4.0), 2)
        metadata = {"credits": random.choice([3, 4]), "weighted": False}
    elif country == 'DE':
        original_grade = round(random.uniform(1.0, 6.0), 1)
        metadata = {"level": "Gymnasium"}
    else: # AR
        original_grade = random.randint(1, 10)
        metadata = {"instancia": "Febrero", "aprobado": original_grade >= 4}

    return {
        "student_id": student_id,
        "country": country,
        "subject": fake.job(), # Simula materia
        "grade": original_grade,
        "metadata": metadata,
        "timestamp": datetime.now()
    }

# --- FUNCIONES DE CARGA ---

def load_data():
    # Conexiones
    mongo_client = MongoClient('mongodb://localhost:27017/')
    mongo_db = mongo_client['edugrade']
    
    cassandra_cluster = Cluster(['127.0.0.1'])
    cassandra_session = cassandra_cluster.connect('edugrade')
    cass_query = cassandra_session.prepare("INSERT INTO audit_log (id, student_id, country, grade, ts) VALUES (uuid(), ?, ?, ?, ?)")

    neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

    print(f"--- Iniciando carga masiva de {TOTAL_RECORDS} registros ---")
    start_time = time.time()
    
    current_batch = []
    for i in range(1, TOTAL_RECORDS + 1):
        current_batch.append(generate_grade_data())
        
        if i % BATCH_SIZE == 0:
            # 1. MongoDB (RF1) [cite: 13, 171]
            mongo_db.grades.insert_many(current_batch)
            
            # 2. Cassandra (RF5) [cite: 20, 244]
            for item in current_batch:
                cassandra_session.execute_async(cass_query, (item['student_id'], item['country'], str(item['grade']), item['timestamp']))
            
            # 3. Neo4j (RF3) [cite: 16, 208]
            with neo4j_driver.session() as session:
                session.run("UNWIND $batch AS item MERGE (s:Student {id: item.student_id}) CREATE (s)-[:STUDIED {grade: item.grade}]->(:Subject {name: item.subject})", batch=current_batch)
            
            print(f"Progreso: {i} registros...")
            current_batch = []

    end_time = time.time()
    print(f"\nCarga finalizada en {round(end_time - start_time, 2)} segundos.")

    # --- VERIFICACIÓN (COUNTS) ---
    print("\n--- VERIFICACIÓN DE REGISTROS ---")
    
    # Mongo Count
    m_count = mongo_db.grades.count_documents({})
    print(f"MongoDB (Calificaciones Originales): {m_count} documentos.") 

    # Cassandra Count
    c_count = cassandra_session.execute("SELECT COUNT(*) FROM audit_log").one()
    print(f"Cassandra (Auditoría Inmutable): {c_count} filas.") 

    # Neo4j Count
    with neo4j_driver.session() as session:
        n_count = session.run("MATCH ()-[r:STUDIED]->() RETURN count(r) as c").single()['c']
        print(f"Neo4j (Relaciones Académicas): {n_count} relaciones.") 

    mongo_client.close()
    cassandra_cluster.shutdown()
    neo4j_driver.close()

if __name__ == "__main__":
    load_data()