from pymongo import MongoClient
from neo4j import GraphDatabase
import redis
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

def get_connection_cassandra():
    # En Docker, el 'contact_points' suele ser el nombre del servicio en docker-compose
    contact_points = ['localhost'] 
    
    # Si configuraste usuarios en tu cluster de Cassandra
    # auth_provider = PlainTextAuthProvider(username='user', password='password')
    # cluster = Cluster(contact_points, auth_provider=auth_provider)
    
    cluster = Cluster(contact_points)
    session = cluster.connect()
    
    # Es recomendable definir el keyspace (la "base de datos" en Cassandra)
    # session.set_keyspace('edugrade_log')
    
    return session

def get_connection_mongodb():
    uri = ""
    client = MongoClient(uri)
    db = client['']

    return db

def get_connection_neo4j():
    uri = ''
    usuario = ''
    contrasena = ''

    driver = GraphDatabase.driver(uri, auth=(usuario, contrasena))
    session = driver.session()

    return session

def get_connection_redis():
    # Redis se usará para el cacheo de reglas de conversión (RF2) [cite: 273]
    r = redis.Redis(
        host='localhost', 
        port=6379, 
        db=0, 
        decode_responses=True # Para que devuelva strings y no bytes
    )
    return r
