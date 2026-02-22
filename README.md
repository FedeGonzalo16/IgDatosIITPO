# EduGrade — Sistema de Gestión Académica con Persistencia Políglota

Trabajo Práctico Obligatorio — Ingeniería de Datos II · IITPO

---

## Introducción

**EduGrade** es un sistema de gestión académica que implementa **persistencia políglota**: en lugar de utilizar una única base de datos para todo, cada motor de almacenamiento resuelve el problema para el que está optimizado.

El sistema permite registrar estudiantes, materias, calificaciones e instituciones de distintos países, cada uno con su propio sistema de notas (numérico argentino 1–10, letras A–F del sistema estadounidense, escala invertida alemana 1.0–6.0, letras A\*–F del sistema británico). EduGrade convierte automáticamente entre escalas, registra trayectorias académicas y genera reportes de auditoría.

### Motores utilizados y su rol

| Motor | Tipo | Rol en EduGrade |
|---|---|---|
| **MongoDB** | Documental | Fuente de verdad de los datos: estudiantes, materias, calificaciones, instituciones y reglas de conversión. Elegido por su esquema flexible, ideal para calificaciones con estructura variable según el país. |
| **Neo4j** | Grafos | Fuente de verdad de las relaciones: trayectorias académicas (`CURSANDO`, `CURSÓ`), equivalencias entre materias de distintas instituciones y relaciones docente–materia. |
| **Redis** | Clave-Valor | Caché de alta velocidad para las reglas de conversión entre sistemas de notas (patrón Cache-Aside, TTL 7 días). No es fuente de verdad; es un espejo de velocidad. |
| **Cassandra** | Columnar | Log inmutable de auditoría y certificados emitidos. Append-only por diseño: nunca se borra nada. Clasificación AP del teorema CAP para garantizar disponibilidad de escritura. |

### Arquitectura general

```
Frontend (React)  ──►  Backend (Flask / Python)
                              │
              ┌───────────────┼───────────────┬──────────────┐
              ▼               ▼               ▼              ▼
          MongoDB           Neo4j           Redis        Cassandra
         (datos)          (relac.)         (caché)       (auditoría)
```

La consistencia entre motores la garantiza la **capa de servicios** mediante dual-write: cada operación escribe en todos los motores necesarios dentro de la misma función Python.

---

## Estructura de Carpetas

```
IgDatosIITPO/
│
├── README.md                          # Este archivo
├── BACKEND_DOCUMENTACION.md           # Documentación técnica de endpoints
├── Persistencia_Poliglota_Explicacion.md  # Explicación arquitectónica del diseño
│
├── backend/
│   ├── run.py                         # Punto de entrada — arranca el servidor Flask
│   ├── data_seed.py                   # Script para poblar las bases con datos de prueba
│   ├── requirements.txt               # Dependencias Python
│   ├── docker-compose.yaml            # Levanta MongoDB, Neo4j, Redis y Cassandra
│   │
│   └── src/
│       ├── __init__.py
│       ├── swagger_template.py        # Definición de la documentación Swagger/OpenAPI
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   └── database.py            # Conexiones a las 4 bases de datos
│       │
│       ├── routes/                    # Endpoints HTTP (Blueprints de Flask)
│       │   ├── student_routes.py      # /api/v1/estudiantes
│       │   ├── professor_routes.py    # /api/v1/profesores
│       │   ├── academic_routes.py     # /api/v1/academic  (materias, carreras, instituciones)
│       │   ├── grading_routes.py      # /api/v1/calificaciones  (notas y conversiones)
│       │   ├── reports_routes.py      # /api/v1/reportes  (Cassandra)
│       │   └── trajectory_routes.py  # /api/v1/trayectoria  (Neo4j)
│       │
│       └── services/                  # Lógica de negocio — coordina las bases de datos
│           ├── student_service.py     # Gestión de estudiantes (MongoDB + Neo4j + Cassandra)
│           ├── professor_service.py   # Gestión de profesores (MongoDB + Neo4j)
│           ├── academic_service.py    # Materias, carreras e instituciones (MongoDB + Neo4j)
│           ├── grading_service.py     # Calificaciones y cursadas (MongoDB + Neo4j + Cassandra)
│           ├── conversion_service.py  # Conversión entre sistemas de notas (MongoDB + Redis)
│           ├── metadata_service.py    # Auditoría y metadatos (Cassandra)
│           ├── transcript_service.py  # Certificados analíticos
│           └── analytics_service.py  # Reportes y estadísticas (Cassandra + MongoDB)
│
└── frontend/
    ├── package.json
    ├── public/
    │   └── index.html
    └── src/
        ├── App.js                     # Componente raíz y rutas
        ├── pages/
        │   ├── Login.js               # Inicio de sesión
        │   ├── Register.js            # Registro de usuarios
        │   ├── StudentDashboard.js    # Panel del estudiante (materias, historial, notas)
        │   ├── StudentProfile.js      # Perfil y trayectoria detallada
        │   ├── ProfessorDashboard.js  # Panel del profesor
        │   ├── AdminDashboard.js      # Panel de administración
        │   └── ReportesPage.js        # Reportes y estadísticas
        ├── components/
        │   ├── Navbar.js              # Barra de navegación
        │   ├── ProtectedRoute.js      # Rutas protegidas por rol
        │   ├── StudentSidebar.js      # Menú lateral del estudiante
        │   └── StudentMenuContent.js  # Contenido dinámico del menú
        ├── services/
        │   ├── api.js                 # Configuración de Axios y servicios REST
        │   └── advancedServices.js    # Servicios para Neo4j, Redis y Cassandra
        └── utils/
            └── certificadoAnalitico.js  # Generación de certificados en PDF
```

