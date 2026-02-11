% EduGrade Frontend - Documentación Completa

# 📚 EduGrade Frontend React - Documentación Completa

## 🎯 Inicio Rápido

↳ **[Leer QUICKSTART.md](./QUICKSTART.md)** (5 minutos)
- Instalación en 3 pasos
- Credenciales de prueba
- Funcionalidades principales

## 📖 Documentación Completa

### 1. **[README.md](./README.md)** - Documentación Principal
Todo lo que necesitas saber sobre el proyecto:
- Características completas
- Requisitos del sistema
- Instalación detallada
- Estructura del proyecto
- Integración con backend
- Variables de entorno
- Troubleshooting

### 2. **[SETUP.md](./SETUP.md)** - Guía de Configuración
Pasos detallados para ejecutar el proyecto:
- Instalación de dependencias
- Cómo ejecutar
- Funcionalidades implementadas
- Características de diseño
- Próximos pasos
- Solución de problemas

### 3. **[QUICKSTART.md](./QUICKSTART.md)** - Guía Rápida
Para empezar inmediatamente:
- 3 pasos para instalar
- Credenciales de demostración
- Datos de ejemplo
- Características principales

## 💻 Guías de Código

### API y Servicios

**[src/services/api.js](./src/services/api.js)**
- Configuración de Axios
- Endpoints MongoDB
- Autenticación
- CRUD Completo

**[src/services/advancedServices.js](./src/services/advancedServices.js)**
- Neo4j - Análisis de trayectorias
- Redis - Cache y sesiones
- Cassandra - Auditoría e informes
- Servicios combinados

**[src/services/EXAMPLES.md](./src/services/EXAMPLES.md)**
- Ejemplo 1: Análisis completo de estudiante
- Ejemplo 2: Dashboard ejecutivo
- Ejemplo 3: Historial de auditoría
- Ejemplo 4: Análisis de trayectoria
- Ejemplo 5: Reportes geográficos

## 📁 Estructura de Carpetas

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Navbar.js
│   │   ├── Navbar.css
│   │   └── ProtectedRoute.js
│   ├── pages/
│   │   ├── Login.js
│   │   ├── Register.js
│   │   ├── StudentDashboard.js
│   │   ├── StudentProfile.js
│   │   ├── AdminDashboard.js
│   │   └── [estilos CSS]
│   ├── services/
│   │   ├── api.js
│   │   ├── advancedServices.js
│   │   └── EXAMPLES.md
│   ├── App.js
│   ├── index.js
│   └── [estilos CSS]
├── .env
├── .gitignore
├── package.json
├── README.md
├── QUICKSTART.md
├── SETUP.md
└── INDEX.md (este archivo)
```

## 🎯 Funcionalidades

### 👨‍🎓 Para Estudiantes
- ✅ **Login/Registro** - Autenticación segura
- ✅ **Dashboard** - Materias en curso y aprobadas
- ✅ **Mi Perfil** - Historial académico detallado
- ✅ **Calificaciones** - Desglose por componentes
- ✅ **Estadísticas** - Promedio y tasa de aprobación
- ✅ **Reportes** - Descargar historial académico

### 👨‍💼 Para Administradores
- ✅ **Estudiantes** - Búsqueda y filtros avanzados
- ✅ **Materias** - Ver estadísticas y aprobación
- ✅ **Calificaciones** - Auditoría y registros
- ✅ **Instituciones** - Gestión completa
- ✅ **Consultas** - Búsqueda en tiempo real

## 🚀 Comenzar

### Opción 1: ¡Empezar Inmediatamente! (Recomendado)
```bash
cd frontend
npm install
npm start
```
Luego abre http://localhost:3000

### Opción 2: Leer Primero
1. Lee [QUICKSTART.md](./QUICKSTART.md) (5 min)
2. Lee [README.md](./README.md) (15 min)
3. Luego ejecuta los pasos anteriores

### Opción 3: Entender la Arquitectura
1. Lee [SETUP.md](./SETUP.md)
2. Revisa [src/services/api.js](./src/services/api.js)
3. Ve los ejemplos en [src/services/EXAMPLES.md](./src/services/EXAMPLES.md)

## 🔐 Credenciales de Prueba

**Estudiante:**
```
Email: student@example.com
Contraseña: 123456
```

**Administrador:**
```
Email: admin@example.com
Contraseña: 123456
```

## 🎨 Características de Diseño

- 🎨 **Gradientes Modernos** - Púrpura/Azul profesional
- 📱 **Responsive** - Funciona en móvil, tablet y desktop
- ✨ **Animaciones** - Transiciones suaves
- 🎯 **Intuitivo** - Navegación clara
- 🎭 **Profesional** - Diseño moderno y limpio

## 🔗 Integración con Bases de Datos

### MongoDB (Puerto 5000)
Datos principales: Estudiantes, Materias, Calificaciones, Instituciones

### Neo4j (Puerto 5001)
Análisis de relaciones: Trayectorias, progresión, recomendaciones

### Redis (Puerto 5002)
Cache y sesiones: Optimización y conversiones

### Cassandra (Puerto 5003)
Auditoría e informes: Historial, geografía, comparativas

## 📊 Ejemplo: Flujo de Login

```
Usuario → Ingresa credenciales
        → Frontend llama /auth/login
        → Backend retorna user + token
        → Token se guarda en localStorage
        → Usuario redirigido a dashboard
        → En cada petición, token se inyecta
