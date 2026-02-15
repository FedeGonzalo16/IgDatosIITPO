import os
from pymongo import MongoClient
from neo4j import GraphDatabase
import redis
from cassandra.cluster import Cluster

# --- 1. MONGODB ---
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:estudiantes2026@localhost:27017/?authSource=admin')
mongo_client = None
mongo_db = None

# Intentar conexión con autenticación
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')
    mongo_db = mongo_client['edugrade_global']
    print("[INFO] MongoDB conectado exitosamente con autenticación")
except Exception as e:
    print(f"[WARNING] Fallo de autenticación con MongoDB: {e}")
    print("[INFO] Intentando conexión sin autenticación (solo para desarrollo)...")
    # Fallback: intentar sin autenticación (solo para desarrollo)
    try:
        MONGO_URI_NO_AUTH = 'mongodb://localhost:27017/'
        mongo_client = MongoClient(MONGO_URI_NO_AUTH, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ping')
        mongo_db = mongo_client['edugrade_global']
        print("[INFO] MongoDB conectado sin autenticación (modo desarrollo)")
        print("[WARNING] Para producción, configura correctamente las credenciales en docker-compose.yaml")
    except Exception as e2:
        print(f"[ERROR] No se pudo conectar a MongoDB: {e2}")
        print("[INFO] Verifica que MongoDB esté corriendo:")
        print("  - docker ps (debe mostrar edugrade_mongo)")
        print("  - docker-compose up -d mongodb (si no está corriendo)")
        print("  - Verifica las credenciales en docker-compose.yaml")
        raise ConnectionError("MongoDB no está disponible. Verifica la conexión y credenciales.")

# --- 2. NEO4J ---
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASS = os.getenv('NEO4J_PASS', 'grafos2026')
neo4j_driver = None
try:
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    # Verificar conexión
    neo4j_driver.verify_connectivity()
    print("[INFO] Neo4j conectado exitosamente")
except Exception as e:
    print(f"[WARNING] No se pudo conectar a Neo4j: {e}")
    print("[INFO] Algunas funcionalidades pueden no estar disponibles")
    neo4j_driver = None

# --- 3. REDIS ---
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
redis_client = None
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True, socket_connect_timeout=5)
    # Verificar conexión
    redis_client.ping()
    print("[INFO] Redis conectado exitosamente")
except Exception as e:
    print(f"[WARNING] No se pudo conectar a Redis: {e}")
    print("[INFO] Algunas funcionalidades pueden no estar disponibles")
    redis_client = None

# --- 4. CASSANDRA ---
# Nota: Cassandra a veces tarda en levantar, manejamos la conexión con cuidado
try:
    CASSANDRA_HOSTS = os.getenv('CASSANDRA_HOSTS', 'localhost').split(',')
    cluster = Cluster(CASSANDRA_HOSTS)
    cassandra_session = cluster.connect()
    # Crear el keyspace si no existe
    cassandra_session.execute("""
        CREATE KEYSPACE IF NOT EXISTS edugrade_audit
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
    """)
    cassandra_session.set_keyspace('edugrade_audit')
    # Crear la tabla en el keyspace
    cassandra_session.execute("""
        CREATE TABLE IF NOT EXISTS entity_metadata (
            entity_type text,
            entity_id text,
            estado text,
            created_at timestamp,
            updated_at timestamp,
            PRIMARY KEY (entity_type, entity_id)
        )
    """)
except Exception as e:
    print(f"[WARNING] Cassandra no disponible: {e}")
    cassandra_session = None

def get_mongo():
    if mongo_db is None:
        raise ConnectionError("MongoDB no está disponible. Verifica la conexión.")
    return mongo_db

def get_neo4j():
    if neo4j_driver is None:
        raise ConnectionError("Neo4j no está disponible. Verifica la conexión.")
    return neo4j_driver.session()

def get_redis():
    if redis_client is None:
        raise ConnectionError("Redis no está disponible. Verifica la conexión.")
    return redis_client

def get_cassandra():
    return cassandra_session