---

## Requisitos Previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) y npm

---

## Paso a Paso para Correr el Sistema

### Paso 1 — Levantar las bases de datos con Docker

Desde la carpeta `backend/`, ejecutar:

```bash
cd backend
docker compose up -d
```

Esto levanta los cuatro contenedores:

| Contenedor | Puerto | Credenciales |
|---|---|---|
| MongoDB | 27017 | `root` / `estudiantes2026` |
| Neo4j | 7474 (browser), 7687 (Bolt) | `neo4j` / `grafos2026` |
| Redis | 6379 | sin contraseña |
| Cassandra | 9042 | sin contraseña |

> **Nota:** Cassandra tarda aproximadamente 60 segundos en inicializarse por completo. Antes de continuar, verificar que el contenedor esté sano con `docker ps`.

---

### Paso 2 — Instalar dependencias del backend

```bash
cd backend
pip install -r requirements.txt
```

---

### Paso 3 — Iniciar el servidor backend

```bash
cd backend
python run.py
```

El servidor queda disponible en `http://localhost:5000`.
La documentación interactiva Swagger está en `http://localhost:5000/apidocs`.

---

### Paso 4 — Poblar las bases con datos de prueba

Con el servidor corriendo, abrir una **segunda terminal** y ejecutar:

```bash
cd backend
python data_seed.py
```

El script crea automáticamente:
- 4 instituciones (UBA, MIT, Oxford, TUM)
- 7 profesores
- 18 materias
- 4 carreras
- 10 estudiantes con distintos perfiles académicos
- 14 reglas de conversión entre sistemas de notas
- Cursadas, calificaciones y trayectorias de ejemplo

---

### Paso 5 — Instalar dependencias del frontend

```bash
cd frontend
npm install
```

---

### Paso 6 — Iniciar el frontend

```bash
cd frontend
npm start
```

La aplicación se abre automáticamente en `http://localhost:3000`.

---

## Credenciales de Prueba

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | `admin@edugrade.com` | `123456` |
| Estudiante (AR) | `fede@mail.com` | `123456` |
| Estudiante (AR) | `ana@mail.com` | `123456` |
| Estudiante (EEUU) | `john@mail.com` | `123456` |
| Profesor | `jorge@mail.com` | `123456` |

---

## Verificación de las bases de datos

**MongoDB** — Conectar desde MongoDB Compass con:
```
mongodb://root:estudiantes2026@localhost:27017/?authSource=admin
```

**Neo4j** — Abrir el browser en `http://localhost:7474` con usuario `neo4j` y contraseña `grafos2026`. Para ver todas las relaciones:
```cypher
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100
```

**Redis** — Verificar conexión:
```bash
docker exec -it edugrade_redis redis-cli ping
```

**Cassandra** — Verificar tablas creadas:
```bash
docker exec -it edugrade_cassandra cqlsh -e "DESCRIBE KEYSPACES;"
```
