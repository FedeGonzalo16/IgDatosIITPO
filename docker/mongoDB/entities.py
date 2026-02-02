from datetime import date
import random
from pymongo import MongoClient
##Conexión
uri = "mongodb://root:estudiantes2026@localhost:27017/admin"
client = MongoClient(uri)

#Procesos
##print(client.admin.command('ping'))
###

db= client["registro_academico"]
estudiante=db["estudiantes"]


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
    "Id_codigo": random.randint(1000, 9999),
    "nombre": "Base de Datos",
    "año_cursada": random.randint(1, 5),
    "estado": "Aprobada",
    "evaluaciones": evaluaciones
    
}


estudiante1={
    "nombre":"Gonzalo",
    "apellido":"Gomez",
    "edad":random.randint(18, 30),
    "dni": random.randint(30000000, 60000000),
    "carrera":"Ingenieria de Datos",
    "trayectorias":[
            {
                "institucion": "Escuela Técnica N°1",
                "nivel": "Secundario",
                "ciclo_lectivo": "2022",
                "estado": "Finalizado",
                },
                {
                "institucion": "UADE",
                "nivel": "Universitario",
                "carrera": "Ingeniería en Informática",
                "ciclo_lectivo": "2025",
                "estado": "En curso",
                "materias":[
                    materia
                ]
            
                }
        ],
}

resultado= estudiante.insert_one(estudiante1) 
print("Estudiante insertado con ID:", resultado.inserted_id)






#Cerrar conexión
client.close()