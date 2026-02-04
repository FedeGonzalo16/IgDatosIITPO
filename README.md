# IgDatosIITPO
Repositorio para el desarrollo del TPO respectivo a la MRI de Ingeniería de Datos II

# Pasos a seguir
# -----------MONGODB-----------
1. Borrar el contenedor actual.
2. crear un nuevo contedor copiando: 
docker run -d -p 27017:27017 --name mongo-edugrade -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=estudiantes2026 mongo:latest
3. Ir al compass y crear una nueva conexión en: mongodb://root:estudiantes2026@localhost:27017/?authSource=admin
4. Ejecutar data_seed.py