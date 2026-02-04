from datetime import date
import random
from pymongo import MongoClient
import api_mongo
##Conexión
uri = "mongodb://root:estudiantes2026@localhost:27017/admin"
client = MongoClient(uri)

#Procesos
##print(client.admin.command('ping'))
###

db= client["registro_academico"]
estudiante=db["estudiantes"]
instituciones=db["instituciones"]
materias=db["materias"]


evaluaciones=[]

parcial1={
    "tipo": "Parcial",
    "fecha": "2023-06-15",
    "nota": random.randint(1, 10)
}
parcial2={
    "tipo": "Parcial",
    "fecha": "2023-09-20",
    "nota": random.randint(1, 10)
}
evaluaciones.append(parcial1)
evaluaciones.append(parcial2)
if(parcial1["nota"] < 4 or parcial2["nota"] <4):
    recuperatorio1={
        "tipo": "Recuperatorio",
        "fecha": "2023-07-10",
        "nota": random.randint(1, 10)
    }
    evaluaciones.append(recuperatorio1)
final={
    "tipo": "Final",
    "fecha": "2023-12-10",
    "nota": random.randint(1, 10)
}

evaluaciones.append(final)

materia= {
    "nombre": "Base de Datos",
    "cantidad_evaluaciones": 4,
}



estudiante1={
    
    "nombre":"Gonzalo",
    "apellido":"Gomez",
    "edad":random.randint(18, 30),
    "dni": random.randint(30000000, 60000000),

}

institucion1={
    "nombre": "UADE",
    "tipo": "Universidad Privada",
    "direccion": "Lima 7577, C1073 CABA",
    "email": "info@uade.edu.ar"}



#cambiar a la API los inserts!!

#tiene que llamar a la funcion cargar_estudiante de api_mongo.py
api_mongo.cargar_institucion(institucion1)
api_mongo.cargar_estudiante(estudiante1)

 
#Cerrar conexión
client.close()