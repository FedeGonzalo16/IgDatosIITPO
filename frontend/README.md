# EduGrade Frontend - Sistema Educativo React

Un frontend moderno y completo construido con React para gestionar sistemas educativos. Incluye autenticación, dashboard de estudiantes, perfil académico detallado y panel administrativo.

## 🎯 Características Principales

### Para Estudiantes
- ✅ **Login y Registro** - Sistema de autenticación seguro
- 📚 **Dashboard Personal** - Visualización de materias en curso y aprobadas
- 📊 **Historial Académico** - Detalles completos de calificaciones y componentes
- 📥 **Descarga de Reportes** - Generar reportes académicos en formato TXT
- 📈 **Estadísticas** - Promedio, tasa de aprobación y más

### Para Administradores
- 👥 **Gestión de Estudiantes** - Ver, editar y filtrar estudiantes
- 📖 **Gestión de Materias** - Control completo de materias y estadísticas
- 📝 **Gestión de Calificaciones** - Registrar y auditar calificaciones
- 🏢 **Gestión de Instituciones** - Administrar instituciones educativas
- 🔍 **Consultas Avanzadas** - Búsqueda y filtros potentes

## 🛠️ Requisitos Previos

- Node.js >= 14.0.0
- npm >= 6.0.0 o yarn >= 1.22.0
- Backend API ejecutándose en `localhost:5000`

## 📦 Instalación

1. **Navega a la carpeta frontend**
```bash
cd frontend
```

2. **Instala las dependencias**
```bash
npm install
```

3. **Configura las variables de entorno**

Crea un archivo `.env` en la raíz del proyecto (ya incluido) con:
```
REACT_APP_API_BASE_URL=http://localhost:5000/api/v1
REACT_APP_API_NEO4J_URL=http://localhost:5001/api
REACT_APP_API_REDIS_URL=http://localhost:5002/api
REACT_APP_API_CASSANDRA_URL=http://localhost:5003/api
```

4. **Inicia el servidor de desarrollo**
```bash
npm start
```

La aplicación se abrirá en `http://localhost:3000`

## 🚀 Uso

### Credenciales de Demostración

**Estudiante:**
- Email: `student@example.com`
- Contraseña: `123456`

**Administrador:**
- Email: `admin@example.com`
- Contraseña: `123456`

### Flujos Principales

#### Para Estudiantes
1. Iniciar sesión con credenciales
2. Ver dashboard con materias en curso y aprobadas
3. Acceder a perfil para ver historial académico detallado
4. Descargar reporte académico en PDF/TXT
5. Cerrar sesión

#### Para Administradores
1. Iniciar sesión como admin
2. Acceder al panel administrativo
3. Usar pestañas para navegar entre:
   - **Estudiantes**: Ver lista, buscar, filtrar por estado
   - **Materias**: Ver estadísticas de aprobación
   - **Calificaciones**: Auditoría de calificaciones
   - **Instituciones**: Gestión de instituciones
4. Usar búsqueda y filtros para consultas específicas

