"""
Especificación OpenAPI/Swagger para la API EduGrade.
Usado por Flasgger para documentación interactiva en /apidocs
"""

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "EduGrade API",
        "description": "API del Sistema de Gestión Académica EduGrade. Documenta todos los endpoints disponibles.",
        "version": "1.0.0",
        "contact": {
            "name": "EduGrade"
        }
    },
    "host": "localhost:5000",
    "basePath": "/api/v1",
    "schemes": ["http"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "tags": [
        {"name": "Estudiantes", "description": "CRUD de estudiantes"},
        {"name": "Instituciones", "description": "Gestión de instituciones educativas"},
        {"name": "Materias", "description": "Gestión de materias"},
        {"name": "Carreras", "description": "Gestión de carreras"},
        {"name": "Profesores", "description": "CRUD de profesores y asignación a materias"},
        {"name": "Calificaciones", "description": "Registro, inscripción y calificaciones"},
        {"name": "Reportes", "description": "Reportes y estadísticas"},
        {"name": "Trayectoria", "description": "Trayectoria académica (Neo4j)"}
    ],
    "paths": {
        # --- ESTUDIANTES ---
        "/estudiantes": {
            "get": {
                "tags": ["Estudiantes"],
                "summary": "Obtener todos los estudiantes",
                "responses": {"200": {"description": "Lista de estudiantes"}}
            },
            "post": {
                "tags": ["Estudiantes"],
                "summary": "Crear estudiante",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "required": True,
                    "schema": {
                        "type": "object",
                        "required": ["legajo", "nombre", "apellido", "email"],
                        "properties": {
                            "legajo": {"type": "string", "example": "L-1001"},
                            "nombre": {"type": "string"},
                            "apellido": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "pais": {"type": "string"}
                        }
                    }
                }],
                "responses": {"201": {"description": "Estudiante creado"}}
            }
        },
        "/estudiantes/{uid}": {
            "get": {
                "tags": ["Estudiantes"],
                "summary": "Obtener estudiante por ID",
                "parameters": [{"in": "path", "name": "uid", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Estudiante encontrado"}, "404": {"description": "No encontrado"}}
            },
            "put": {
                "tags": ["Estudiantes"],
                "summary": "Actualizar estudiante",
                "parameters": [
                    {"in": "path", "name": "uid", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {"type": "object"}}
                ],
                "responses": {"200": {"description": "Actualizado"}}
            },
            "delete": {
                "tags": ["Estudiantes"],
                "summary": "Eliminar estudiante (soft delete)",
                "parameters": [{"in": "path", "name": "uid", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Eliminado"}}
            }
        },
        "/estudiantes/email/{email}": {
            "get": {
                "tags": ["Estudiantes"],
                "summary": "Obtener estudiante por email",
                "parameters": [{"in": "path", "name": "email", "required": True, "type": "string"}],
                "responses": {"200": {"description": "Estudiante encontrado"}, "404": {"description": "No encontrado"}}
            }
        },
        # --- INSTITUCIONES ---
        "/academic/instituciones": {
            "get": {"tags": ["Instituciones"], "summary": "Listar instituciones", "responses": {"200": {"description": "Lista"}}},
            "post": {
                "tags": ["Instituciones"],
                "summary": "Crear institución",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "schema": {
                        "type": "object",
                        "properties": {"codigo": {"type": "string"}, "nombre": {"type": "string"}, "pais": {"type": "string"}}
                    }
                }],
                "responses": {"201": {"description": "Creada"}}
            }
        },
        "/academic/instituciones/{uid}": {
            "get": {"tags": ["Instituciones"], "summary": "Obtener institución", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "OK"}}},
            "put": {"tags": ["Instituciones"], "summary": "Actualizar institución", "parameters": [{"in": "path", "name": "uid", "type": "string"}, {"in": "body", "name": "body"}], "responses": {"200": {"description": "OK"}}},
            "delete": {"tags": ["Instituciones"], "summary": "Eliminar institución", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "OK"}}}
        },
        # --- MATERIAS ---
        "/academic/materias": {
            "get": {"tags": ["Materias"], "summary": "Listar materias", "responses": {"200": {"description": "Lista"}}},
            "post": {
                "tags": ["Materias"],
                "summary": "Crear materia",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "schema": {
                        "type": "object",
                        "properties": {"codigo": {"type": "string"}, "nombre": {"type": "string"}, "nivel": {"type": "string"}, "institucion_id": {"type": "string"}}
                    }
                }],
                "responses": {"201": {"description": "Creada"}}
            }
        },
        "/academic/materias/{uid}": {
            "get": {"tags": ["Materias"], "summary": "Obtener materia", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "OK"}}},
            "put": {"tags": ["Materias"], "summary": "Actualizar materia", "parameters": [{"in": "path", "name": "uid", "type": "string"}, {"in": "body", "name": "body"}], "responses": {"200": {"description": "OK"}}},
            "delete": {"tags": ["Materias"], "summary": "Eliminar materia", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "OK"}}}
        },
        "/academic/materias/estudiante/{est_id}": {
            "get": {"tags": ["Materias"], "summary": "Materias de un estudiante", "parameters": [{"in": "path", "name": "est_id", "type": "string"}], "responses": {"200": {"description": "OK"}}}
        },
        # --- CARRERAS ---
        "/academic/carreras": {
            "get": {"tags": ["Carreras"], "summary": "Listar carreras", "responses": {"200": {"description": "Lista"}}},
            "post": {"tags": ["Carreras"], "summary": "Crear carrera", "parameters": [{"in": "body", "name": "body"}], "responses": {"201": {"description": "Creada"}}}
        },
        "/academic/carreras/{uid}": {
            "get": {"tags": ["Carreras"], "summary": "Obtener carrera", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "OK"}}}
        },
        # --- PROFESORES ---
        "/profesores": {
            "get": {"tags": ["Profesores"], "summary": "Listar profesores", "responses": {"200": {"description": "Lista"}}},
            "post": {
                "tags": ["Profesores"],
                "summary": "Crear profesor",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "schema": {
                        "type": "object",
                        "required": ["legajo_docente", "nombre", "apellido"],
                        "properties": {
                            "legajo_docente": {"type": "string"},
                            "nombre": {"type": "string"},
                            "apellido": {"type": "string"},
                            "especialidad": {"type": "string"}
                        }
                    }
                }],
                "responses": {"201": {"description": "Creado"}}
            }
        },
        "/profesores/{uid}": {
            "get": {"tags": ["Profesores"], "summary": "Obtener profesor", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "OK"}}},
            "put": {"tags": ["Profesores"], "summary": "Actualizar profesor", "parameters": [{"in": "path", "name": "uid", "type": "string"}, {"in": "body", "name": "body"}], "responses": {"200": {"description": "OK"}}},
            "delete": {"tags": ["Profesores"], "summary": "Eliminar profesor", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "OK"}}}
        },
        "/profesores/{prof_id}/asignar-materia": {
            "post": {
                "tags": ["Profesores"],
                "summary": "Asignar materia a profesor",
                "parameters": [
                    {"in": "path", "name": "prof_id", "required": True, "type": "string"},
                    {"in": "body", "name": "body", "schema": {"type": "object", "properties": {"materia_id": {"type": "string"}, "activo": {"type": "boolean", "default": True}}}}
                ],
                "responses": {"201": {"description": "Asignada"}}
            }
        },
        # --- CALIFICACIONES ---
        "/calificaciones": {
            "get": {"tags": ["Calificaciones"], "summary": "Listar calificaciones", "responses": {"200": {"description": "Lista"}}},
            "post": {
                "tags": ["Calificaciones"],
                "summary": "Registrar calificación",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "estudiante_id": {"type": "string"},
                            "materia_id": {"type": "string"},
                            "valor_original": {"type": "object"}
                        }
                    }
                }],
                "responses": {"201": {"description": "Registrada"}}
            }
        },
        "/calificaciones/estudiante/{uid}": {
            "get": {"tags": ["Calificaciones"], "summary": "Historial de calificaciones del estudiante", "parameters": [{"in": "path", "name": "uid", "type": "string"}], "responses": {"200": {"description": "Historial"}}
            }
        },
        "/calificaciones/inscribir": {
            "post": {
                "tags": ["Calificaciones"],
                "summary": "Inscribir alumno a materia",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "schema": {
                        "type": "object",
                        "required": ["estudiante_id", "materia_id"],
                        "properties": {"estudiante_id": {"type": "string"}, "materia_id": {"type": "string"}, "anio_lectivo": {"type": "integer"}}
                    }
                }],
                "responses": {"201": {"description": "Inscrito"}}
            }
        },
        "/calificaciones/cargar-nota": {
            "post": {
                "tags": ["Calificaciones"],
                "summary": "Cargar nota (parcial, final, previo)",
                "parameters": [{
                    "in": "body",
                    "name": "body",
                    "schema": {
                        "type": "object",
                        "required": ["estudiante_id", "materia_id", "tipo_nota", "valor"],
                        "properties": {"estudiante_id": {"type": "string"}, "materia_id": {"type": "string"}, "tipo_nota": {"type": "string", "enum": ["primer_parcial", "segundo_parcial", "final", "previo"]}, "valor": {"type": "number"}}
                    }
                }],
                "responses": {"201": {"description": "Cargada"}}
            }
        },
        "/calificaciones/cerrar-cursada": {
            "post": {
                "tags": ["Calificaciones"],
                "summary": "Cerrar cursada (evalúa aprobado/reprobado)",
                "parameters": [{"in": "body", "name": "body", "schema": {"type": "object", "properties": {"estudiante_id": {"type": "string"}, "materia_id": {"type": "string"}}}}],
                "responses": {"200": {"description": "Cerrada"}}
            }
        },
        "/calificaciones/reglas": {
            "get": {"tags": ["Calificaciones"], "summary": "Listar reglas de conversión", "responses": {"200": {"description": "Lista"}}},
            "post": {"tags": ["Calificaciones"], "summary": "Crear regla de conversión", "parameters": [{"in": "body", "name": "body"}], "responses": {"201": {"description": "Creada"}}
            }
        },
        "/calificaciones/convertir": {
            "post": {"tags": ["Calificaciones"], "summary": "Aplicar conversión de nota", "parameters": [{"in": "body", "name": "body"}], "responses": {"200": {"description": "Valor convertido"}}
            }
        },
        # --- REPORTES ---
        "/reportes/certificado-analitico/{est_id}": {
            "get": {
                "tags": ["Reportes"],
                "summary": "Certificado analítico del estudiante",
                "parameters": [
                    {"in": "path", "name": "est_id", "required": True, "type": "string"},
                    {"in": "query", "name": "carrera_nombre", "type": "string"},
                    {"in": "query", "name": "guardar_snapshot", "type": "boolean", "default": True}
                ],
                "responses": {"200": {"description": "Certificado"}}
            }
        },
        "/reportes/estudiante/{est_id}": {
            "get": {"tags": ["Reportes"], "summary": "Reporte completo del estudiante", "parameters": [{"in": "path", "name": "est_id", "type": "string"}], "responses": {"200": {"description": "Reporte"}}
            }
        },
        "/reportes/institucion/{inst_id}": {
            "get": {"tags": ["Reportes"], "summary": "Reporte de institución", "parameters": [{"in": "path", "name": "inst_id", "type": "string"}], "responses": {"200": {"description": "Reporte"}}
            }
        },
        "/reportes/calificaciones": {
            "get": {"tags": ["Reportes"], "summary": "Estadísticas de calificaciones", "parameters": [{"in": "query", "name": "materia_id", "type": "string"}, {"in": "query", "name": "estudiante_id", "type": "string"}], "responses": {"200": {"description": "Estadísticas"}}
            }
        },
        "/reportes/aprobacion": {
            "get": {"tags": ["Reportes"], "summary": "Estadísticas de aprobación", "responses": {"200": {"description": "Tasa aprobación"}}
            }
        },
        "/reportes/auditoria/{est_id}": {
            "get": {"tags": ["Reportes"], "summary": "Auditoría de un estudiante", "parameters": [{"in": "path", "name": "est_id", "type": "string"}], "responses": {"200": {"description": "Auditoría"}}
            }
        },
        # --- TRAYECTORIA ---
        "/trayectoria/estudiante/{est_id}": {
            "get": {"tags": ["Trayectoria"], "summary": "Trayectoria completa del estudiante (materias en curso, aprobadas, reprobadas, recursadas)", "parameters": [{"in": "path", "name": "est_id", "type": "string"}], "responses": {"200": {"description": "Trayectoria"}}
            }
        },
        "/trayectoria/materia/{mat_id}": {
            "get": {"tags": ["Trayectoria"], "summary": "Trayectoria de una materia (estudiantes en curso, aprobados, reprobados)", "parameters": [{"in": "path", "name": "mat_id", "type": "string"}], "responses": {"200": {"description": "Trayectoria"}}
            }
        }
    }
}
