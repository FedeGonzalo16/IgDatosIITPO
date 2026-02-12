import subprocess
import sys
import time
import os
import signal

# Definimos los scripts y sus puertos para identificación
scripts = [
    {"path": "backend/docker/mongodb/api_mongo.py", "name": "API MONGO (5000)"},
    {"path": "backend/docker/neo4j/api_neo4j.py", "name": "API NEO4J (5001)"},
    {"path": "backend/docker/redis/api_redis.py", "name": "API REDIS (5002)"},
    {"path": "backend/docker/cassandra/api_cassandra.py", "name": "API CASSANDRA (5003)"}
]

processes = []

def stop_all(signal_received, frame):
    print("\n\n[ORQUESTADOR] Deteniendo todos los servicios...")
    for p in processes:
        p.terminate()  # Envía señal de terminación
    sys.exit(0)

# Capturar Ctrl+C para cerrar todo limpio
signal.signal(signal.SIGINT, stop_all)

print(f"[ORQUESTADOR] Iniciando 4 microservicios con Python {sys.version.split()[0]}...")
print("Presiona CTRL+C para detener todo.\n")

# Directorio raíz del proyecto
base_dir = os.getcwd()

try:
    for script in scripts:
        full_path = os.path.join(base_dir, script["path"])
        
        if not os.path.exists(full_path):
            print(f"[ERROR] No se encontró: {full_path}")
            continue

        print(f"--> Iniciando {script['name']}...")
        
        # Iniciar proceso independiente
        # Usamos sys.executable para asegurar que usa el mismo python que ejecutó este script
        p = subprocess.Popen([sys.executable, full_path], cwd=base_dir)
        processes.append(p)
        
    print("\n[ORQUESTADOR] Todos los servicios están corriendo.")
    print("[INFO] Los logs de cada API aparecerán aquí mezclados.\n")
    
    # Mantener el script vivo
    while True:
        time.sleep(1)

except Exception as e:
    print(f"[ERROR CRÍTICO] {e}")
    stop_all(None, None)