```

## 🆘 Ayuda Rápida

| Problema | Solución |
|----------|----------|
| npm install falla | Borra node_modules y .package-lock.json, luego npm install |
| Puerto 3000 ocupado | PORT=3001 npm start |
| No se conecta al backend | Verifica que backend esté corriendo en puerto 5000 |
| Datos no se cargan | Abre F12 (dev tools) y revisa la consola |
| Problemas CORS | Habilita CORS en el backend |

## 📚 Aprender Más

**React:**
- [React Docs](https://react.dev)
- [React Router](https://reactrouter.com)

**Axios:**
- [Axios Docs](https://axios-http.com)

**Tailwind (si quieres agregar):**
- [Tailwind CSS](https://tailwindcss.com)

## 🎓 Próximas Mejoras

- [ ] Conectar con backend real
- [ ] Agregar gráficos (Chart.js)
- [ ] Modo oscuro/claro
- [ ] Exportación a PDF
- [ ] Notificaciones en tiempo real

## 📞 Contacto y Soporte

Revisa:
1. [README.md](./README.md) - Sección Troubleshooting
2. [SETUP.md](./SETUP.md) - Solución de Problemas
3. [src/services/EXAMPLES.md](./src/services/EXAMPLES.md) - Ejemplos de código

## 📄 Archivos Importantes

| Archivo | Propósito |
|---------|-----------|
| [package.json](./package.json) | Dependencias y scripts |
| [.env](./.env) | Variables de entorno |
| [README.md](./README.md) | Documentación principal |
| [SETUP.md](./SETUP.md) | Guía de configuración |
| [QUICKSTART.md](./QUICKSTART.md) | Inicio rápido |
| [src/App.js](./src/App.js) | Componente raíz |
| [src/services/api.js](./src/services/api.js) | Configuración API |

---

## 🎯 Plan de Acción Recomendado

### Día 1: Entender el Proyecto
1. Lee [QUICKSTART.md](./QUICKSTART.md)

### Día 1: Ejecutar la Aplicación
2. Corre `npm install && npm start`
3. Prueba login/registro

### Día 2: Explorar el Código
4. Revisa [README.md](./README.md)
5. Examina [src/services/api.js](./src/services/api.js)

### Día 3: Integrar Backend
6. Descomenta servicios de API
7. Implementa autenticación real

### Día 4+: Agregar Features
8. Consulta [src/services/EXAMPLES.md](./src/services/EXAMPLES.md)
9. Agrega nuevas funcionalidades

---

**¡Tu aplicación está lista para usar!** 🎉

Elige una opción arriba y ¡comienza!
