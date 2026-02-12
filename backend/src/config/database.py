import os
from pymongo import MongoClient
from neo4j import GraphDatabase
import redis
from cassandra.cluster import Cluster

# --- 1. MONGODB ---
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://root:estudiantes2026@localhost:27017/?authSource=admin')
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client['edugrade_global']

# --- 2. NEO4J ---
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASS = os.getenv('NEO4J_PASS', 'grafos2026')
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# --- 3. REDIS ---
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# --- 4. CASSANDRA ---
# Nota: Cassandra a veces tarda en levantar, manejamos la conexión con cuidado
try:
    CASSANDRA_HOSTS = os.getenv('CASSANDRA_HOSTS', 'localhost').split(',')
    cluster = Cluster(CASSANDRA_HOSTS)
    cassandra_session = cluster.connect()
    # Aseguramos que el keyspace exista
     # Dentro del bloque try de Cassandra en database.py:
    cassandra_session.execute("""
        CREATE TABLE IF NOT EXISTS edugrade_audit.entity_metadata (
            entity_type text,
            entity_id text,
            estado text,
            created_at timestamp,
            updated_at timestamp,
            PRIMARY KEY (entity_type, entity_id)
        )
    """)
    cassandra_session.set_keyspace('edugrade_audit')
except Exception as e:
    print(f"[WARNING] Cassandra no disponible: {e}")
    cassandra_session = None

def get_mongo(): return mongo_db
def get_neo4j(): return neo4j_driver.session()
def get_redis(): return redis_client
def get_cassandra(): return cassandra_session