## 📁 Estructura del Proyecto

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Navbar.js           # Barra de navegación
│   │   ├── Navbar.css
│   │   └── ProtectedRoute.js    # Rutas protegidas
│   ├── pages/
│   │   ├── Login.js            # Página de login
│   │   ├── Register.js         # Página de registro
│   │   ├── StudentDashboard.js # Dashboard de estudiante
│   │   ├── StudentProfile.js   # Perfil académico detallado
│   │   ├── AdminDashboard.js   # Panel administrativo
│   │   └── Auth.css            # Estilos de autenticación
│   ├── services/
│   │   └── api.js              # Configuración de axios y endpoints
│   ├── App.js                  # Componente raíz
│   ├── App.css
│   ├── index.js
│   └── index.css
├── .env                        # Variables de entorno
├── package.json
└── README.md
```

## 🔌 Integración con Backend

El frontend utiliza los siguientes endpoints del backend:

### Autenticación
- `POST /auth/login` - Iniciar sesión
- `POST /auth/register` - Registrar estudiante

### Estudiantes
- `GET /estudiantes` - Listar estudiantes
- `GET /estudiantes/{id}` - Obtener estudiante
- `POST /estudiantes` - Crear estudiante
- `PUT /estudiantes/{id}` - Actualizar estudiante
- `DELETE /estudiantes/{id}` - Eliminar estudiante

### Calificaciones
- `GET /calificaciones` - Listar calificaciones
- `GET /calificaciones/estudiante/{studentId}` - Calificaciones de estudiante
- `POST /calificaciones` - Registrar calificación
- `PUT /calificaciones/{id}` - Actualizar calificación

### Materias
- `GET /materias` - Listar materias
- `GET /materias/{id}` - Obtener materia
- `POST /materias` - Crear materia
- `PUT /materias/{id}` - Actualizar materia

### Reportes
- `GET /reportes/estudiante/{studentId}` - Reporte académico
- `GET /reportes/aprobacion` - Estadísticas de aprobación

## 🎨 Diseño y UX

- **Diseño Responsivo**: Funcionan perfectamente en desktop, tablet y móvil
- **Gradientes Modernos**: Paleta de colores profesional (púrpura/azul)
- **Animaciones Suaves**: Transiciones y efectos CSS3
- **Interfaz Intuitiva**: Navegación clara y fácil de usar
- **Iconos Lucide React**: Iconos profesionales y consistentes

## 🔐 Seguridad

- Token JWT almacenado en localStorage
- Interceptores de Axios para inyección automática de token
- Rutas protegidas con ProtectedRoute
- Validación de roles (admin/student)
- Logout automático si token expira (401)

## 🌐 Variables de Entorno

```
REACT_APP_API_BASE_URL        # URL base del API MongoDB
REACT_APP_API_NEO4J_URL       # URL del API Neo4j (opcional)
REACT_APP_API_REDIS_URL       # URL del API Redis (opcional)
REACT_APP_API_CASSANDRA_URL   # URL del API Cassandra (opcional)
```

## 📚 Dependencias Principales

- **react** (^18.2.0) - Biblioteca UI
- **react-router-dom** (^6.20.0) - Enrutamiento
- **axios** (^1.6.0) - Cliente HTTP
- **lucide-react** (^0.294.0) - Iconos
- **chart.js** (^4.4.0) - Gráficos (para futuras expansiones)

## 🔄 Flujo de Autenticación

```
1. Usuario accede a /login
2. Ingresa credenciales
3. Frontend llama a /auth/login
4. Backend retorna JWT token + datos usuario
5. Token se almacena en localStorage
6. Usuario redirigido a /student o /admin según rol
7. En cada petición, token se inyecta en headers
8. Si token expira (401), se borra y redirige a /login
```

## 🧪 Testing

Para agregar tests (opcional):
```bash
npm test
```

## 📝 Notas de Implementación

### Conexión al Backend
Actualmente el frontend usa datos simulados (mock data). Para conectar con el backend real:

1. Descomenta los servicios de API en cada página
2. Reemplaza los datos mock con llamadas a `api.js`
3. Asegúrate de que el backend tenga CORS habilitado

Ejemplo:
```javascript
// En lugar de mock data:
// const mockSubjects = [...]

// Usa:
const response = await gradeService.getByStudent(userId);
setSubjects(response.data);
```

### Agregar Autenticación Real
En `Login.js` y `Register.js`:
```javascript
// En lugar de mock token:
// const mockToken = 'mock-token-' + Date.now();

// Usa:
const response = await authService.login(email, password);
onLogin(response.data.user, response.data.token);
```

## 🐛 Troubleshooting

**El frontend no se conecta al backend**
- Verifica que el backend esté ejecutándose en el puerto correcto
- Revisa la consola del navegador para errores de CORS
- Asegúrate de que las URLs en `.env` son correctas

**Error de autenticación**
- Limpia localStorage: `localStorage.clear()`
- Recarga la página (Ctrl+Shift+R)
- Verifica que el token sea válido en el backend

**Datos vacíos en las tablas**
- Asegúrate de tener datos en la base de datos
- Verifica que los endpoints del backend retornen datos correctamente

## 📞 Soporte

Para reportar bugs o solicitar características:
1. Revisa el código en `src/services/api.js`
2. Verifica los logs en la consola del navegador
3. Comprueba la respuesta del backend usando una herramienta como Postman

## 📄 Licencia

Este proyecto es parte del sistema educativo EduGrade.

## 🎓 Próximas Mejoras

- [ ] Autenticación OAuth2
- [ ] Integración con gráficos (Chart.js)
- [ ] Temas oscuro/claro
- [ ] Notificaciones en tiempo real
- [ ] Descarga de reportes en PDF
- [ ] Exportación de datos a Excel
- [ ] Historial de auditoría detallado

---

**Últimas actualización:** Febrero 2026
**Versión:** 1.0.0
